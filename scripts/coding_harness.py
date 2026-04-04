#!/usr/bin/env python3
# Checked AGENTS.md - implementing directly because:
# This IS the agent orchestration harness itself — it cannot be delegated to an agent.
# Architecture, safety gates, and evaluation logic must be owned by Claude (senior dev).
# Gemini Flash is delegated to within the harness for boilerplate and doc writing.
"""
Coding Harness — Planner → Generator → Evaluator → Doc Updater

Autonomous feature development with criteria locked before work begins.
Separate agents for each phase prevent self-approval and shortcutting.

Agent delegation model (per GEMINI_WORKFLOW.md):
  Claude Opus    — Planner: architecture, spec, acceptance criteria
  Claude Sonnet  — Generator: feature implementation (safety-critical path)
  Claude Sonnet  — Evaluator: quality gate, scores against frozen criteria
  Gemini Flash   — Boilerplate classifier/generator: routine subtasks within generation
  Gemini Flash   — Doc Updater: doc patching from diff (routine writing)
  Claude Haiku   — fallback doc updater if Gemini unavailable

Usage:
    uv run python scripts/coding_harness.py "Add recall endpoint for 2026 models"
    uv run python scripts/coding_harness.py "task" --plan-only    # inspect plan before building
    uv run python scripts/coding_harness.py --eval-only           # re-evaluate current branch
    uv run python scripts/coding_harness.py "task" --dry-run      # plan + show, no generation
"""

import argparse
import json
import os
import subprocess
import sys
import textwrap
from datetime import datetime
from pathlib import Path

# ── Project paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
HARNESS_DIR = PROJECT_ROOT / ".harness"
PLANS_DIR = HARNESS_DIR / "plans"
CURRENT_PLAN_FILE = HARNESS_DIR / "current-plan.json"

# ── Model assignments (per GEMINI_WORKFLOW.md) ────────────────────────────────
MODEL_PLANNER = "claude-opus-4-6"          # Complex architecture — keep with Claude
MODEL_GENERATOR = "claude-sonnet-4-6"      # Implementation — keep with Claude
MODEL_EVALUATOR = "claude-sonnet-4-6"      # Quality gate — keep with Claude
MODEL_DOC_UPDATER_GEMINI = "gemini-2.5-flash"  # Doc writing — delegate to Gemini
MODEL_DOC_UPDATER_FALLBACK = "claude-haiku-4-5-20251001"  # Fallback if Gemini unavailable

MAX_EVAL_ITERATIONS = 3
MIN_PASS_FRACTION = 0.75  # 75% of max possible score required to pass

WATCHED_DOCS = [
    ".claude/docs/DIAGRAMS.md",
    ".claude/docs/ARCHITECT.md",
    "CLAUDE.md",
    ".claude/docs/LESSONS.md",
]


# ── API clients ───────────────────────────────────────────────────────────────

