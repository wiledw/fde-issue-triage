# Triage playbook

Rules learned from hand-triaging real uv issues (audit/round1_results.md). Edit this file as evals reveal new failure patterns; it is the agent's long-term memory.

1. The reporter asks "Is this a bug?", "Am I doing something wrong?", or "How should I…?" → usually a **question**.
2. The report names the release that broke it, or the change that caused it ("worked in 0.12.13, fails in 0.12.14") → strong signal for **bug**.
3. The tool behaves as designed and the reporter proposes different behaviour or shares a workaround → **enhancement**.
4. It fails only on the reporter's setup while other methods or machines work, and there is no minimal reproduction → **needs_mre**, and consider **likely_external**.
5. The failure comes from a defect in another tool (e.g. a build backend emitting malformed metadata), the OS, antivirus, or the network (e.g. "connection reset" while downloading) → **likely_external**. A package's deliberate version cap is not a defect → **question**, not external.
6. Unexpected output alone does not make it a bug. First rule out a config mistake (check the docs: does the key or flag exist?) and behaviour forced by a dependency's own constraints (check package metadata).
