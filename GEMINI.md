# Coding Agent Guide

## Prerequisites

Install the CLI (one-time):
```bash
uv tool install google-agents-cli
```

---

## Development Phases

### Phase 1: Understand Requirements
Before writing any code, understand the project's requirements, constraints, and success criteria.

### Phase 2: Build and Implement
Implement agent logic in `app/`. Use `agents-cli playground` for interactive testing. Iterate based on user feedback.

### Phase 3: The Evaluation Loop (Main Iteration Phase)
Start with 1-2 eval cases, run `agents-cli eval generate`, then `agents-cli eval grade`, iterate by making changes and rerunning both commands until satisfied. Expect 5-10+ iterations. Once you have a baseline, reach for `agents-cli eval compare` (regression diffs), `agents-cli eval analyze` (cluster failure modes), and `agents-cli eval optimize` (auto-tune prompts). See the **Evaluation Guide** for metrics, dataset schema, LLM-as-judge config, and common gotchas.

### Phase 4: Pre-Deployment Tests
Run `uv run pytest tests/unit tests/integration`. Fix issues until all tests pass.

### Phase 5: Deploy to Dev
**Requires explicit human approval.** Run `agents-cli deploy` only after user confirms. See the **Deployment Guide** for details.

### Phase 6: Production Deployment
Ask the user: Option A (simple single-project) or Option B (full CI/CD pipeline with `agents-cli infra cicd`).

## Development Commands

| Command | Purpose |
|---------|---------|
| `agents-cli playground` | Interactive local testing |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests |
| `agents-cli eval dataset synthesize` | Synthesize multi-turn eval scenarios for your agent |
| `agents-cli eval generate` | Run agent on eval dataset, produce traces |
| `agents-cli eval grade` | Run agent evaluations on the traces |
| `agents-cli eval compare` | Compare two grade-results files (regression check) |
| `agents-cli eval analyze` | Cluster failure modes from grade results |
| `agents-cli eval metric list` | List built-in metrics available in the SDK |
| `agents-cli eval optimize` | Auto-tune agent prompts using eval data |
| `agents-cli lint` | Check code quality |
| `agents-cli infra single-project` | Set up project infrastructure (Terraform) |
| `agents-cli deploy` | Deploy to dev |
| `agents-cli scaffold enhance` | Add deployment target or CI/CD to project |
| `agents-cli scaffold upgrade` | Upgrade project to latest version |

---

## Operational Guidelines for Coding Agents

- **Code preservation**: Only modify code directly targeted by the user's request. Preserve all surrounding code, config values (e.g., `model`), comments, and formatting.
- **NEVER change the model** unless explicitly asked.
- **Model 404 errors**: Fix `GOOGLE_CLOUD_LOCATION` (e.g., `global` instead of `us-east1`), not the model name.
- **ADK tool imports**: Import the tool instance, not the module: `from google.adk.tools.load_web_page import load_web_page`
- **Run Python with `uv`**: `uv run python script.py`. Run `agents-cli install` first.
- **Stop on repeated errors**: If the same error appears 3+ times, fix the root cause instead of retrying.
- **Terraform conflicts** (Error 409): Use `terraform import` instead of retrying creation.

---

## Cadence-Specific Architectural Patterns & Lessons Learned

### State & Session Management
- **Local JSON State Stores**: Score states are tracked sequentially in JSON files under `skills/score_construction/assets/score_{session_id}.json`. When implementing tools or modifications, locate the score file and ensure changes are safely appended or mutated within the correct session context.
- **Session IDs**: The unique ID should be fetched via `tool_context.session.id` or passed as `session_id`. Stale state assets should be proactively deleted (e.g., when rendering visual notation files) to prevent cross-run interference.

### Input Sanitization & Path Traversal Guards
- **Path Resolution**: Always resolve files using `_safe_resolve_path(user_path)` to ensure paths remain locked inside allowed roots (`_PROJECT_ROOT`, home directories, Downloads, Desktop, Documents).
- **Subprocess Argument Caps**: Truncate all string arguments passed to subprocess scripts using `_sanitize_arg(value)` (standard cap is 256 characters, or up to 4096 for ABC/TinyNotation notation strings) to prevent excessive buffering and ensure robust error messages.
- **Unpitched Percussion & Soundfonts**: Restrict user-supplied soundfont path strings to prevent directory traversal by stripping everything except the filename (e.g., `Path(name).name`) and appending it to `soundfonts/`.

### Subprocess Execution of Skills
- **Virtual Environment Resolving**: In tools that run scripts under `skills/`, find the python binary dynamically (e.g., checking `.venv/Scripts/python.exe` on Windows and `.venv/bin/python` on POSIX, before falling back to `sys.executable` or `"python"`).
- **Ignore Subprocess Warnings**: Run scripts with `-W ignore` flags (e.g., `python -W ignore script.py`) to prevent deprecation warnings or warning outputs from corrupting the returned JSON stdout payload.
- **MimeType & Base64 Attachments**: When decoding user attachments (like `.mid` files), utilize `_safe_decode_base64()`. Ensure it handles potential URL data prefixes (e.g., `data:audio/midi;base64,...`), strips whitespace and extraneous backslashes/quotes, and fixes missing base64 padding.

### Rendering & Output Formatting
- **Visual Aid Embedding**: When the model or tools render piano rolls, chord fretboards, or keyboard layouts, save them to the appropriate assets directory. The agent response should reference these assets inline as Markdown images using the relative path returned by the tool (e.g., `![Piano Roll](skills/visual_notation_rendering/assets/piano_roll_{session_id}.png)`).
- **No Direct file:// Links**: Never print raw local paths or `file://` URLs in response texts. The chat UI automatically processes file attachments (such as `.mid` or `.wav` files) and sheet music (such as `.musicxml` files) and displays them to the user inline or in the Artifacts panel.

