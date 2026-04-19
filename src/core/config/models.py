# SPDX-License-Identifier: MIT
"""Data models for processing logs."""

from dataclasses import dataclass
from typing import Optional

from src.core.config.enums import ProcessingStage, StatusType, SubStage, validate_stage_substage


@dataclass
class LogEntry:
    """Represents a single log entry in the processing pipeline."""

    stage: ProcessingStage
    substage: Optional[SubStage] = None
    status_type: StatusType = StatusType.IN_PROGRESS
    message: Optional[str] = None
    symbol: Optional[str] = None

    def __post_init__(self):
        """Validate log entry after initialization."""
        if not validate_stage_substage(self.stage, self.substage):
            raise ValueError(f"Substage {self.substage} does not belong to stage {self.stage}")


@dataclass(frozen=True)
class ValidationResult:
    """Result of symbol validation."""

    is_valid: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    market: Optional[str] = None  # "US" or "IN"
