# Handoff: Project Optimization Review And Smart Input Detection

## Session Metadata
- Created: 2026-03-13 00:43:11
- Project: /home/louis/doubao-batch-translator
- Branch: main
- Session duration: about 2.5 hours across dependency migration, real EPUB translation, code review, and CLI UX discussion

### Recent Commits (for context)
  - a20fe4a build: migrate project to uv with cernet mirror
  - 6318ff2 test: replace brittle assertions with stable offline smoke tests
  - c052868 test: add lightweight unit coverage for core translator behaviors
  - 8b6ffe4 test: avoid pytest fixture collection in concurrency script
  - c5fc9b9 docs: add badges and CI workflow

## Handoff Chain

- **Continues from**: None (fresh start)
- **Supersedes**: None

> This is the first handoff for this task.

## Current State Summary

This session finished the repo migration from `pip` to `uv`, added a repo-level CERNET mirror, updated CI/docs, and pushed commit `a20fe4a` to `origin/main`. A real end-to-end translation run was completed for `/home/louis/Downloads/The Dialectic of Sex (Shulamith Firestone) (z-library.sk, 1lib.sk, z-lib.sk).epub`, producing `/home/louis/Downloads/The Dialectic of Sex (Shulamith Firestone) (z-library.sk, 1lib.sk, z-lib.sk)_zh.epub`; the built-in repair loop stalled on the `part0005` chapter inside the EPUB, so three remaining untranslated organization names were fixed manually and `uv run python tools/check_untranslated.py` then reported `0` untranslated items. The user now wants two follow-ups: push optimization/design docs into the repo, and improve the CLI so users do not need to explicitly specify file type subcommands when the tool can infer input type intelligently.

## Codebase Understanding

## Architecture Overview

`main.py` contains a large `MainCLI` class that owns argparse setup, config loading, dispatch, EPUB repackaging, and the interactive repair loop. Translation logic fans out into specialized processors under `processors/` (`html_worker.py`, `epub_worker.py`, markdown/json handling) and uses `AsyncTranslator` plus `TranslatorConfig` from `core/`. EPUB quality control is handled by `tools/check_untranslated.py`, which is also used from `MainCLI._run_interactive_patch_loop()`. The project now uses `uv` as the package manager (`pyproject.toml`, `uv.lock`, `.python-version`) and CI installs dependencies with `uv sync --locked --dev`.

## Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| main.py | Top-level CLI, subcommand definitions, dispatch, EPUB repair loop | Smart input detection will likely start here because current UX requires `json/html/md/epub` subcommands |
| processors/html_worker.py | Parses and rewrites HTML/XHTML content during translation | Real EPUB run exposed XML parsed as HTML warnings here |
| tools/check_untranslated.py | Scans translated EPUBs and writes untranslated reports | Contains a real bug at `tools/check_untranslated.py:262` when writing a report file |
| core/token_tracker.py | Tracks daily quota/token usage windows | Emits current deprecation warnings due to `datetime.utcnow()` usage |
| pyproject.toml | Project metadata, dependencies, and repo-level uv index config | Holds the new `uv` mirror configuration |
| README.md | Main user-facing setup and usage documentation | Must be updated again if CLI input auto-detection changes |

## Key Patterns Discovered

The current CLI is strongly subcommand-oriented: each file type has its own parser branch with duplicated `--file`, `--output`, and language flags. The EPUB repair loop currently uses a pragmatic but brittle monkey-patch strategy against `HTMLProcessor` internals instead of a stable patch API. Tests are lightweight and mostly smoke-level, so behavior discovered during a real book translation matters more than the automated suite right now. The repository has already standardized on `uv run ...` for commands, `uv sync --locked --dev` for setup, and the committed lockfile should be treated as authoritative.

## Work Completed

## Tasks Finished

- [x] Migrated the project from `pip`/`requirements.txt` to `uv` with `pyproject.toml`, `uv.lock`, `.python-version`, updated CI, and updated docs
- [x] Added a repo-level CERNET `uv` mirror so installs work from the repository without relying on the machine-local `~/.config/uv/uv.toml`
- [x] Committed and pushed the dependency/tooling migration as `a20fe4a build: migrate project to uv with cernet mirror`
- [x] Ran a full real-world EPUB translation, manually fixed three residual untranslated items, and revalidated the output EPUB to `0` untranslated segments
- [x] Reviewed the codebase with the `code-reviewer` workflow and identified concrete optimization priorities backed by real runtime behavior
- [x] Installed the `session-handoff` skill and created this handoff document

## Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| pyproject.toml | Added project metadata, dependencies, and repo-level `uv` index config | Replaced ad hoc `pip` workflow with reproducible `uv` management |
| uv.lock | Added lockfile generated by `uv lock` | Ensures deterministic dependency resolution in local and CI environments |
| .python-version | Added pinned Python version marker | Aligns local interpreter selection with `uv` workflow |
| .github/workflows/ci.yml | Switched CI install/test steps to `uv` | Keeps CI consistent with local developer workflow |
| README.md | Updated installation and run commands to `uv` | Prevents stale setup instructions after migration |
| CLAUDE.md | Updated local project instructions to `uv` | Keeps agent-facing repo docs aligned with actual tooling |

## Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Standardize on `uv` instead of `pip` | Keep `requirements.txt`, add `pyproject.toml` only, or fully migrate to `uv` | Full migration removed split-brain dependency management and made CI/local commands consistent |
| Commit a repo-level China-friendly mirror in `pyproject.toml` | Rely on global user config only, document manual setup, or commit repo config | Repo-level config is portable and works for collaborators without extra machine setup |
| Treat the real EPUB translation run as primary evidence for optimization priorities | Rely only on unit tests, static review, or a synthetic sample | The real book surfaced failure modes that current tests did not catch |
| Delay CLI auto-detection implementation until the next step | Implement immediately, document first, or ignore UX feedback | The user explicitly asked for optimization/design docs, and one CLI behavior question remained unresolved |

