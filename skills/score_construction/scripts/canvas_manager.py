#!/usr/bin/env python3
import sys
import json
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Deterministic score construction canvas manager.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-commands")

    # init sub-command
    init_parser = subparsers.add_parser("init", help="Initialize a blank canvas.")
    init_parser.add_argument("--time-signature", default="4/4", help="Time signature of the canvas (default '4/4')")

    # add sub-command
    add_parser = subparsers.add_parser("add", help="Add a note/rest token to the canvas.")
    add_parser.add_argument("--pitch", required=True, help="Pitch name (e.g. 'C4') or 'rest'")
    add_parser.add_argument("--duration", required=True, help="Duration (e.g. 'quarter', 'half', 'eighth')")

    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).parent.resolve()
    assets_dir = script_dir.parent / "assets"
    state_file = assets_dir / "canvas_state.json"

    try:
        if args.command == "init":
            # Ensure assets folder exists
            assets_dir.mkdir(parents=True, exist_ok=True)
            
            state = {
                "time_signature": args.time_signature,
                "notes": []
            }
            
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
                
            print(json.dumps({
                "status": "success",
                "action": "init",
                "time_signature": args.time_signature,
                "notes_count": 0
            }, indent=2))
            sys.exit(0)

        elif args.command == "add":
            if not state_file.is_file():
                raise FileNotFoundError(
                    "Canvas has not been initialized yet. Run 'init' first."
                )
                
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                
            new_note = {
                "pitch": args.pitch,
                "duration": args.duration
            }
            state["notes"].append(new_note)
            
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
                
            print(json.dumps({
                "status": "success",
                "action": "add",
                "added_note": new_note,
                "notes_count": len(state["notes"])
            }, indent=2))
            sys.exit(0)

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e),
            "notes_count": 0
        }, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
