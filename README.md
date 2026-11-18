# Open Game Studio

An MIT-licensed local runner for developing games with Unity or Godot and one or more AI providers. Start a blank game, generate the playable **Beacon Relay** graybox, or adopt an existing project. Use the agents and tool licenses you already have.

## Quick start

Install [Python 3.10 or newer](https://www.python.org/downloads/) and [Git](https://git-scm.com/downloads). After cloning or downloading this repository, run the wizard from its root:

```sh
python studio.py --project "../My Game" setup
python studio.py --project "../My Game" doctor
python studio.py --project "../My Game" plan
```

Use `py -3` on Windows or `python3` on macOS/Linux if your Python launcher has that name. Paths with spaces should be quoted. The runner has no Python package dependencies.

The wizard detects an existing Unity or Godot project. For a new project, choose the engine and either a blank project or the Beacon Relay graybox. It checks common install locations and PATH, shows official install links for missing tools, and asks you to sign in to the selected agent CLIs. Install and activate editor software through its vendor. Rerun setup if a tool needs an explicit executable path:

```sh
python studio.py --project "../My Game" setup --engine godot --template beacon --agents codex claude --non-interactive
python studio.py --project "../My Game" setup --tool "godot=/absolute/path/to/godot"
```

For Unity, install Unity Hub and the patch listed in `ProjectSettings/ProjectVersion.txt`; the starter is pinned to **6000.3.12f1** and uses the Built-in Render Pipeline for its small graybox. Use Unity Hub to install Windows Build Support for the sample build where needed. Existing projects keep their renderer, editor version, and packages. Use `--tool unity=PATH` for a nonstandard install. For Godot use Godot 4.x; the starter uses the Compatibility renderer and was tested with 4.5.1. Install matching export templates separately to package a Godot desktop build.

The Python runner is portable across Windows, macOS, and Linux where your selected tools are available. Each engine and AI CLI has its own OS and hardware requirements. Photoshop desktop jobs require a supported Windows/macOS system and an active Adobe installation. Blender, Photoshop and FFmpeg are optional until a job needs them. A low-spec machine can run the Godot graybox first.

## Existing or older games

Point `--project` at the directory containing `project.godot` or the Unity `Assets`, `Packages`, and `ProjectSettings` directories. Setup writes local configuration under `.studio/` and preserves the engine and gameplay files. Use the matching engine version and work on a backup, clean branch, or disposable copy. Legacy Godot 3 projects require their original editor and project-specific workflows. The Beacon template is for Godot 4.

Jobs can edit the project using the permissions of their selected CLI. Review untrusted project instructions, local executable overrides, and files before running a job. Providers can receive the brief and project content accessed by their CLI. Keep credentials outside game files and review the artifacts you share across providers. `doctor` checks executable discovery; sign-in and license validity are checked by the tools themselves.

## Providers and roles

| Configuration | Default assignment |
|---|---|
| One provider | All roles share the subscription or account, with a fresh invocation per job. |
| Two providers | First owns design and Unity/Godot changes. Second handles model, UI, audio, QA and marketing jobs. |
| Three or more providers | First owns design and game integration, second handles asset production and marketing, third handles QA. Route additional workers explicitly. |

Supported CLI adapters: [Codex](https://developers.openai.com/codex/cli/), [Claude Code](https://code.claude.com/docs/en/setup), and [Gemini CLI](https://geminicli.com/docs/get-started/installation/). Install and authenticate only the providers you can use. Provider terms, quotas, and usage charges still apply. All jobs have a timeout and persistent logs. Same-project dispatch is serial to avoid conflicting scene edits.

```sh
python studio.py --project "../My Game" setup --agents codex claude gemini --route qa=claude
python studio.py --project "../My Game" workflow examples/beacon-relay.md --dry-run
python studio.py --project "../My Game" job gameplay examples/beacon-relay.md
python studio.py --project "../My Game" workflow examples/beacon-relay.md --through qa
```

The workflow stages are producer, gameplay, world, models, UI, audio, integrator, QA, and marketing. Each adds its artifact directory to the next stage's inputs. It stops on a failed invocation or missing delivery report. QA must deliver a positive verdict to let a workflow advance. QA should be independently reviewed on the built player. The verdict is furnished by the agent and serves as a handoff gate. Review the resulting evidence before release. Marketing is opt-in through `--through marketing` or an individual job; publication is a creator action.

### Shared memory and quota failover

Each project keeps durable decisions and status in `.studio/memory.md`. Every agent receives its path and instructions to maintain it. Agents save partial work in the project and write `checkpoint.md` in their attempt folder as they go. Job folders keep attempts, logs and a `handoff.json` pointing to the accepted delivery. Keep secrets out of these files, since every enabled provider may read them.

Enable two or more signed-in providers with `setup --agents codex claude`. If the assigned provider reports a recognizable quota or rate-limit error, the runner retries that role with the next enabled provider. The backup sees the same project files, shared memory, completed stage artifacts, and prior attempt folders. It must deliver its own report and QA verdict where applicable. A quota-limited provider is skipped for the rest of that workflow run. Each new workflow can try it again.

If no backup can finish, the workflow stops with the project edits and checkpoints intact. Use `--from ROLE` and `--input` to point a later run at the relevant successful handoffs and interrupted attempt folder. This preserves saved files and checkpoints. Any reasoning or edits the provider never saved cannot be recovered.

Use `--from ROLE` plus repeated `--input PATH` to pick up work from prior jobs. To extend the system, supply `--provider-file providers.json` with an ID mapped to an argument list such as `{"my-agent":["/absolute/path/to/agent","--stdin"]}`. The custom executable receives a UTF-8 prompt on standard input and runs from the game directory. It should emit a process exit code and create the requested report. Select it with `--agents` and assign it with `--route ROLE=my-agent`. Provider-specific credentials live in their CLI or local environment. Reusable role instructions live in `roles.json`.

## Production and release

1. **Design:** Turn the brief into a level, game loop, asset inventory, rights requirements, and acceptance checks. Implement gameplay with graybox assets first.
2. **Models and animation:** Source through approved catalogs such as [Poly Haven](https://polyhaven.com/license), build in Blender, or use a mesh-generation provider with appropriate rights. Author or clean up rigs, collision, pivots, texture maps, and animation. Use FBX for Unity or GLB for Godot. The included Blender helper imports source meshes, checks evaluated triangle budgets, and exports FBX or GLB.
3. **UI and audio:** Keep layered PSD masters and export PNGs. Use the engine for live text, navigation and HUD state. Use Photoshop interactively for the initial pipeline, or connect [Adobe UXP](https://developer.adobe.com/photoshop/uxp/2022/ps-reference/) as a custom production tool. For sound, deliver WAV masters and a cue map; use [FFmpeg](https://ffmpeg.org/download.html) to inspect or convert clips. Review levels, looping, spatial cues and mix in-game.
4. **Integration:** Import derivatives by asset ID. Preserve Unity .meta files and use wrapper prefabs, or use equivalent inherited scenes in Godot. Keep source or job IDs, checksums, rights, attribution, and derivatives in an asset manifest. See [example manifest](examples/asset-manifest.json).
5. **Marketing:** Draft the hook, capture real gameplay from an approved build, create key art and crop variants, cut a trailer, and prepare draft store copy and credits. Verify [Steam graphical assets](https://partner.steamgames.com/doc/store/assets/standard) and the [Steam Content Survey](https://partner.steamgames.com/doc/gettingstarted/contentsurvey) if targeting Steam. Approve uploads and campaign spend yourself.

```sh
blender --background --disable-autoexec --python-exit-code 1 --python tools/prepare_model.py -- input.blend relay-core.glb --max-triangles 2500
```

The MIT license covers the studio code and included original templates. Assets you import or generate are governed by their own terms. The starter includes the model export helper and production job contracts. Configure your asset providers separately; Photoshop, generated audio, rig retargeting, and store uploads have guided handoffs.

## Test with Beacon Relay

Choose `--template beacon` during setup, then run:

```sh
python studio.py --project "../My Game" smoke --sample
```

- **Unity:** Runs the interaction scenario in the editor, creates the playable scene if needed, and builds `BeaconRelay.exe` in the printed smoke-job directory. Launch it on Windows or open the generated scene in Unity to check input and visuals.
- **Godot:** Runs the sample's headless interaction scenario. Open the project and press F6 with the Beacon scene open, or F5 to run the main scene.
- **Playthrough:** Move with arrows. Enter picks up the amber core and installs it at the relay. Verify the success state, then press R to reset. Try interacting before reaching the core.
- **First full production pass:** Use the [Beacon Relay brief](examples/beacon-relay.md) for a sourced environment kit, original hero prop, UI, cues, effects, and store materials. Replace the prop, change the HUD prompt, and soften the relay cue in a second revision. Verify both builds and keep each revision's evidence.
- **Existing projects:** `smoke` without `--sample` checks headless Godot import or Unity batch project load. Wire in project-specific test commands, graphics and packaged build checks for a full acceptance suite.

## Design references

- [OpenAI harness engineering](https://openai.com/index/harness-engineering/) for versioned working environments and execution evidence.
- [OpenGame](https://arxiv.org/abs/2604.18394) for reusable game templates and evaluation of running builds.
- [GameDevBench](https://proceedings.mlr.press/v306/chi26a.html) for visually grounded game development evaluation.
- [Game development techniques](https://github.com/AkaitoAi/game-development-techniques) for additional discipline-specific reading.
