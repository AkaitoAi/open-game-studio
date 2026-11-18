"""Portable local game production runner. Python 3.10+; no dependencies."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
from argparse import Namespace

HERE = Path(__file__).resolve().parent
PROVIDERS = {
    "codex": ["codex", "exec", "--json", "--sandbox", "workspace-write", "-"],
    "claude": ["claude", "-p", "--output-format", "json", "--permission-mode", "acceptEdits"],
    "gemini": ["gemini", "--output-format", "json", "--approval-mode", "auto_edit"],
}
LINKS = {
    "unity": "https://unity.com/download",
    "godot": "https://godotengine.org/download/",
    "blender": "https://www.blender.org/download/",
    "photoshop": "https://www.adobe.com/products/photoshop.html",
    "ffmpeg": "https://ffmpeg.org/download.html",
    "git": "https://git-scm.com/downloads",
    "codex": "https://developers.openai.com/codex/cli/",
    "claude": "https://code.claude.com/docs/en/setup",
    "gemini": "https://geminicli.com/docs/get-started/installation/",
}
ROLES = json.loads((HERE / "roles.json").read_text(encoding="utf-8"))
STAGES = ("producer", "gameplay", "world", "models", "ui", "audio", "integrator", "qa", "marketing")


def detect_engine(root):
    known = []
    if (root / "project.godot").is_file():
        known.append("godot")
    if (root / "ProjectSettings/ProjectVersion.txt").is_file() and (
        root / "Packages/manifest.json"
    ).is_file() and (root / "Assets").is_dir():
        known.append("unity")
    if len(known) > 1:
        raise ValueError("Both engine markers found. Select a single engine project directory.")
    return next(iter(known), None)


def executable(name, root=None):
    aliases = {"godot": ("godot", "godot4", "Godot"), "photoshop": ("Photoshop",)}
    picks = aliases.get(name, (name,))
    for alias in picks if name != "unity" else ():
        hit = shutil.which(alias)
        if hit and Path(hit).suffix.lower() != ".ps1":
            return hit

    version = "*"
    if name == "unity" and root:
        file = root / "ProjectSettings/ProjectVersion.txt"
        if file.is_file():
            version = file.read_text(encoding="utf-8").splitlines()[0].split()[-1]

    locations = {
        "unity": [("ProgramFiles", f"Unity/Hub/Editor/{version}/Editor/Unity.exe"),
                  (None, f"/Applications/Unity/Hub/Editor/{version}/Unity.app/Contents/MacOS/Unity"),
                  (None, f"~/Unity/Hub/Editor/{version}/Editor/Unity")],
        "blender": [("ProgramFiles", "Blender Foundation/Blender */blender.exe"),
                    (None, "/Applications/Blender.app/Contents/MacOS/Blender")],
        "godot": [(None, "/Applications/Godot.app/Contents/MacOS/Godot")],
        "photoshop": [("ProgramFiles", "Adobe/Adobe Photoshop */Photoshop.exe"),
                      (None, "/Applications/Adobe Photoshop */Adobe Photoshop *.app/Contents/MacOS/Adobe Photoshop *")],
    }
    for env, pattern in locations.get(name, []):
        if env and not os.environ.get(env):
            continue
        path = Path(os.environ[env]) / pattern if env else Path(pattern).expanduser()
        matches = sorted(Path(path.anchor).glob(str(path.relative_to(path.anchor))), reverse=True)
        for candidate in matches:
            if candidate.is_file():
                return str(candidate)
    return shutil.which("unity") if name == "unity" and version == "*" else None


def read_config(root):
    return json.loads((root / ".studio/config.json").read_text(encoding="utf-8"))


def write_config(root, config):
    directory = root / ".studio"
    directory.mkdir(exist_ok=True)
    (directory / ".gitignore").write_text("*\n", encoding="utf-8")
    target = directory / "config.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def route(providers):
    # Keep a primary implementation owner. Put independent specialties on other accounts.
    groups = {"producer": 0, "gameplay": 0, "world": 0, "integrator": 0,
              "models": 1, "ui": 1, "audio": 1, "marketing": 1, "qa": 2}
    return {role: providers[(1 if group == 2 and len(providers) == 2 else group) % len(providers)]
            for role, group in groups.items()}


def custom_providers(config):
    return config.get("custom_providers", {})


def setup(args, root):
    old = detect_engine(root)
    config_path = root / ".studio/config.json"
    previous = read_config(root) if config_path.is_file() else {}
    custom = dict(custom_providers(previous))
    for definition in args.provider_file:
        data = json.loads(Path(definition).read_text(encoding="utf-8"))
        for name, argv in data.items():
            if (not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", name) or name in LINKS
                    or not isinstance(argv, list) or not argv
                    or any(not isinstance(part, str) or not part for part in argv)
                    or not Path(argv[0]).expanduser().is_absolute()
                    or not Path(argv[0]).expanduser().is_file()):
                raise ValueError("Custom providers require a unique ID and an absolute executable with arguments.")
            custom[name] = [str(Path(argv[0]).expanduser().resolve()), *argv[1:]]
    engine = args.engine or old
    providers = list(dict.fromkeys(args.agents or previous.get("providers", [])))
    if args.non_interactive and (not engine or not providers):
        raise ValueError("Non-interactive setup requires an engine and at least one agent.")
    if not engine:
        engine = input("Engine [unity/godot]: ").strip().lower()
    if not providers:
        providers = list(dict.fromkeys(input(
            "Subscribed or otherwise authorized agents, in priority order [codex claude gemini]: "
        ).lower().split()))
    if engine not in ("unity", "godot") or (old and old != engine):
        raise ValueError("Select the engine matching the project, or choose an empty directory.")
    if not providers or any(provider not in PROVIDERS and provider not in custom for provider in providers):
        raise ValueError("Choose at least one of codex, claude, gemini, or a configured custom provider.")
    tools = dict(previous.get("tools", {}))
    roles = previous.get("roles", {}) if providers == previous.get("providers") else route(providers)
    for mapping in args.route:
        role, sep, provider = mapping.partition("=")
        if not sep or role not in ROLES or provider not in providers:
            raise ValueError(f"Expected --route ROLE=SELECTED_PROVIDER, got {mapping!r}.")
        roles[role] = provider
    for mapping in args.tool:
        name, sep, path = mapping.partition("=")
        if not sep or name not in LINKS or not Path(path).expanduser().is_file():
            raise ValueError(f"Expected --tool TOOL=EXISTING_EXECUTABLE, got {mapping!r}.")
        tools[name] = str(Path(path).expanduser().resolve())
    sample = previous.get("sample", False)
    if not old:
        if root.exists() and any(item.name != ".git" for item in root.iterdir()):
            raise ValueError("A new project requires an empty directory or an empty Git repository.")
        template = args.template
        if template is None and not args.non_interactive:
            template = input("Project template [blank/beacon, default blank]: ").strip().lower()
        template = template or "blank"
        if template not in {"blank", "beacon"}:
            raise ValueError("Select blank or beacon.")
        shutil.copytree(HERE / "templates" / engine, root, dirs_exist_ok=True)
        sample = template == "beacon"
        if not sample and engine == "unity":
            shutil.rmtree(root / "Assets" / "Editor")
            (root / "Assets" / "BeaconGame.cs").unlink()
        if not sample and engine == "godot":
            (root / "beacon.tscn").unlink()
            (root / "beacon.gd").unlink()
            project_file = root / "project.godot"
            project_file.write_text(project_file.read_text(encoding="utf-8")
                                    .replace('config/name="Beacon Relay"', 'config/name="New Game"')
                                    .replace('run/main_scene="res://beacon.tscn"\n', ''), encoding="utf-8")
    config = {"engine": engine, "providers": providers, "roles": roles, "tools": tools,
              "custom_providers": custom, "sample": sample}
    write_config(root, config)
    print(f"{engine} project at {root}")
    if engine == "unity":
        print("Use the editor patch in ProjectSettings/ProjectVersion.txt; activate it via Unity Hub.")
        if config["sample"]:
            print("The first Unity smoke run generates the playable Beacon Relay scene.")
    print("Sign in to each selected CLI with your own account before running jobs.")
    doctor(root, config)


def doctor(root, config):
    needed = [config["engine"], "git", *config["providers"]]
    optional = ["blender", "photoshop", "ffmpeg"]
    for name in needed + optional:
        path = tool_path(root, config, name)
        if path and Path(path).is_file():
            print(f"{name}: {path}")
        else:
            kind = "required" if name in needed else "optional"
            if name in LINKS:
                print(f"{name} ({kind}): install from {LINKS[name]} and rerun setup with --tool {name}=PATH if needed")
            else:
                print(f"{name} ({kind}): check the executable in your custom provider definition.")
    print("Detection checks paths only. Verify engine licensing and agent login with the installed tools.")


def tool_path(root, config, name):
    custom = custom_providers(config).get(name)
    return custom[0] if custom else config["tools"].get(name) or executable(name, root)


def command_for(root, config, name):
    path = tool_path(root, config, name)
    if not path or not Path(path).is_file():
        raise ValueError(f"{name} executable missing. Run doctor or set it with setup --tool.")
    # Windows npm installations expose .cmd shims; prompt contents always go through stdin.
    if os.name == "nt" and Path(path).suffix.lower() in (".cmd", ".bat"):
        if any(character in path for character in '%!&|<>^"'):
            raise ValueError("Use an executable or a CLI shim path without shell metacharacters.")
        return ["cmd.exe", "/d", "/c", path]
    return [path]


def job_folder(root, role):
    directory = root / ".studio/jobs" / f"{role}-{uuid.uuid4().hex[:12]}"
    directory.mkdir(parents=True)
    return directory


QUOTA_ERROR = re.compile(
    r"\b(?:429|rate[_ -]?limit(?:ed|[_ -]?exceeded|[_ -]?error)?|"
    r"usage[_ -]?limit|insufficient[_ -]?quota|quota[_ -]?exceeded|"
    r"hit your (?:limit|usage limit)|out of (?:credits|quota)|"
    r"reached your (?:usage )?limit|resource[_ -]?exhausted)\b", re.IGNORECASE
)


def quota_failure(directory, code):
    # Only inspect provider error events and failing CLI diagnostics.
    with (directory / "stdout.log").open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            if (event.get("type") in {"error", "turn.failed", "rate_limit_event"}
                    or event.get("is_error") is True or event.get("error")):
                if event.get("type") == "rate_limit_event":
                    info = event.get("rate_limit_info")
                    if isinstance(info, dict) and info.get("status") == "rejected":
                        return True
                    continue
                detail = {key: event[key] for key in ("error", "message", "result", "errors", "message_type")
                          if key in event}
                if QUOTA_ERROR.search(json.dumps(detail)):
                    return True
    if code not in (0, 124):
        with (directory / "stderr.log").open("rb") as stream:
            stream.seek(max(0, stream.seek(0, os.SEEK_END) - 65536))
            return bool(QUOTA_ERROR.search(stream.read().decode("utf-8", errors="replace")))
    return False


def save_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def shared_memory(root):
    path = root / ".studio/memory.md"
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write("# Project memory\n\nRecord durable decisions, current state, "
                         "the last passing build, and next steps here. Keep credentials out.\n")
    except FileExistsError:
        pass
    return path


def run_job(args, root, config):
    provider = args.provider or config["roles"][args.role]
    if provider not in config["providers"]:
        raise ValueError("Enable this provider in setup before assigning jobs to it.")
    directory = getattr(args, "directory", None) or job_folder(root, args.role)
    directory.mkdir(parents=True, exist_ok=True)
    brief = Path(args.brief).read_text(encoding="utf-8")
    inputs = [str(Path(path).resolve()) for path in args.input]
    tools = {name: config["tools"].get(name) or executable(name, root)
             for name in (config["engine"], "blender", "photoshop", "ffmpeg")}
    memory = root / ".studio/memory.md"
    if not args.dry_run:
        memory = shared_memory(root)
    instructions = (
        f"Game studio role: {args.role}\nEngine: {config['engine']}\n"
        f"Role responsibilities: {ROLES[args.role]}\n"
        f"Input artifact paths: {json.dumps(inputs)}\n"
        f"Shared project memory: {memory.relative_to(root).as_posix()}\n"
        "Read the shared project memory before working. Keep it current as milestones land, "
        "including decisions, files changed, verification, and next steps. Use checkpoint.md "
        "in the job output folder to record partial work throughout the job.\n"
        f"Tool executable paths (null means unavailable): {json.dumps(tools)}\n"
        "Respect repository instructions. Do not publish or install tools. "
        "Write a report.md in the job output directory recording actual files, tests, and open issues.\n"
        "For QA, report findings and leave production files unchanged. "
        "For asset and marketing roles, stage derivatives in the job directory for integration.\n"
        f"\nCreator brief:\n{brief}\n"
    )
    if args.role == "qa":
        instructions += '\nWrite verdict.json with {"passed": true} only when acceptance checks passed. Use false if failed or unverified.\n'
    relative = directory.relative_to(root).as_posix()
    (directory / "prompt.txt").write_text(
        f"Job output directory: {relative}\n" + instructions, encoding="utf-8")
    if args.dry_run:
        print(f"{args.role} via {provider} -> {directory}", flush=True)
        return 0

    exhausted = getattr(args, "exhausted", set())
    candidates = [provider, *(name for name in config["providers"] if name != provider)]
    attempts = []
    result = 5
    for candidate in candidates:
        if candidate in exhausted:
            continue
        attempt = directory / f"attempt-{len(attempts) + 1}-{candidate}"
        attempt.mkdir()
        prompt = f"Job output directory: {attempt.relative_to(root).as_posix()}\n" + instructions
        if attempts or exhausted:
            prior = [item["directory"] for item in attempts if item["directory"]]
            prompt += (
                f"\nPrior attempt folders for this job: {json.dumps(prior)}\n"
                "Inspect current project files and Git status/diff before editing. "
                "Read any previous checkpoint and review previous staged assets. "
                "Preserve existing edits and reuse verified outputs. Finish outstanding work "
                "and write a fresh report (and QA verdict when applicable) to your own folder.\n"
            )
        (attempt / "prompt.txt").write_text(prompt, encoding="utf-8")
        launch = custom_providers(config).get(candidate) or PROVIDERS[candidate]
        try:
            argv = command_for(root, config, candidate) + launch[1:]
        except ValueError as error:
            if not exhausted:
                raise
            attempts.append({"provider": candidate, "directory": None, "state": "unavailable"})
            print(error, file=sys.stderr)
            continue
        print(f"{args.role} via {candidate} -> {attempt}", flush=True)
        code = execute(argv, root, attempt, args.timeout, prompt)
        limited = quota_failure(attempt, code)
        result = 5 if limited else validate_delivery(attempt, args.role, code)
        attempts.append({"provider": candidate, "directory": str(attempt),
                         "exit_code": code, "state": "quota_limited" if limited else
                         ("passed" if result == 0 else "failed")})
        save_json(directory / "handoff.json", {"role": args.role, "attempts": attempts,
                                             "exit_code": result, "provider": candidate,
                                             "delivery": str(attempt) if result == 0 else None})
        if not limited:
            return result
        exhausted.add(candidate)
        print(f"{candidate} hit a usage limit. Checking remaining providers.", file=sys.stderr)
    print("No remaining provider for this job. Checkpoints and edits were retained.", file=sys.stderr)
    return result


def validate_delivery(directory, role, code):
    if code:
        return code
    if not (directory / "report.md").is_file():
        print("Provider exited successfully but did not deliver report.md.", file=sys.stderr)
        return 3
    if role == "qa":
        try:
            verdict = json.loads((directory / "verdict.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            verdict = None
        if not isinstance(verdict, dict) or verdict.get("passed") is not True:
            print("QA did not return a passing verdict.", file=sys.stderr)
            return 4
    return 0


def workflow(args, root, config):
    run = job_folder(root, "workflow")
    start = STAGES.index(args.start)
    stop = STAGES.index(args.through) + 1
    if start >= stop:
        raise ValueError("--from must precede or equal --through.")
    brief = run / "brief.md"
    shutil.copyfile(args.brief, brief)
    state = {"dry_run": args.dry_run, "stages": {}}
    inputs = list(args.input)
    exhausted = set()
    for role in STAGES[start:stop]:
        directory = run / role
        result = run_job(Namespace(role=role, provider=None, directory=directory, brief=brief,
                                   input=inputs, dry_run=args.dry_run, timeout=args.timeout,
                                   exhausted=exhausted),
                         root, config)
        handoff = directory / "handoff.json"
        delivery = json.loads(handoff.read_text(encoding="utf-8")) if handoff.is_file() else {}
        state["stages"][role] = {"provider": delivery.get("provider", config["roles"][role]),
                                 "exit_code": result}
        save_json(run / "workflow.json", state)
        if result:
            return result
        inputs = [*inputs, delivery.get("delivery") or str(directory)]
    return 0


def execute(argv, root, directory, timeout, prompt=None):
    with (directory / "stdout.log").open("wb") as out, (directory / "stderr.log").open("wb") as err:
        try:
            result = subprocess.run(argv, cwd=root, input=prompt.encode("utf-8") if prompt else None,
                                    stdout=out, stderr=err, timeout=timeout, check=False)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
    (directory / "result.json").write_text(json.dumps({"exit_code": code}) + "\n", encoding="utf-8")
    print(f"Exit {code}. Logs: {directory}")
    return code


def smoke(args, root, config):
    engine = config["engine"]
    directory = job_folder(root, "smoke")
    argv = command_for(root, config, engine)
    if args.sample and not config.get("sample"):
        raise ValueError("The sample smoke action is available only in generated sample projects.")
    if engine == "godot":
        argv += ["--headless", "--path", str(root)]
        argv += ["--", "--studio-smoke"] if args.sample else ["--editor", "--import"]
    elif args.sample:
        argv += ["-batchmode", "-nographics", "-quit", "-projectPath", str(root),
                 "-executeMethod", "BeaconStudio.Build", "-logFile", str(directory / "unity.log"),
                 "-studioBuildPath", str(directory / "BeaconRelay.exe")]
    else:
        argv += ["-batchmode", "-nographics", "-quit", "-projectPath", str(root),
                 "-logFile", str(directory / "unity.log")]
    return execute(argv, root, directory, args.timeout)


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--project", default=".", help="Engine project path")
    commands = cli.add_subparsers(dest="command", required=True)
    wizard = commands.add_parser("setup")
    wizard.add_argument("--engine", choices=("unity", "godot"))
    wizard.add_argument("--template", choices=("blank", "beacon"))
    wizard.add_argument("--agents", nargs="+")
    wizard.add_argument("--provider-file", action="append", default=[])
    wizard.add_argument("--route", action="append", default=[], metavar="ROLE=PROVIDER")
    wizard.add_argument("--tool", action="append", default=[], metavar="NAME=PATH")
    wizard.add_argument("--non-interactive", action="store_true")
    commands.add_parser("doctor")
    commands.add_parser("plan")
    job = commands.add_parser("job")
    job.add_argument("role", choices=tuple(ROLES))
    job.add_argument("brief")
    job.add_argument("--input", action="append", default=[])
    job.add_argument("--provider")
    job.add_argument("--dry-run", action="store_true")
    job.add_argument("--timeout", type=int, default=1800)
    flow = commands.add_parser("workflow")
    flow.add_argument("brief")
    flow.add_argument("--from", dest="start", choices=STAGES, default=STAGES[0])
    flow.add_argument("--through", choices=STAGES, default="qa")
    flow.add_argument("--input", action="append", default=[])
    flow.add_argument("--dry-run", action="store_true")
    flow.add_argument("--timeout", type=int, default=1800)
    test = commands.add_parser("smoke")
    test.add_argument("--sample", action="store_true")
    test.add_argument("--timeout", type=int, default=900)
    return cli


def main():
    args = parser().parse_args()
    root = Path(args.project).expanduser().resolve()
    try:
        if args.command == "setup":
            setup(args, root)
            return 0
        config = read_config(root)
        if args.command == "doctor":
            doctor(root, config)
        elif args.command == "plan":
            for role, provider in config["roles"].items():
                print(f"{role:12} {provider:8} {ROLES[role]}")
        elif args.command == "job":
            return run_job(args, root, config)
        elif args.command == "workflow":
            return workflow(args, root, config)
        elif args.command == "smoke":
            return smoke(args, root, config)
        return 0
    except (OSError, ValueError, KeyError, EOFError) as error:
        print(f"Studio: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