## Pending Work

## Immediate Next Steps

1. Add and push one or more design/optimization documents under the repo describing the discovered issues, proposed fixes, and rollout order
2. Resume the smart CLI UX design and decide the fallback behavior when file type auto-detection fails or a directory contains mixed input types
3. Implement the chosen CLI auto-detection approach in `main.py`, add tests, and update `README.md` and `CLAUDE.md`

## Blockers/Open Questions

- [ ] Open question: the user wants the CLI to be "尽量自动/智能", but the fallback policy for ambiguous inputs is not finalized yet, especially for mixed-type directories or failed detection
- [ ] Open question: decide whether auto-detection should preserve backward-compatible subcommands while adding an optional no-subcommand path, or whether the default parser should become the primary interface immediately
- [ ] Operational prerequisite: real translation runs still require a working `ARK_API_KEY` in `.env` or the environment

## Deferred Items

- Fix `tools/check_untranslated.py:262` so report generation does not reference undefined `epub_path`; deferred because the user shifted to docs and CLI UX
- Replace the whole-file monkey-patch repair loop in `main.py:213` with a targeted patch flow based on specific untranslated hits; deferred because it is a larger design change
- Split XHTML/XML parsing onto a correct XML-aware path in `processors/html_worker.py:251`; deferred because no code changes were requested after the review
- Replace `datetime.utcnow()` in `core/token_tracker.py:45` and `core/token_tracker.py:50`; deferred because the warnings are non-blocking
- Expand automated coverage around EPUB translation/repair paths; deferred because the higher-priority user ask became documentation plus UX simplification

## Context for Resuming Agent

## Important Context

The most important facts are operational, not theoretical. First, the repo is already migrated to `uv` and that state is committed and pushed; do not reintroduce `requirements.txt` or `pip`-first docs. Second, the project was tested on a real book, and that run proved the current auto-repair loop is not robust: `MainCLI._run_interactive_patch_loop()` repeatedly retranslated the `part0005` chapter file inside the EPUB and hit the hard stop after five rounds, leaving three untranslated organization names that had to be edited manually in the output EPUB. Third, `tools/check_untranslated.py` contains a confirmed bug when writing a report file, because `generate_report()` uses `epub_path` without defining it in scope; this happened in practice, not just in theory. Fourth, the user explicitly dislikes having to declare file type manually and wants the CLI to infer the correct behavior as intelligently as possible, so any next code change should be shaped around a more automatic entrypoint instead of adding more explicit flags.

The translated output EPUB already exists at `/home/louis/Downloads/The Dialectic of Sex (Shulamith Firestone) (z-library.sk, 1lib.sk, z-lib.sk)_zh.epub`, and the final verification command reported `0` untranslated items. Manual fixes applied there were: translating `Daughters of the American Revolution` to `美国革命之女会`, `National Association for the Advancement of Coloured People` to `美国全国有色人种协进会`, and `National Organization of Women` to `美国全国妇女组织`. Those changes were applied only to the generated EPUB artifact outside the repo, so the repository working tree remains clean and still lacks code fixes for the underlying repair-loop weakness.

## Assumptions Made

- Assumption: `origin/main` now includes commit `a20fe4a` and should be treated as the baseline for any follow-up work
- Assumption: the user still wants both deliverables previously requested, namely repo-pushed optimization docs and a more automatic CLI UX
- Assumption: keeping existing subcommands as compatibility paths is safer than deleting them outright, unless the user explicitly asks for a breaking CLI change
- Assumption: `.env` still contains a valid `ARK_API_KEY`, because it was present during the translation run

## Potential Gotchas

- `tools/check_untranslated.py` will fail if you try to save a report file before fixing the undefined `epub_path` reference at `tools/check_untranslated.py:262`
- `main.py:268-272` monkey-patches `HTMLProcessor` filters during repair; changing surrounding logic casually can create hard-to-debug side effects
- `processors/html_worker.py:253` currently parses XML/XHTML via BeautifulSoup with `lxml` HTML mode, which already emitted `XMLParsedAsHTMLWarning` during the real EPUB run
- The translation artifact lives outside the repo, so `git status` will not tell you whether the generated EPUB was changed
- The `code-reviewer` helper `pr_analyzer.py` from the external skill set is broken in this environment because it defines `--head/-h` and conflicts with argparse help; prefer the quality checker or direct file inspection

## Environment State

## Tools/Services Used

- `uv`: project dependency management, lockfile generation, sync, and test execution
- GitHub `origin/main`: remote branch that already contains the `uv` migration commit
- ARK/Doubao translation API: used through the project's existing client and `ARK_API_KEY`
- `session-handoff` skill scripts: created and validated this handoff
- `code-reviewer` workflow: used for code-quality inspection, supplemented by direct source review and a real translation run

## Active Processes

- None intentionally left running

## Environment Variables

- `ARK_API_KEY`

## Related Resources

- `main.py`
- `tools/check_untranslated.py`
- `processors/html_worker.py`
- `core/token_tracker.py`
- `pyproject.toml`
- `README.md`
- `.github/workflows/ci.yml`
- `/home/louis/Downloads/The Dialectic of Sex (Shulamith Firestone) (z-library.sk, 1lib.sk, z-lib.sk)_zh.epub`

---

**Security Reminder**: Before finalizing, run `validate_handoff.py` to check for accidental secret exposure.
