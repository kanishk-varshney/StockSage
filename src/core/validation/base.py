"""Abstract base classes for symbol validators."""

from abc import ABC, abstractmethod

from src.core.config.models import ValidationResult


class FormatValidator(ABC):
    """Abstract base class for format validators."""
    
    @abstractmethod
    def validate(self, symbol: str) -> ValidationResult:
        """
        Validate symbol format.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            ValidationResult indicating if format is valid
        """
        pass


class MarketValidator(ABC):
    """Abstract base class for market validators."""
    
    @abstractmethod
    def validate(self, symbol: str) -> ValidationResult:
        """
        Validate symbol exists in market.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            ValidationResult indicating if symbol exists in market
        """
        pass
