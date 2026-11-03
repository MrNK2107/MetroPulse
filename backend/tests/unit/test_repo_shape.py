"""Repository shape: company files exist, simulator-era documents are archived."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

MUST_EXIST = [
    "LICENSE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "NEEDS_INPUT.md",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    "docs/adr/README.md",
    "docs/adr/0001-browser-first-core-loop.md",
    "docs/adr/0002-client-side-data-import.md",
    "docs/adr/0003-remove-the-simulator.md",
    "docs/adr/0004-public-api-in-the-nextjs-app.md",
    "docs/archive/README.md",
    "docs/archive/2026-05-spec-simulator.md",
    "docs/archive/2026-05-implementation-plan-simulator.md",
    "docs/archive/2026-10-status.md",
    "docs/archive/night-runs.md",
    "docs/archive/INDIA_OVERHAUL_PLAN.md",
    "docs/archive/RAG_ENGINE.md",
    "docs/archive/2026-05-26-scenario-driven-simulation-design.md",
    "docs/archive/2026-05-28-nl-simulation-design.md",
    "docs/archive/2026-05-28-nl-simulation.md",
]

MUST_NOT_EXIST = [
    "SPEC.md",
    "IMPLEMENTATION_PLAN.md",
    "status.md",
    "NIGHT_RUN_NOTES.md",
    "docs/INDIA_OVERHAUL_PLAN.md",
    "docs/RAG_ENGINE.md",
    "docs/superpowers/specs/2026-05-26-scenario-driven-simulation-design.md",
    "docs/superpowers/specs/2026-05-28-nl-simulation-design.md",
    "docs/superpowers/plans/2026-05-28-nl-simulation.md",
]


def test_repo_root_is_found():
    assert (REPO_ROOT / "AGENTS.md").is_file()
    assert (REPO_ROOT / "backend").is_dir()


@pytest.mark.parametrize("rel", MUST_EXIST)
def test_file_exists(rel):
    assert (REPO_ROOT / rel).is_file(), f"missing {rel}"


@pytest.mark.parametrize("rel", MUST_NOT_EXIST)
def test_file_archived(rel):
    assert not (REPO_ROOT / rel).exists(), f"{rel} should be in docs/archive/"


def test_license_is_apache_2():
    text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in text and "Version 2.0, January 2004" in text
    assert "2026 MetroPulse contributors" in text


def test_codeowners_names_owner():
    assert "* @MrNK2107" in (REPO_ROOT / ".github/CODEOWNERS").read_text(encoding="utf-8")


def test_dependabot_covers_three_ecosystems():
    text = (REPO_ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
    for eco in ("npm", "pip", "github-actions"):
        assert f'package-ecosystem: "{eco}"' in text
    assert text.count('interval: "weekly"') == 3
