# Triage playbook

Rules learned from hand-triaging and adjudicating real uv issues (audit/round1_results.md, evals/adjudication_v0.2.md). Edit this file as evals reveal new failure patterns; it is the agent's long-term memory.

## Rules

1. The reporter asks "Is this a bug?", "Am I doing something wrong?", or "How should I…?" → usually a **question**.
2. The report names the release that broke it, or the change that caused it ("worked in 0.12.13, fails in 0.12.14") → strong signal for **bug**. Exception: if the newer version started *enforcing* something it used to silently ignore, and the error message says what to change, it is a **question**.
3. The tool behaves as designed and the reporter proposes different behaviour or shares a workaround → **enhancement**.
4. It fails only on the reporter's setup while other methods or machines work, and there is no minimal reproduction → **needs_mre**, and consider **likely_external**.
5. The failure comes from a defect in another tool (e.g. a build backend emitting malformed metadata), a non-standard registry, the OS, antivirus, or the network (e.g. "connection reset" while downloading) → **likely_external**. A package's deliberate version cap is not a defect → **question**, not external.
6. Unexpected output alone does not make it a bug. First rule out a config mistake (does the key or flag exist? is there an existing setting for exactly this?) and behaviour forced by a dependency's own constraints (check package metadata).
7. The behaviour turns out to be by design: if the reporter *asks for a change*, it is an **enhancement**; if they are confused or stuck, it is a **question**. The reporter followed the documented setup and it failed → **bug**.
8. Antivirus / VirusTotal flags on a fresh uv release are almost always vendor false positives → **likely_external**, search for the current tracking issue, and escalate (security).

## uv concepts that explain many reports

- **Universal resolution.** `uv lock`, `uv add` and `uv sync` resolve for *all* platforms and Python versions allowed by `requires-python`, not just the current machine, so they may need metadata for wheels you will never install (e.g. a Windows-only dependency on Linux). Restrict with `[tool.uv] environments = [...]`. `uv pip compile` / `uv pip install` resolve for the current platform unless `--universal`. A macOS wheel appearing in a lock made on Windows is expected.
- **`--locked` vs `--frozen`.** `--locked` checks the lockfile is up to date (so it may need to read sources); `--frozen` uses the lockfile as-is without checking.
- **`uvx` / `uv tool run`.** Runs the tool in its own isolated environment, not the project's. If a tool seems to see project dependencies, suspect `PYTHONPATH`, a wrapper that calls `uv run`, or the interpreter in use.
- **Editable / local-directory installs.** uv rebuilds a local package only when its cache keys change (by default `pyproject.toml`, `setup.py`, `setup.cfg`), so stale installs after other edits are a known pattern.
- **Config keys.** Settings live under `[tool.uv]` (not `[tools.uv]`); scripts are `[project.scripts]`.
