"""Enums for processing stages, substages, and status types."""

from enum import Enum
from typing import Dict, List, Optional

# SINGLE SOURCE OF TRUTH — display names and substage ordering
# To add a stage or substage: add an entry here AND a matching member below.
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


class ProcessingStage(str, Enum):
    """Top-level pipeline stages."""

    STARTING = "starting"
    VALIDATING = "validating"
    DOWNLOADING_DATA = "downloading_data"
    ANALYZING = "analyzing"
    COMPLETE = "complete"

    @property
    def display_name(self) -> str:
        return STAGE_REGISTRY[self.value]["display_name"]

    @property
    def substages(self) -> "List[SubStage]":
        return [SubStage(k) for k in STAGE_REGISTRY[self.value]["substages"]]


class SubStage(str, Enum):
    """Pipeline substages."""

    # validating
    VALIDATING_SYMBOL = "validating_symbol"

    # downloading_data
    DOWNLOADING_COMPANY_PROFILE = "downloading_company_profile"
    DOWNLOADING_PRICE_HISTORY = "downloading_price_history"
    DOWNLOADING_FINANCIALS = "downloading_financials"
    DOWNLOADING_MARKET_INTEL = "downloading_market_intel"
    DOWNLOADING_BENCHMARKS = "downloading_benchmarks"
    DOWNLOADING_NEWS = "downloading_news"
    DOWNLOADING_TRENDS = "downloading_trends"
    SAVING_DATA = "saving_data"

    # analyzing
    VALIDATING_DATA_SANITY = "validating_data_sanity"
    ANALYZING_VALUATION_RATIOS = "analyzing_valuation_ratios"
    ANALYZING_PRICE_PERFORMANCE = "analyzing_price_performance"
    ANALYZING_FINANCIAL_HEALTH = "analyzing_financial_health"
    ANALYZING_MARKET_SENTIMENT = "analyzing_market_sentiment"
    REVIEWING_ANALYSIS = "reviewing_analysis"
    GENERATING_INVESTMENT_REPORT = "generating_investment_report"

    @property
    def display_name(self) -> str:
        for stage_data in STAGE_REGISTRY.values():
            subs = stage_data["substages"]
            if self.value in subs:
                return subs[self.value]
        return self.value.replace("_", " ")

    @property
    def parent_stage(self) -> Optional[ProcessingStage]:
        for stage_id, stage_data in STAGE_REGISTRY.items():
            if self.value in stage_data["substages"]:
                return ProcessingStage(stage_id)
        return None


class StatusType(str, Enum):
    """Status types for processing steps."""

    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"

    @property
    def display_message(self) -> str:
        return {"in_progress": "", "success": "success", "failed": "failed"}[self.value]


class ValidationErrorCode(str, Enum):
    """Error codes for symbol validation."""

    INVALID_FORMAT = "invalid_format"
    SYMBOL_NOT_FOUND = "symbol_not_found"
    MARKET_ERROR = "market_error"


def validate_stage_substage(stage: ProcessingStage, substage: Optional[SubStage]) -> bool:
    """Validate that a substage belongs to a stage."""
    return substage is None or substage.parent_stage == stage


def get_total_pipeline_steps() -> int:
    """Derive the expected workspace-entry count from the stage registry.

    Each stage with substages also emits a stage-level transition entry
    (e.g. 'Downloading data...', 'Processing...'), hence len + 1.
    Stages without substages emit a single stage-level entry.
    """
    return sum(len(s["substages"]) + 1 for key, s in STAGE_REGISTRY.items() if key != "complete")