def _read_key(env_var: str, secret_name: str | None = None) -> str:
    """Read a key from environment, .env file, or GCP Secret Manager."""
    key = os.environ.get(env_var, "")
    if key:
        return key
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith(f"{env_var}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    if secret_name:
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest", f"--secret={secret_name}"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    return ""


def get_anthropic_client():
    """Return Anthropic client."""
    try:
        import anthropic  # type: ignore[import-untyped]
    except ImportError:
        print("ERROR: anthropic not installed")
        sys.exit(1)
    key = _read_key("ANTHROPIC_API_KEY")
    if not key:
        print("ERROR: ANTHROPIC_API_KEY not found")
        sys.exit(1)
    return anthropic.Anthropic(api_key=key)


def get_gemini_client():
    """Return configured google.genai client, or None if unavailable."""
    try:
        from google import genai as google_genai  # type: ignore[import-untyped]
    except ImportError:
        return None
    key = _read_key("GOOGLE_AI_API_KEY", secret_name="gemini-api-key")
    if not key:
        return None
    return google_genai.Client(api_key=key)


def call_claude(client, model: str, system: str, user: str, max_tokens: int = 4096) -> str:
    """Single Claude API call, returns text."""
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def call_gemini(genai_client, prompt: str, model: str = MODEL_DOC_UPDATER_GEMINI) -> str:
    """Single Gemini API call via google-genai SDK, returns text."""
    response = genai_client.models.generate_content(model=model, contents=prompt)
    return response.text.strip()


def strip_code_fences(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


# ── Phase 1: Planner (Claude Opus) ───────────────────────────────────────────

PLANNER_SYSTEM = """You are a senior software architect for an automotive diagnostic AI system.
Create a complete, unambiguous feature specification with LOCKED acceptance criteria
BEFORE any code is written. These criteria will be evaluated by a SEPARATE agent —
make them objective, graded, and verifiable by code inspection and test output.

Project stack: Python 3.11+, FastAPI (server/home_server.py), Next.js (src/frontend/),
SQLite (automotive_complaints.db 843MB primary, automotive_diagnostics.db secondary).
Tests: 280 Python unit, 142 Vitest, 42 Playwright. Use `uv run pytest`.

Return ONLY valid JSON:
{
  "task": "one-line task summary",
  "branch": "feature/kebab-case-name",
  "spec": "Full technical specification (2-5 paragraphs)",
  "subtasks": [
    {"step": "description", "type": "boilerplate|complex|safety-critical"}
  ],
  "acceptance_criteria": [
    {
      "id": "AC-1",
      "description": "what must be true",
      "how_to_verify": "concrete verification step (grep/test/curl)",
      "max_score": 3,
      "delegate": false
    }
  ],
  "docs_to_update": ["relative/path/to/doc.md"],
  "test_requirements": "what new/updated tests are required",
  "estimated_files": ["files to create or modify"],
  "gemini_subtasks": ["subtask descriptions safe to delegate to Gemini Flash"]
}

Mark subtasks as:
  "boilerplate" — CRUD, serialization, simple helpers → delegate to Gemini Flash
  "complex" — logic, integration, multi-step → keep with Claude Sonnet
  "safety-critical" → Claude only, never delegate

Include 4-8 acceptance criteria scored 0-3 (0=not met, 3=fully met).
List in gemini_subtasks ONLY boilerplate items safe for Gemini delegation."""


def run_planner(client, task_description: str) -> dict:
    """Phase 1: Claude Opus generates spec + locked acceptance criteria."""
    print(f"\n{'='*60}")
    print("PHASE 1 — PLANNING  [Claude Opus]")
    print(f"{'='*60}")
    print(f"Task: {task_description}")

    raw = call_claude(client, MODEL_PLANNER, PLANNER_SYSTEM,
                      f"Create a complete feature spec:\n\n{task_description}",
                      max_tokens=3000)
    raw = strip_code_fences(raw)

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Planner returned invalid JSON: {e}\n{raw[:400]}")
        sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    plan.update({"created_at": ts, "task_input": task_description, "status": "planned"})

    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    plan_file = PLANS_DIR / f"{ts}-plan.json"
    plan_file.write_text(json.dumps(plan, indent=2))
    CURRENT_PLAN_FILE.write_text(json.dumps(plan, indent=2))

    print(f"\n✓ Plan locked → {plan_file.name}")
    print(f"\nBranch: {plan['branch']}")
    max_pts = sum(c["max_score"] for c in plan["acceptance_criteria"])
    print(f"\nAcceptance Criteria (locked, {len(plan['acceptance_criteria'])} criteria, {max_pts}pt max):")
    for c in plan["acceptance_criteria"]:
        print(f"  {c['id']} [{c['max_score']}pt] {c['description']}")

    gemini_tasks = plan.get("gemini_subtasks", [])
    if gemini_tasks:
        print(f"\nBoilerplate delegated to Gemini Flash ({len(gemini_tasks)} subtasks):")
        for t in gemini_tasks:
            print(f"  • {t}")

    print(f"\nDocs to check: {', '.join(plan.get('docs_to_update', WATCHED_DOCS))}")
    return plan


# ── Phase 1b: Gemini pre-generation (boilerplate) ────────────────────────────

def run_gemini_pregen(genai_module, plan: dict) -> dict[str, str]:
    """Pre-generate boilerplate snippets via Gemini Flash before Generator starts."""
    gemini_tasks = plan.get("gemini_subtasks", [])
    if not gemini_tasks or not genai_module:
        return {}

    print(f"\n{'='*60}")
    print("PHASE 1b — BOILERPLATE PRE-GENERATION  [Gemini Flash]")
    print(f"{'='*60}")

    results: dict[str, str] = {}
    context = f"""Project: automotive-diagnostic-skills
Stack: Python 3.11+, FastAPI, SQLite, Next.js
Feature being built: {plan['task']}
Spec: {plan['spec'][:500]}

Generate clean, production-ready code for this boilerplate task.
Include type annotations. Follow existing project conventions.
Return ONLY the code, no explanation."""

    for task in gemini_tasks:
        print(f"  Gemini: {task[:60]}...")
        try:
            result = call_gemini(genai_module, f"{context}\n\nTask: {task}")
            results[task] = result
            print(f"  ✓ {len(result)} chars generated")
        except Exception as e:
            print(f"  ✗ Gemini failed for '{task[:40]}': {e}")

    return results


# ── Phase 2: Generator (Claude Sonnet via Claude Code CLI) ────────────────────

def run_generator(plan: dict, boilerplate: dict[str, str], dry_run: bool) -> str:
    """Phase 2: Claude Sonnet implements the feature via Claude Code CLI."""
    print(f"\n{'='*60}")
    print("PHASE 2 — GENERATION  [Claude Sonnet]")
    print(f"{'='*60}")

    branch = plan["branch"]

    if dry_run:
        print(f"[DRY RUN] Would create branch: {branch}")
        return branch

    # Create feature branch
    result = subprocess.run(["git", "checkout", "-b", branch],
                            cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        subprocess.run(["git", "checkout", branch], cwd=PROJECT_ROOT,
                       capture_output=True, check=True)
    print(f"✓ Branch: {branch}")

    # Build criteria section (read-only for generator)
    criteria_lines = "\n".join(
        f"  {c['id']} (max {c['max_score']}pt): {c['description']}\n"
        f"    Verify: {c['how_to_verify']}"
        for c in plan["acceptance_criteria"]
    )

    subtasks_text = "\n".join(
        f"  {i+1}. [{s.get('type','complex').upper()}] {s['step'] if isinstance(s, dict) else s}"
        for i, s in enumerate(plan["subtasks"])
    )

    # Include pre-generated boilerplate if available
    boilerplate_section = ""
    if boilerplate:
        snippets = "\n\n".join(
            f"### {task}\n```\n{code[:800]}\n```"
            for task, code in boilerplate.items()
        )
        boilerplate_section = f"\n\n## Pre-generated Boilerplate (from Gemini Flash — review and adapt)\n{snippets}"

    generator_prompt = textwrap.dedent(f"""
        You are implementing a feature for the automotive-diagnostic-skills project.
        Work on branch: {branch}

        ## Task
        {plan['task']}

        ## Specification
        {plan['spec']}

        ## Implementation Steps
        {subtasks_text}
        {boilerplate_section}

        ## Acceptance Criteria (READ-ONLY — set by Planner, evaluated by separate Evaluator)
        {criteria_lines}

        ## Test Requirements
        {plan.get('test_requirements', 'All 280 existing tests must continue to pass.')}

        ## Files Likely Affected
        {', '.join(plan.get('estimated_files', []))}

        ## Rules
        - Run tests before finishing: uv run pytest --tb=no -q --ignore=tests/integration
        - Commit at logical checkpoints
        - Do NOT modify .harness/ directory or acceptance criteria
        - Do NOT merge to main — stay on branch {branch}
        - Safety-critical code (brakes/airbags/steering) requires confidence >= 0.9

        Implement the full feature now.
    """).strip()

    prompt_file = HARNESS_DIR / "generator-prompt.md"
    prompt_file.write_text(generator_prompt)

    print(f"Invoking Claude Code (model: {MODEL_GENERATOR})...")
    print("─" * 40)
    subprocess.run(
        ["claude", "--model", MODEL_GENERATOR, "--dangerously-skip-permissions", "--print", generator_prompt],
        cwd=PROJECT_ROOT
    )
    return branch


# ── Phase 3: Evaluator (Claude Sonnet) ───────────────────────────────────────

EVALUATOR_SYSTEM = """You are a strict, skeptical QA evaluator for an automotive diagnostic AI project.
Evaluate completed implementations against PRE-DEFINED acceptance criteria. Be harsh.

Rules:
- Test superficially passing is NOT enough — check edge cases were handled
- "Existing tests pass" does not mean new tests were added when required
- Check error handling: what happens on bad input, DB errors, network failures?
- Docs being stale is a defect — if row counts or file paths changed, that matters
- If safety-critical code was touched, confidence threshold enforcement must be present

Scoring: 0=not met, 1=partial, 2=mostly, 3=fully met.

Return ONLY valid JSON:
{
  "scores": [{"id": "AC-1", "score": 2, "rationale": "specific reason"}],
  "total_score": 14,
  "max_score": 18,
  "fraction": 0.78,
  "verdict": "PASS" or "FAIL",
  "feedback": "Specific, actionable feedback if FAIL — what exactly to fix",
  "test_status": "PASS" or "FAIL",
  "critical_issues": ["blocking issues preventing approval"]
}"""


def get_git_diff(branch: str) -> str:
    """Get stat + unified diff of branch vs main."""
    stat = subprocess.run(["git", "diff", "main...", "--stat"],
                          cwd=PROJECT_ROOT, capture_output=True, text=True).stdout.strip()
    diff = subprocess.run(["git", "diff", "main...", "--unified=3"],
                          cwd=PROJECT_ROOT, capture_output=True, text=True).stdout
    if len(diff) > 15000:
        diff = diff[:15000] + "\n...[truncated]..."
    return f"=== STAT ===\n{stat}\n\n=== DIFF ===\n{diff}"


def run_tests_for_eval() -> tuple[bool, str]:
    """Run pytest, return (passed, output_tail)."""
    result = subprocess.run(
        ["uv", "run", "--with", "pytest", "pytest", "--tb=short", "-q",
         "--ignore=tests/integration"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120
    )
    return result.returncode == 0, (result.stdout + result.stderr)[-3000:]


def run_evaluator(client, plan: dict, branch: str, iteration: int) -> dict:
    """Phase 3: Claude Sonnet evaluates diff against frozen criteria."""
    print(f"\n{'='*60}")
    print(f"PHASE 3 — EVALUATION  [Claude Sonnet]  (pass {iteration}/{MAX_EVAL_ITERATIONS})")
    print(f"{'='*60}")
    print("Running tests...")

    passed, test_out = run_tests_for_eval()
    print(f"Tests: {'✓ PASS' if passed else '✗ FAIL'}")

    criteria_json = json.dumps(plan["acceptance_criteria"], indent=2)
    max_total = sum(c["max_score"] for c in plan["acceptance_criteria"])
    diff = get_git_diff(branch)

    raw = call_claude(
        client, MODEL_EVALUATOR, EVALUATOR_SYSTEM,
        f"""Evaluate this implementation.

## Task
{plan['task']}

## Acceptance Criteria (max {max_total}pt)
{criteria_json}

## Test Results
{'PASSED' if passed else 'FAILED'}
{test_out}

## Git Diff
{diff}
""",
        max_tokens=2000
    )
    raw = strip_code_fences(raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"verdict": "FAIL", "feedback": raw[:500], "fraction": 0.0, "scores": []}

    # Pretty-print scores
    print(f"\nScores:")
    for s in result.get("scores", []):
        crit = next((c for c in plan["acceptance_criteria"] if c["id"] == s["id"]), {})
        mx = crit.get("max_score", 3)
        bar = "█" * s["score"] + "░" * (mx - s["score"])
        print(f"  {s['id']} [{bar}] {s['score']}/{mx}  {s['rationale'][:70]}")

    frac = result.get("fraction", 0.0)
    verdict = result.get("verdict", "FAIL")
    print(f"\nTotal: {result.get('total_score','?')}/{result.get('max_score','?')} "
          f"({frac:.0%}) → {verdict}")

    for issue in result.get("critical_issues", []):
        print(f"  ✗ {issue}")

    return result


# ── Phase 4: Doc Updater (Gemini Flash, Haiku fallback) ──────────────────────

DOC_UPDATER_PROMPT_TEMPLATE = """You are a documentation maintenance agent for an automotive diagnostic AI project.
Review a git diff and patch any stale documentation files.

Rules:
- DIAGRAMS.md is ground truth — update row counts, file paths, architecture if changed
- ARCHITECT.md lists components and files — update if new files were added
- CLAUDE.md DB quick-reference — update if row counts changed
- LESSONS.md — add an entry if a non-obvious technique or pitfall was encountered
- Only patch docs that are ACTUALLY stale — skip if still accurate

Return ONLY valid JSON:
{{
  "updates": [
    {{
      "file": "relative/path/to/doc.md",
      "reason": "why stale",
      "old_text": "exact text to replace",
      "new_text": "replacement text"
    }}
  ],
  "summary": "one-line summary of changes"
}}

If nothing is stale: {{"updates": [], "summary": "No doc updates required."}}

## Feature implemented
{task}

## Git Diff
{diff}

## Current doc contents
{doc_contents}"""


def run_doc_updater(client, genai_module, plan: dict, branch: str, dry_run: bool) -> None:
    """Phase 4: Update stale docs via Gemini Flash (Haiku fallback)."""
    print(f"\n{'='*60}")
    print("PHASE 4 — DOC UPDATE  "
          f"[{'Gemini Flash' if genai_module else 'Claude Haiku (Gemini unavailable)'}]")
    print(f"{'='*60}")

    diff = get_git_diff(branch)
    doc_contents = ""
    for doc_rel in plan.get("docs_to_update", WATCHED_DOCS):
        full = PROJECT_ROOT / doc_rel
        if full.exists():
            doc_contents += f"\n=== {doc_rel} ===\n{full.read_text()[:2500]}\n"

    prompt = DOC_UPDATER_PROMPT_TEMPLATE.format(
        task=plan["task"], diff=diff, doc_contents=doc_contents
    )

    try:
        if genai_module:
            raw = call_gemini(genai_module, prompt)
        else:
            raw = call_claude(client, MODEL_DOC_UPDATER_FALLBACK,
                              "You are a documentation updater. Return only JSON.", prompt,
                              max_tokens=2000)
        raw = strip_code_fences(raw)
        result = json.loads(raw)
    except Exception as e:
        print(f"  WARN: Doc updater failed ({e}), skipping")
        return

    updates = result.get("updates", [])
    if not updates:
        print(f"  ✓ {result.get('summary', 'No doc updates needed')}")
        return

    patched_files = []
    for u in updates:
        fpath = PROJECT_ROOT / u["file"]
        if not fpath.exists():
            print(f"  SKIP: {u['file']} not found")
            continue
        content = fpath.read_text()
        old, new = u.get("old_text", ""), u.get("new_text", "")
        if old and old in content:
            if not dry_run:
                fpath.write_text(content.replace(old, new, 1))
            action = "[DRY RUN]" if dry_run else "✓"
            print(f"  {action} {u['file']}: {u['reason']}")
            patched_files.append(str(fpath))
        else:
            print(f"  SKIP: {u['file']} — text not found (may already be current)")

    if patched_files and not dry_run:
        subprocess.run(["git", "add"] + patched_files, cwd=PROJECT_ROOT)
        subprocess.run(
            ["git", "commit", "-m",
             f"docs: auto-update after {plan['task'][:55]}\n\n{result.get('summary','')}"],
            cwd=PROJECT_ROOT
        )
        print(f"  ✓ Committed doc updates")

    print(f"\n  {result.get('summary', '')}")


# ── Main orchestrator ─────────────────────────────────────────────────────────

def _notify_telegram(msg: str) -> None:
    """Best-effort Telegram status notification (non-blocking)."""
    try:
        chat_id = "6466088194"
        bot_token = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest", "--secret=telegram-bot-token"],
            capture_output=True, text=True
        ).stdout.strip()
        if not bot_token:
            return
        import urllib.request, urllib.parse
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode()
        urllib.request.urlopen(url, data, timeout=5)
    except Exception:
        pass  # Never block on notification failure


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Coding harness: Planner → Generator → Evaluator → Doc Updater"
    )
    parser.add_argument("task", nargs="?", help="Feature description")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, no file changes")
    parser.add_argument("--plan-only", action="store_true", help="Stop after planning")
    parser.add_argument("--eval-only", action="store_true", help="Re-run evaluator on current branch")
    parser.add_argument("--skip-gen", action="store_true", help="Skip generation, use existing branch")
    args = parser.parse_args()

    anthropic_client = get_anthropic_client()
    gemini = get_gemini_client()
    if gemini:
        print(f"✓ Gemini Flash available for boilerplate + doc updates")
    else:
        print(f"! Gemini unavailable — Claude Haiku will handle doc updates")

    # ── Eval-only ──
    if args.eval_only:
        if not CURRENT_PLAN_FILE.exists():
            print("ERROR: No current plan. Run with a task first.")
            sys.exit(1)
        plan = json.loads(CURRENT_PLAN_FILE.read_text())
        branch = subprocess.run(["git", "branch", "--show-current"],
                                 cwd=PROJECT_ROOT, capture_output=True, text=True).stdout.strip()
        eval_result = run_evaluator(anthropic_client, plan, branch, 1)
        if eval_result.get("verdict") == "PASS":
            run_doc_updater(anthropic_client, gemini, plan, branch, dry_run=False)
        return

    if not args.task:
        parser.print_help()
        sys.exit(1)

    print(f"\n{'#'*60}")
    print("  CODING HARNESS  v1.0")
    print(f"{'#'*60}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Phase 1: Plan (Claude Opus)
    plan = run_planner(anthropic_client, args.task)
    _notify_telegram(f"🔧 Harness started: {plan['task']}\nBranch: {plan['branch']}\n"
                     f"Criteria: {len(plan['acceptance_criteria'])} locked")

    if args.plan_only or args.dry_run:
        print("\n[Stopped after planning]")
        return

    # Phase 1b: Boilerplate pre-gen (Gemini Flash)
    boilerplate = run_gemini_pregen(gemini, plan)

    # Phase 2: Generate (Claude Sonnet via Claude Code CLI)
    if not args.skip_gen:
        branch = run_generator(plan, boilerplate, dry_run=False)
    else:
        branch = plan["branch"]
        print(f"\n[Skipping generation — using existing branch: {branch}]")

    # Phase 3: Evaluate loop (Claude Sonnet)
    eval_passed = False
    for iteration in range(1, MAX_EVAL_ITERATIONS + 1):
        eval_result = run_evaluator(anthropic_client, plan, branch, iteration)

        if eval_result.get("verdict") == "PASS":
            eval_passed = True
            _notify_telegram(f"✅ Harness PASSED on iteration {iteration}\n"
                             f"Score: {eval_result.get('total_score')}/{eval_result.get('max_score')} "
                             f"({eval_result.get('fraction', 0):.0%})\n"
                             f"Branch {branch} ready to merge.")
            break

        if iteration < MAX_EVAL_ITERATIONS:
            feedback = eval_result.get("feedback", "Fix issues above.")
            issues = "\n".join(f"- {i}" for i in eval_result.get("critical_issues", []))
            fb_prompt = (f"Evaluator rejected your implementation.\n\nFeedback:\n{feedback}"
                         f"\n\nCritical issues:\n{issues}\n\n"
                         f"Fix these, re-run tests, commit.")
            print(f"\n↩ Sending feedback to generator (attempt {iteration+1})...")
            subprocess.run(["claude", "--model", MODEL_GENERATOR, "--dangerously-skip-permissions", "--print", fb_prompt],
                           cwd=PROJECT_ROOT)
        else:
            _notify_telegram(f"❌ Harness FAILED after {MAX_EVAL_ITERATIONS} iterations\n"
                             f"Branch {branch} left open for manual review.")
            print(f"\n✗ FAILED after {MAX_EVAL_ITERATIONS} iterations — manual review needed")
            plan["status"] = "eval-failed"
            CURRENT_PLAN_FILE.write_text(json.dumps(plan, indent=2))
            sys.exit(1)

    # Phase 4: Doc update (Gemini Flash / Haiku fallback)
    if eval_passed:
        run_doc_updater(anthropic_client, gemini, plan, branch, dry_run=False)
        plan["status"] = "complete"
        CURRENT_PLAN_FILE.write_text(json.dumps(plan, indent=2))
        print(f"\n{'='*60}")
        print("  HARNESS COMPLETE")
        print(f"{'='*60}")
        print(f"  Branch {branch} ready to merge.")
        print(f"  Run: git checkout main && git merge {branch}")
        print(f"       git tag vX.Y-<name> && git push origin main --tags")


if __name__ == "__main__":
    main()
