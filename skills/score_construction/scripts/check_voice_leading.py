#!/usr/bin/env python3
import sys
import json
import argparse
from pathlib import Path
from music21 import pitch

DURATION_MAP = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "sixteenth": 0.25
}

RANGE_PROFILES = {
    "soprano": {"min": 60, "max": 81, "name": "Soprano (C4-A5)"},
    "alto": {"min": 55, "max": 77, "name": "Alto (G3-F5)"},
    "tenor": {"min": 48, "max": 67, "name": "Tenor (C3-G4)"},
    "bass": {"min": 41, "max": 64, "name": "Bass (F2-E4)"}
}

def get_midi_num(pitch_str: str) -> int:
    if not pitch_str or pitch_str.lower() == "rest":
        return -1
    try:
        p = pitch.Pitch(pitch_str)
        return p.midi
    except Exception:
        return -1

def main():
    parser = argparse.ArgumentParser(description="Check score for voice-leading and range violations.")
    parser.add_argument("--score-path", help="Path to the score state JSON file")
    parser.add_argument("--session-id", help="Session ID to locate score state JSON file")
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.parent.parent.resolve()
    
    if args.score_path:
        score_path = Path(args.score_path)
    elif args.session_id:
        score_path = project_root / "skills" / "score_construction" / "assets" / f"score_{args.session_id}.json"
    else:
        print(json.dumps({
            "status": "error",
            "error": "Must provide either --score-path or --session-id"
        }))
        sys.exit(1)
        
    try:
        if not score_path.is_file():
            raise FileNotFoundError(f"Score file not found: {score_path}")
            
        with open(score_path, "r", encoding="utf-8") as f:
            state = json.load(f)
            
        parts = state.get("parts", [])
        if not parts:
            raise ValueError("Score has no parts to analyze.")
            
        parallel_fifths = []
        parallel_octaves = []
        range_violations = []
        
        # 1. Build note timeline for each part
        part_timelines = {}
        all_beats = set()
        
        for part in parts:
            part_id = part.get("id", "melody")
            part_name = part.get("name", part_id)
            timeline = []
            current_beat = 0.0
            
            # Identify if there is a range profile matching this part
            range_profile = None
            for key, profile in RANGE_PROFILES.items():
                if key in part_id.lower() or key in part_name.lower():
                    range_profile = profile
                    break
            
            for measure in part.get("measures", []):
                m_num = measure.get("number", 1)
                for event in measure.get("events", []):
                    dur_str = event.get("duration", "quarter").lower()
                    dur_beats = DURATION_MAP.get(dur_str, 1.0)
                    pitches = event.get("pitches", ["rest"])
                    
                    # Range check
                    if range_profile and pitches and "rest" not in [p.lower() for p in pitches]:
                        for p_str in pitches:
                            midi_num = get_midi_num(p_str)
                            if midi_num != -1:
                                if midi_num < range_profile["min"] or midi_num > range_profile["max"]:
                                    range_violations.append({
                                        "part_id": part_id,
                                        "part_name": part_name,
                                        "measure": m_num,
                                        "pitch": p_str,
                                        "midi_value": midi_num,
                                        "profile": range_profile["name"],
                                        "reason": f"Pitch {p_str} is outside range {range_profile['name']}."
                                    })
                                    
                    timeline.append({
                        "start": current_beat,
                        "end": current_beat + dur_beats,
                        "pitches": pitches,
                        "measure": m_num
                    })
                    all_beats.add(current_beat)
                    all_beats.add(current_beat + dur_beats)
                    current_beat += dur_beats
            part_timelines[part_id] = timeline
            
        # Sort all beat boundaries
        sorted_beats = sorted(list(all_beats))
        
        # Helper to get active pitch at a specific beat interval
        def get_active_pitch(timeline, start, end):
            for item in timeline:
                if item["start"] <= start and item["end"] >= end:
                    pitches = item["pitches"]
                    if pitches and "rest" not in [p.lower() for p in pitches]:
                        # return the highest pitch if it's a chord
                        midi_nums = [get_midi_num(p) for p in pitches if get_midi_num(p) != -1]
                        if midi_nums:
                            return max(midi_nums)
            return None

        # 2. Check for parallel fifths/octaves between every pair of parts
        part_ids = list(part_timelines.keys())
        for idx1 in range(len(part_ids)):
            for idx2 in range(idx1 + 1, len(part_ids)):
                id1, id2 = part_ids[idx1], part_ids[idx2]
                name1 = next(p.get("name", id1) for p in parts if p.get("id") == id1)
                name2 = next(p.get("name", id2) for p in parts if p.get("id") == id2)
                
                # Iterate through adjacent time steps in our grid
                for s_idx in range(len(sorted_beats) - 2):
                    b1 = sorted_beats[s_idx]
                    b2 = sorted_beats[s_idx + 1]
                    b3 = sorted_beats[s_idx + 2]
                    
                    p1_first = get_active_pitch(part_timelines[id1], b1, b2)
                    p2_first = get_active_pitch(part_timelines[id2], b1, b2)
                    
                    p1_second = get_active_pitch(part_timelines[id1], b2, b3)
                    p2_second = get_active_pitch(part_timelines[id2], b2, b3)
                    
                    # Both parts must have active notes in both steps
                    if (p1_first is not None and p2_first is not None and 
                        p1_second is not None and p2_second is not None):
                        
                        # Both parts must move
                        motion1 = p1_second - p1_first
                        motion2 = p2_second - p2_first
                        
                        if motion1 != 0 and motion2 != 0:
                            # Check if motion is in the same direction (parallel/similar)
                            if (motion1 > 0 and motion2 > 0) or (motion1 < 0 and motion2 < 0):
                                # Intervals
                                int1 = abs(p1_first - p2_first)
                                int2 = abs(p1_second - p2_second)
                                
                                # Parallel Fifth: interval modulo 12 is 7
                                if int1 % 12 == 7 and int2 % 12 == 7:
                                    # Get measure number
                                    m_num = next((item["measure"] for item in part_timelines[id1] if item["start"] <= b2 < item["end"]), 1)
                                    parallel_fifths.append({
                                        "parts": [id1, id2],
                                        "part_names": [name1, name2],
                                        "measure": m_num,
                                        "first_interval": f"{p1_first} to {p2_first}",
                                        "second_interval": f"{p1_second} to {p2_second}",
                                        "reason": f"Parallel fifths detected between {name1} and {name2} moving into measure {m_num}."
                                    })
                                    
                                # Parallel Octave/Unison: interval modulo 12 is 0
                                if int1 % 12 == 0 and int2 % 12 == 0:
                                    m_num = next((item["measure"] for item in part_timelines[id1] if item["start"] <= b2 < item["end"]), 1)
                                    parallel_octaves.append({
                                        "parts": [id1, id2],
                                        "part_names": [name1, name2],
                                        "measure": m_num,
                                        "first_interval": f"{p1_first} to {p2_first}",
                                        "second_interval": f"{p1_second} to {p2_second}",
                                        "reason": f"Parallel octaves/unisons detected between {name1} and {name2} moving into measure {m_num}."
                                    })
                                    
        result = {
            "status": "success",
            "score_file": score_path.name,
            "has_violations": bool(parallel_fifths or parallel_octaves or range_violations),
            "violations": {
                "parallel_fifths": parallel_fifths,
                "parallel_octaves": parallel_octaves,
                "range_violations": range_violations
            }
        }
        
        print(json.dumps(result, indent=2))
        sys.exit(0)
        
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
