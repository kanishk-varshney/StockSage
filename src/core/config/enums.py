"""Enums for processing stages, substages, and status types."""

from enum import Enum
from typing import Dict, List, Optional


# SINGLE SOURCE OF TRUTH — add stages/substages here only
# substages: dict mapping ID → human-readable display name
STAGE_REGISTRY: Dict[str, Dict] = {
    "starting": {
        "display_name": "Starting",
        "substages": {},
    },
    "validating": {
        "display_name": "Validating",
        "substages": {
            "validating_symbol": "Validating symbol",
        },
    },
    "downloading_data": {
        "display_name": "Downloading data",
        "substages": {
            "downloading_company_profile": "Downloading company profile",
            "downloading_price_history": "Downloading price history",
            "downloading_financials": "Downloading financials",
            "downloading_market_intel": "Downloading market intel",
            "downloading_benchmarks": "Downloading benchmarks",
            "downloading_news": "Downloading news",
            "downloading_trends": "Downloading trends",
            "saving_data": "Saving data",
        },
    },
    "analyzing": {
        "display_name": "Analyzing",
        "substages": {
            "validating_data_sanity": "Validating data quality",
            "analyzing_valuation_ratios": "Analyzing valuation",
            "analyzing_price_performance": "Analyzing performance & risk",
            "analyzing_financial_health": "Analyzing financial health",
            "analyzing_market_sentiment": "Analyzing market sentiment",
            "reviewing_analysis": "Reviewing analysis quality",
            "generating_investment_report": "Generating final report",
        },
    },
    "complete": {
        "display_name": "Complete",
        "substages": {},
    },
}

# Collect all substage IDs from registry
_SUBSTAGE_IDS = {
    substage_id
    for stage_data in STAGE_REGISTRY.values()
    for substage_id in stage_data["substages"]
}

# Generate enums from registry (no manual enum definitions needed)
ProcessingStage = Enum(
    "ProcessingStage",
    {k.upper(): k for k in STAGE_REGISTRY.keys()},
    type=str,
    module=__name__
)

SubStage = Enum(
    "SubStage",
    {k.upper(): k for k in _SUBSTAGE_IDS},
    type=str,
    module=__name__
)

# Add helper methods
def _get_stage_display_name(stage: ProcessingStage) -> str:
    return STAGE_REGISTRY[stage.value]["display_name"]

def _get_stage_substages(stage: ProcessingStage) -> List[SubStage]:
    return [SubStage(k) for k in STAGE_REGISTRY[stage.value]["substages"]]

def _get_substage_display_name(substage: SubStage) -> str:
    for stage_data in STAGE_REGISTRY.values():
        subs = stage_data["substages"]
        if substage.value in subs:
            return subs[substage.value]
    return substage.value.replace("_", " ")

def _get_substage_parent(substage: SubStage) -> Optional[ProcessingStage]:
    for stage_id, stage_data in STAGE_REGISTRY.items():
        if substage.value in stage_data["substages"]:
            return ProcessingStage(stage_id)
    return None

# Attach as properties
ProcessingStage.display_name = property(_get_stage_display_name)
ProcessingStage.substages = property(_get_stage_substages)
SubStage.display_name = property(_get_substage_display_name)
SubStage.parent_stage = property(_get_substage_parent)


class StatusType(str, Enum):
    """Status types for processing steps."""
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    
    @property
    def display_message(self) -> str:
        return {"in_progress": "", "success": "success", "failed": "failed"}[self.value]


def validate_stage_substage(stage: ProcessingStage, substage: Optional[SubStage]) -> bool:
    """Validate that a substage belongs to a stage."""
    return substage is None or substage.parent_stage == stage


def get_total_pipeline_steps() -> int:
    """Derive the expected workspace-entry count from the stage registry.

    Each stage with substages also emits a stage-level transition entry
    (e.g. 'Downloading data...', 'Processing...'), hence len + 1.
    Stages without substages emit a single stage-level entry.
    """
    return sum(
        len(s["substages"]) + 1
        for key, s in STAGE_REGISTRY.items()
        if key != "complete"
    )


class ValidationErrorCode(str, Enum):
    """Error codes for symbol validation."""
    
    INVALID_FORMAT = "invalid_format"
    SYMBOL_NOT_FOUND = "symbol_not_found"
    MARKET_ERROR = "market_error"
