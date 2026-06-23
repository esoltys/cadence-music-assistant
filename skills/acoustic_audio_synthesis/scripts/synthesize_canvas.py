#!/usr/bin/env python3
import sys
import json
import re
import math
import struct
import wave
import argparse
from pathlib import Path

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

def midi_to_freq(midi_num):
    if midi_num is None:
        return 0.0
    return 440.0 * (2.0 ** ((midi_num - 69) / 12.0))

def main():
    parser = argparse.ArgumentParser(description="Synthesize canvas state to WAV audio.")
    parser.add_argument("--canvas-path", help="Path to the canvas state JSON file")
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent.parent.parent.resolve()
    
    if args.canvas_path:
        canvas_path = Path(args.canvas_path)
    else:
        canvas_path = project_root / "skills" / "score_construction" / "assets" / "canvas_state.json"
        
    assets_dir = script_dir.parent / "assets"
    output_file = assets_dir / "score.wav"
    
    try:
        if not canvas_path.is_file():
            raise FileNotFoundError(f"Canvas state file not found: {canvas_path}")
            
        with open(canvas_path, "r", encoding="utf-8") as f:
            state = json.load(f)
            
        notes = state.get("notes", [])
        if not notes:
            raise ValueError("Canvas has no notes to synthesize.")
            
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        sample_rate = 44100
        volume = 0.5
        decay_rate = 3.0
        
        audio_data = bytearray()
        
        for note_item in notes:
            pitch_str = note_item.get("pitch", "rest")
            duration_str = note_item.get("duration", "quarter").lower()
            dur_beats = DURATION_MAP.get(duration_str, 1.0)
            
            # Map beats to seconds (assuming 120 BPM: 1 beat = 0.5 seconds)
            dur_seconds = dur_beats * 0.5
            
            midi_num = pitch_to_midi(pitch_str)
            freq = midi_to_freq(midi_num)
            
            num_samples = int(dur_seconds * sample_rate)
            
            for i in range(num_samples):
                t = i / sample_rate
                if freq > 0.0:
                    # Sine wave modulated by exponential decay
                    val = math.sin(2.0 * math.pi * freq * t) * math.exp(-decay_rate * t)
                    sample = int(val * 32767 * volume)
                else:
                    sample = 0
                
                # Clip to 16-bit bounds
                sample = max(-32768, min(32767, sample))
                audio_data.extend(struct.pack('<h', sample))
                
        # Write WAV file
        with wave.open(str(output_file), 'wb') as wav_file:
            wav_file.setnchannels(1)      # Mono
            wav_file.setsampwidth(2)     # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
            
        abs_path = str(output_file.resolve().as_posix())
        print(json.dumps({
            "status": "success",
            "audio_path": abs_path
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
