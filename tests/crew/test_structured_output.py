"""Tests for structured-output validation and serialization."""

from types import SimpleNamespace

from src.crew.structured_output import (
    output_model_for_task,
    serialize_structured_output,
    validate_task_output,
)

# ── output_model_for_task ──────────────────────────────────────────────────────


def test_output_model_for_task_returns_model_for_known_task():
    model = output_model_for_task("analyze_valuation_ratios")
    assert model is not None
    assert model.__name__ == "ValuationOutput"


def test_output_model_for_task_returns_none_for_unknown():
    assert output_model_for_task("nonexistent_task") is None


# ── validate_task_output ───────────────────────────────────────────────────────


def test_validate_valuation_output_backfills_summary_from_overview():
    task_output = SimpleNamespace(
        json_dict={
            "overview": "Valuation appears fair versus peers.",
            "metrics": [
                {"label": "P/E", "value": "22.1x", "source": "company_info.csv"},
            ],
            "implications": ["Growth expectations are already priced in."],
            "citations": [],
        }
    )
    model = validate_task_output("analyze_valuation_ratios", task_output)
    assert model is not None
    assert model.summary == "Valuation appears fair versus peers."


def test_validate_returns_none_for_unknown_task():
    task_output = SimpleNamespace(raw="some text")
    assert validate_task_output("nonexistent_task", task_output) is None
    assert validate_task_output(None, task_output) is None


def test_validate_returns_none_for_empty_output():
    task_output = SimpleNamespace(raw="", json_dict=None, pydantic=None)
    assert validate_task_output("analyze_valuation_ratios", task_output) is None


# ── serialize_structured_output ────────────────────────────────────────────────


def test_serialize_valuation_output():
    from src.crew.schemas import ValuationOutput

    model = ValuationOutput.model_validate(
        {
            "summary": "Valuation appears fair relative to peers.",
            "metrics": [
                {"label": "P/E", "value": "22.1x", "source": "company_info.csv"},
            ],
            "implications": ["Growth expectations priced into current valuation."],
            "citations": [],
        }
    )
    text = serialize_structured_output("analyze_valuation_ratios", model)
    assert "Structured Summary:" in text
    assert "P/E" in text


def test_serialize_returns_empty_for_unknown_model():
    from pydantic import BaseModel

    class UnknownModel(BaseModel):
        foo: str = "bar"

    assert serialize_structured_output(None, UnknownModel()) == ""
