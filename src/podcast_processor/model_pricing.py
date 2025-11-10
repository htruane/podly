"""Model pricing configuration loader for custom LiteLLM pricing."""

import csv
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ModelPricingConfig:
    """Manages custom model pricing configuration from CSV file."""

    def __init__(self, csv_path: Optional[Path] = None):
        """
        Initialize pricing configuration.

        Args:
            csv_path: Path to CSV file. If None, uses default location.
        """
        if csv_path is None:
            # Default to model_pricing.csv in src directory
            csv_path = Path(__file__).parent.parent / "model_pricing.csv"

        self.csv_path = csv_path
        self._pricing_cache: Dict[str, Tuple[float, float]] = {}
        self._load_pricing()

    def _load_pricing(self) -> None:
        """Load pricing from CSV file into cache."""
        if not self.csv_path.exists():
            logger.warning(
                f"Model pricing CSV not found at {self.csv_path}. "
                f"Custom pricing will not be available."
            )
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                # Filter out comment lines
                lines = [line for line in f if not line.strip().startswith("#")]
                reader = csv.DictReader(lines)
                for row in reader:
                    model_pattern = row["model_pattern"].strip().lower()
                    input_cost = float(row["input_cost_per_million"])
                    output_cost = float(row["output_cost_per_million"])

                    # Convert from per-million to per-token
                    input_cost_per_token = input_cost / 1_000_000
                    output_cost_per_token = output_cost / 1_000_000

                    self._pricing_cache[model_pattern] = (
                        input_cost_per_token,
                        output_cost_per_token,
                    )

            logger.info(
                f"Loaded custom pricing for {len(self._pricing_cache)} model patterns"
            )
        except Exception as e:
            logger.error(f"Failed to load model pricing from {self.csv_path}: {e}")
            self._pricing_cache = {}

    def get_pricing(
        self, model_name: str
    ) -> Optional[Tuple[float, float]]:
        """
        Get pricing for a model name.

        Args:
            model_name: Model name to lookup

        Returns:
            Tuple of (input_cost_per_token, output_cost_per_token) or None
        """
        model_name_lower = model_name.lower()

        for pattern, (input_cost, output_cost) in self._pricing_cache.items():
            if pattern in model_name_lower:
                return (input_cost, output_cost)

        return None

    def reload(self) -> None:
        """Reload pricing from CSV file."""
        self._pricing_cache = {}
        self._load_pricing()


# Global instance
_pricing_config: Optional[ModelPricingConfig] = None


def get_pricing_config() -> ModelPricingConfig:
    """Get or create global pricing configuration instance."""
    global _pricing_config  # pylint: disable=global-statement
    if _pricing_config is None:
        _pricing_config = ModelPricingConfig()
    return _pricing_config
