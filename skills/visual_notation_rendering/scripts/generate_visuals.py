#!/usr/bin/env python3
import sys
import json
import re
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Import music21 elements
from music21 import stream, note, clef, meter

DURATION_MAP = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "sixteenth": 0.25
}

def pitch_to_midi(pitch_str):
    if pitch_str.lower() == "rest":
        return None
    # Parse note name, optional accidental, and octave (e.g. C4, F#3, E-5)
    pattern = r"^([A-G])([#\-]?)(-?\d+)$"
    match = re.match(pattern, pitch_str, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid pitch format: {pitch_str}")
    
    note_name = match.group(1).upper()
    alteration = match.group(2)
    octave = int(match.group(3))
    
    semitones = {
        'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11
    }
    
    pitch_val = 12 * (octave + 1) + semitones[note_name]
    if alteration == '#':
        pitch_val += 1
    elif alteration == '-':
        pitch_val -= 1
        
    return pitch_val

def main():
    parser = argparse.ArgumentParser(description="Render score canvas state to visual plots and MusicXML.")
    parser.add_argument("--canvas-path", help="Path to the canvas state JSON file")
    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.parent.parent.resolve()
    
    if args.canvas_path:
        canvas_path = Path(args.canvas_path)
    else:
        canvas_path = project_root / "skills" / "score_construction" / "assets" / "canvas_state.json"
        
    assets_dir = script_dir.parent / "assets"
    
    try:
        if not canvas_path.is_file():
            raise FileNotFoundError(f"Canvas state file not found: {canvas_path}")
            
        with open(canvas_path, "r", encoding="utf-8") as f:
            state = json.load(f)
            
        notes = state.get("notes", [])
        if not notes:
            raise ValueError("Canvas has no notes to render.")
            
        # Ensure output assets folder exists
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse notes to compute time steps and MIDI pitches
        note_data = []
        current_time = 0.0
        
        for idx, n_item in enumerate(notes):
            pitch_str = n_item.get("pitch", "rest")
            duration_str = n_item.get("duration", "quarter").lower()
            dur = DURATION_MAP.get(duration_str, 1.0)
            
            midi = pitch_to_midi(pitch_str)
            if midi is not None:
                note_data.append((current_time, current_time + dur, midi, pitch_str))
            current_time += dur
            
        if not note_data:
            raise ValueError("Canvas contains only rests, no notes to visualize.")
            
        # Unique pitches for Y-axis ticks
        unique_pitches = {}
        for _, _, midi, pitch in note_data:
            unique_pitches[midi] = pitch
            
        sorted_midi = sorted(unique_pitches.keys())
        sorted_labels = [unique_pitches[m] for m in sorted_midi]
        
        # 1. Piano Roll Export (Matplotlib)
        plt.figure(figsize=(10, 4))
        plt.title("Score Canvas Piano Roll View", fontsize=14, fontweight='bold', pad=15)
        plt.xlabel("Time (Beats)", fontsize=11, labelpad=10)
        plt.ylabel("Pitch", fontsize=11, labelpad=10)
        plt.grid(True, which='both', linestyle='--', alpha=0.5)
        
        # Plot horizontal segments
        for start, end, midi, pitch in note_data:
            plt.plot([start, end], [midi, midi], color='#2b5c8f', linewidth=8, solid_capstyle='butt')
            
        plt.yticks(sorted_midi, sorted_labels)
        if len(sorted_midi) == 1:
            plt.ylim(sorted_midi[0] - 1, sorted_midi[0] + 1)
        else:
            plt.ylim(sorted_midi[0] - 0.5, sorted_midi[-1] + 0.5)
            
        plt.xlim(-0.2, current_time + 0.2)
        plt.tight_layout()
        
        piano_roll_path = assets_dir / "piano_roll.png"
        plt.savefig(piano_roll_path, dpi=150)
        plt.close()
        
        # 2. music21 MusicXML Export
        m21_score = stream.Score()
        m21_part = stream.Part()
        
        # Add Time Signature and Treble Clef
        ts_str = state.get("time_signature", "4/4")
        m21_part.append(meter.TimeSignature(ts_str))
        m21_part.append(clef.TrebleClef())
        
        # Populate notes/rests
        for n_item in notes:
            pitch_str = n_item.get("pitch", "rest")
            duration_str = n_item.get("duration", "quarter").lower()
            dur_val = DURATION_MAP.get(duration_str, 1.0)
            
            if pitch_str.lower() == "rest":
                r = note.Rest()
                r.quarterLength = dur_val
                m21_part.append(r)
            else:
                n = note.Note(pitch_str)
                n.quarterLength = dur_val
                m21_part.append(n)
                
        m21_score.append(m21_part)
        
        # Export score to MusicXML
        musicxml_path = assets_dir / "score.musicxml"
        m21_score.write("musicxml", fp=str(musicxml_path))
        
        # Make relative paths from project root for portability
        rel_piano_roll = piano_roll_path.relative_to(project_root).as_posix()
        rel_score_xml = musicxml_path.relative_to(project_root).as_posix()
        
        print(json.dumps({
            "status": "success",
            "piano_roll": rel_piano_roll,
            "score_xml": rel_score_xml
        }, indent=2))
        sys.exit(0)
        
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
