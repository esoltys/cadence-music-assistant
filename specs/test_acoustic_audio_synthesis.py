import os
import sys
import re
import json
import asyncio
import warnings
from pathlib import Path

# Suppress the experimental JSON schema warning from google.adk tools
warnings.filterwarnings("ignore", category=UserWarning, module="google.adk")

# Add project root and agents directory to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "agents"))

# Import ADK elements
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.evaluation.eval_case import Invocation, IntermediateData
from google.adk.evaluation.eval_metrics import EvalMetric, ToolTrajectoryCriterion
from google.adk.evaluation.trajectory_evaluator import TrajectoryEvaluator
from google.genai import types

# Import agent app
from music_assistant.agent import app

def parse_gherkin_scenarios(feature_file_path: str):
    scenarios = []
    current_scenario = None
    
    with open(feature_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("Scenario:"):
                if current_scenario:
                    scenarios.append(current_scenario)
                current_scenario = {
                    "name": line[9:].strip(),
                    "canvas_path": None,
                    "expected_audio_path": None
                }
            elif current_scenario:
                # Given an active score canvas state at "skills/score_construction/assets/canvas_state.json"
                match_path = re.search(r'active score canvas state at "([^"]+)"', line)
                if match_path:
                    current_scenario["canvas_path"] = match_path.group(1)
                
                # And the response should confirm the output audio target path "skills/acoustic_audio_synthesis/assets/score.wav"
                match_audio = re.search(r'output audio target path "([^"]+)"', line)
                if match_audio:
                    current_scenario["expected_audio_path"] = match_audio.group(1)
                    
        if current_scenario:
            scenarios.append(current_scenario)
            
    return scenarios

async def run_evaluation():
    feature_file = PROJECT_ROOT / "specs" / "acoustic_audio_synthesis.feature"
    print(f"Reading Gherkin scenarios from: {feature_file}\n")
    scenarios = parse_gherkin_scenarios(str(feature_file))
    
    # Initialize Runner
    runner = Runner(
        app=app,
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
        auto_create_session=True
    )
    
    # Setup TrajectoryEvaluator with IN_ORDER
    criterion = ToolTrajectoryCriterion(
        threshold=1.0,
        match_type=ToolTrajectoryCriterion.MatchType.IN_ORDER
    )
    eval_metric = EvalMetric(
        metric_name="trajectory_accuracy",
        criterion=criterion
    )
    evaluator = TrajectoryEvaluator(eval_metric=eval_metric)
    
    scoring_blocks = []
    
    for idx, sc in enumerate(scenarios):
        print(f"==================================================")
        print(f"Running Scenario {idx+1}: {sc['name']}")
        print(f"==================================================")
        
        session_id = f"eval-session-{idx}"
        canvas_path_str = sc["canvas_path"].replace("{session_id}", session_id)
        canvas_file = PROJECT_ROOT / canvas_path_str
        print(f"Pre-loading canvas state file: {canvas_file}")
        canvas_file.parent.mkdir(parents=True, exist_ok=True)
        
        test_state = {
            "time_signature": "4/4",
            "key_signature": "C Major",
            "parts": [
                {
                    "id": "melody",
                    "name": "Melody",
                    "clef": "treble",
                    "measures": [
                        {
                            "number": 1,
                            "events": [
                                {"pitches": ["C4"], "duration": "quarter"},
                                {"pitches": ["E4"], "duration": "quarter"},
                                {"pitches": ["G4"], "duration": "quarter"},
                                {"pitches": ["C5"], "duration": "quarter"}
                            ]
                        },
                        {
                            "number": 2,
                            "events": [
                                {"pitches": ["D5"], "duration": "eighth"},
                                {"pitches": ["C5"], "duration": "eighth"},
                                {"pitches": ["B4"], "duration": "quarter"},
                                {"pitches": ["A4"], "duration": "half"}
                            ]
                        },
                        {
                            "number": 3,
                            "events": [
                                {"pitches": ["G4"], "duration": "half"},
                                {"pitches": ["C4"], "duration": "whole"}
                            ]
                        }
                    ]
                }
            ]
        }
        with open(canvas_file, "w", encoding="utf-8") as f:
            json.dump(test_state, f, indent=2)
        print("Canvas file pre-loaded with a rich melody.")

        query = "Convert the active canvas notes into a piano WAV file."
        print(f"Query: '{query}'")
        
        # Define expected tool call
        expected_tool_call = types.FunctionCall(
            name="synthesize_score",
            args={}
        )
        
        expected_invocation = Invocation(
            invocation_id=f"inv_{idx}",
            user_content=types.Content(role="user", parts=[types.Part.from_text(text=query)]),
            final_response=None,
            intermediate_data=IntermediateData(
                tool_uses=[expected_tool_call]
            )
        )
        
        # Run agent
        user_id = "eval-user"
        new_message = types.Content(
            role="user",
            parts=[types.Part(text=query)]
        )
        
        # Run natively using async generator
        response_stream = runner.run_async(
            user_id="eval-user",
            session_id=session_id,
            new_message=new_message
        )
        
        actual_tool_calls = []
        response_text = ""
        
        # Process response stream
        async for event in response_stream:
            if hasattr(event, "message") and event.message and event.message.parts:
                for part in event.message.parts:
                    if part.text:
                        response_text += part.text
                    if part.function_call:
                        actual_tool_calls.append(part.function_call)
                        
        print(f"\nRaw Agent Response:\n{response_text.strip()}\n")
        print(f"Actual Tool Calls: {actual_tool_calls}")
        
        actual_invocation = Invocation(
            invocation_id=f"inv_{idx}",
            user_content=new_message,
            final_response=types.Content(role="model", parts=[types.Part(text=response_text)]),
            intermediate_data=IntermediateData(
                tool_uses=actual_tool_calls
            )
        )
        
        # Evaluate trajectory
        eval_result = evaluator.evaluate_invocations(
            actual_invocations=[actual_invocation],
            expected_invocations=[expected_invocation]
        )
        trajectory_score = eval_result.overall_score
        
        # Evaluate response text assertions
        response_passed = True
        reasons = []
        
        expected_path = sc["expected_audio_path"].replace("{session_id}", session_id).replace("\\", "/")
        normalized_response = response_text.replace("\\", "/")
        
        if expected_path not in normalized_response:
            response_passed = False
            reasons.append(f"Expected output audio path '{expected_path}' not in response")
                
        response_score = 1.0 if response_passed else 0.0
        
        scoring_blocks.append({
            "scenario": sc["name"],
            "trajectory_score": trajectory_score,
            "response_score": response_score,
            "reasons": reasons
        })
        
    print(f"\n==================================================")
    print(f"FINAL VALIDATION SCORING BLOCKS")
    print(f"==================================================")
    for block in scoring_blocks:
        print(f"Scenario: {block['scenario']}")
        print(f"  Trajectory Validation (IN_ORDER):  {block['trajectory_score'] * 100}%")
        print(f"  Response Assertion Validation:     {block['response_score'] * 100}%")
        if block["reasons"]:
            print(f"  Fail Reasons: {block['reasons']}")
        print()

if __name__ == "__main__":
    asyncio.run(run_evaluation())
