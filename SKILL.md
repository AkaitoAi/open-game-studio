---
name: open-game-studio
description: Multi-agent game production runner for Unity and Godot with shared project memory, automated provider quota failover, and playbook learning across Codex, Claude, and Gemini. Use when orchestrating game development across agents, planning game milestones, running production workflows, or diagnosing game studio tools.
---

# Open Game Studio

Open Game Studio is an MIT-licensed local runner for multi-agent game production with Unity or Godot. It orchestrates AI agent CLIs (Codex, Claude Code, Gemini CLI, or custom providers) across a structured 9-stage game production pipeline, provides automated quota failover between providers, maintains persistent project memory across runs and Git checkouts, and learns from verified job outcomes through a shared playbook.

## Repository & Installation

- **Local Path**: `D:\Test Projects\_Tools\open-game-studio`
- **GitHub**: `https://github.com/AkaitoAi/open-game-studio`
- **Global Command**: `open-game-studio` or `studio` (or `python "D:/Test Projects/_Tools/open-game-studio/studio.py"`)

## Supported Engines & AI Providers

- **Game Engines**:
  - **Unity**: Verified on Unity 6 (6000.3.12f1 Built-in Render Pipeline baseline or existing URP/HDRP projects).
  - **Godot**: Verified on Godot 4.x (4.5.1 Compatibility or Forward+ renderer).
- **Supported AI Providers**:
  - `codex`: OpenAI Codex CLI (`codex exec --json --sandbox workspace-write -`)
  - `claude`: Anthropic Claude Code CLI (`claude -p --output-format json --permission-mode acceptEdits`)
  - `gemini`: Google Gemini CLI (`gemini --output-format json --approval-mode auto_edit`)
  - Custom providers via `--provider-file`
- **Detected Production Tools**:
  - Blender 5.3 (model export helper `tools/prepare_model.py`)
  - Adobe Photoshop (layered PSD masters & UI derivatives)
  - FFmpeg (audio conversion & inspection)

## Studio Roles & Pipeline Stages

Workflows advance through up to nine sequential roles:
1. `producer`: Scoped game design brief, creative direction, milestone plan, acceptance checks.
2. `gameplay`: Core game loop and mechanics in Unity or Godot with focused tests.
3. `world`: Level design, lighting, camera, environment, collision, navigation, scene edits.
4. `models`: 3D assets via Poly Haven, Blender, or mesh generators (FBX for Unity, GLB for Godot).
5. `ui`: Accessible HUD, menus, layout notes, PNG derivatives from PSD masters.
6. `audio`: Cue map, mixer groups, WAV masters, playback/gain notes.
7. `integrator`: Preserves engine asset references, wires UI and audio, builds playable revision.
8. `qa`: Independent reproducible gameplay checks; must emit passing `verdict.json` (`{"passed": true}`) to advance.
9. `marketing`: Store copy, hook, trailer shot list, layered key art, store/social variants.

## Core Commands

### 1. Initialize or Adopt a Project
```bash
# New or adopted Unity project
open-game-studio --project "D:/MyGame" setup --engine unity --agents codex claude gemini --non-interactive

# New or adopted Godot project
open-game-studio --project "D:/MyGame" setup --engine godot --agents codex claude gemini --non-interactive

# Check discovery of all engines, CLIs, and tools
open-game-studio --project "D:/MyGame" doctor

# Run engine smoke check (headless Godot import or Unity batch load)
open-game-studio --project "D:/MyGame" smoke
```

### 2. View Planned Role Assignments
```bash
open-game-studio --project "D:/MyGame" plan
```

### 3. Run Production Workflows
```bash
# Run full workflow through QA gate
open-game-studio --project "D:/MyGame" workflow "brief.md" --through qa

# Dry-run workflow without invoking providers
open-game-studio --project "D:/MyGame" workflow "brief.md" --dry-run

# Run targeted single-role job
open-game-studio --project "D:/MyGame" job gameplay "brief.md"
open-game-studio --project "D:/MyGame" job models "brief.md"
open-game-studio --project "D:/MyGame" job qa "brief.md"
```

### 4. Shared Memory & Quota Failover
- Each project keeps durable shared memory in `.studio/memory.md`.
- Each job attempt maintains `checkpoint.md` and `memory.json`.
- When an active provider returns 429 / rate-limit / quota exhausted error, the runner automatically fails over to the next configured provider, passing prior attempt artifacts and checkpoints.
- Project history is recorded in `StudioMemory/*.json`.
- Automatic Git commits for project memory can be enabled with `--memory-commit`.

### 5. Playbook Learning Loop
- Agents propose reusable rules and evidence in `memory.json`.
- Creators view and approve lessons:
```bash
open-game-studio --project "D:/MyGame" learn list
open-game-studio --project "D:/MyGame" learn approve <RECORD_ID> <INDEX> [--all-roles]
open-game-studio --project "D:/MyGame" learn retire <RECORD_ID> <INDEX>
```
Approved lessons are stored in `StudioMemory/Playbook/` and automatically supplied to future jobs for the relevant role.

## Companion Resources
- Techniques Reference: `https://github.com/AkaitoAi/game-development-techniques` (or local skill `game-development-techniques`)
