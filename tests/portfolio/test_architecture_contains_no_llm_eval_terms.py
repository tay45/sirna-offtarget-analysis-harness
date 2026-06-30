from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = (
    "llm",
    "model evaluation",
    "oracle",
    "system under test",
    "prompt",
    "response",
    "evaluator",
    "agent",
    "judge",
)


def test_architecture_contains_no_llm_eval_terms() -> None:
    text = "\n".join(
        [
            (ROOT / "docs/architecture_current_and_planned.md").read_text(),
            (ROOT / "docs/architecture_current_and_planned.svg").read_text(),
        ]
    ).lower()
    for term in FORBIDDEN:
        assert term not in text
