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
                    "expected_image_path": None
                }
            elif current_scenario:
                # Given an active score canvas state at "skills/score_construction/assets/canvas_state.json"
                match_path = re.search(r'active score canvas state at "([^"]+)"', line)
                if match_path:
                    current_scenario["canvas_path"] = match_path.group(1)
                
                # And the response should confirm the output image target path "skills/visual_notation_rendering/assets/score_plot.png"
                match_image = re.search(r'output image target path "([^"]+)"', line)
                if match_image:
                    current_scenario["expected_image_path"] = match_image.group(1)
                    
        if current_scenario:
            scenarios.append(current_scenario)
            
    return scenarios

async def run_evaluation():
    feature_file = PROJECT_ROOT / "specs" / "visual_notation_rendering.feature"
    print(f"Reading Gherkin scenarios from: {feature_file}\n")
    scenarios = parse_gherkin_scenarios(str(feature_file))
    
    # Initialize Runner
    runner = Runner(
        app=app,
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
        auto_create_session=True
    )
    
    # Setup TrajectoryEvaluator with ANY_ORDER
    criterion = ToolTrajectoryCriterion(
        threshold=1.0,
        match_type=ToolTrajectoryCriterion.MatchType.ANY_ORDER
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
        
        # Ensure canvas state file exists and has data (e.g. a rich multi-note melody)
        canvas_file = PROJECT_ROOT / sc["canvas_path"]
        print(f"Pre-loading canvas state file: {canvas_file}")
        canvas_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Always write a rich test state to guarantee a robust multi-note validation
        test_state = {
            "time_signature": "4/4",
            "notes": [
                {"pitch": "C4", "duration": "quarter"},
                {"pitch": "E4", "duration": "quarter"},
                {"pitch": "G4", "duration": "quarter"},
                {"pitch": "C5", "duration": "quarter"},
                {"pitch": "D5", "duration": "eighth"},
                {"pitch": "C5", "duration": "eighth"},
                {"pitch": "B4", "duration": "quarter"},
                {"pitch": "A4", "duration": "half"},
                {"pitch": "G4", "duration": "half"},
                {"pitch": "C4", "duration": "whole"}
            ]
        }
        with open(canvas_file, "w", encoding="utf-8") as f:
            json.dump(test_state, f, indent=2)
        print(f"Canvas file pre-loaded with a rich melody of {len(test_state['notes'])} notes.")

        query = "Render the active score canvas to an image and show the visualization of the current notes."
        print(f"Query: '{query}'")
        
        # Define expected tool call
        expected_tool_call = types.FunctionCall(
            name="render_notation",
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
        session_id = f"eval-session-{idx}"
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
        
        # Expect the output image target path (e.g. skills/visual_notation_rendering/assets/score_plot.png) in response
        # Normalize paths for comparison (forward slashes)
        expected_path = sc["expected_image_path"].replace("\\", "/")
        normalized_response = response_text.replace("\\", "/")
        
        if expected_path not in normalized_response:
            response_passed = False
            reasons.append(f"Expected output image path '{expected_path}' not in response")
            
        # Verify that it is formatted as an inline Markdown image link, i.e., ![Alt Text](path)
        markdown_image_pattern = r"!\[[^\]]*\]\(" + re.escape(expected_path) + r"\)"
        if not re.search(markdown_image_pattern, normalized_response):
            response_passed = False
            reasons.append(f"Expected output image path '{expected_path}' to be formatted as an inline Markdown image link (e.g. ![Score Plot]({expected_path}))")
            
        # Verify MusicXML path is mentioned in response
        expected_xml = "skills/visual_notation_rendering/assets/score.musicxml"
        if expected_xml not in normalized_response:
            response_passed = False
            reasons.append(f"Expected MusicXML path '{expected_xml}' not in response")
            
        # Verify MuseScore/inspection is mentioned
        if "musescore" not in normalized_response.lower() and "inspection" not in normalized_response.lower():
            response_passed = False
            reasons.append("Expected MuseScore or inspection notification in response")
                
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
        print(f"  Trajectory Validation (ANY_ORDER): {block['trajectory_score'] * 100}%")
        print(f"  Response Assertion Validation:    {block['response_score'] * 100}%")
        if block["reasons"]:
            print(f"  Fail Reasons: {block['reasons']}")
        print()

if __name__ == "__main__":
    asyncio.run(run_evaluation())
