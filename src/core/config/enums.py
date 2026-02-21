"""Enums for processing stages, substages, and status types."""

from enum import Enum
from typing import Dict, List, Optional


# SINGLE SOURCE OF TRUTH - add stages/substages here only
# Substages are just IDs - display names auto-generated (underscores -> spaces)
STAGE_REGISTRY: Dict[str, Dict] = {
    "starting": {
        "display_name": "Starting",
        "substages": []
    },
    "validating": {
        "display_name": "Validating",
        "substages": ["validating_symbol"]
    },
    "downloading_data": {
        "display_name": "Downloading data",
        "substages": [
            "downloading_company_profile",
            "downloading_price_history",
            "downloading_financials",
            "downloading_market_intel",
            "downloading_benchmarks",
            "downloading_news",
            "downloading_trends",
            "saving_data"
        ]
    },
    "analyzing": {
        "display_name": "Analyzing",
        "substages": [
            "analyzing_valuation_ratios",
            "analyzing_price_performance",
            "analyzing_financial_health",
            "analyzing_market_sentiment",
            "reviewing_analysis",
            "generating_investment_report",
        ]
    },
    "complete": {
        "display_name": "Complete",
        "substages": []
    }
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
    # Auto-generate display name: replace underscores with spaces
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


class ValidationErrorCode(str, Enum):
    """Error codes for symbol validation."""
    
    INVALID_FORMAT = "invalid_format"
    SYMBOL_NOT_FOUND = "symbol_not_found"
    MARKET_ERROR = "market_error"
