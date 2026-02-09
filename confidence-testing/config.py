"""
User Settings Configuration
===========================

This module provides user-configurable settings for the confidence testing pipeline.
Users can modify these settings without editing the main code.

Settings can be configured via:
1. This config file (config.py) - modify the values below
2. Environment variables - override specific settings
3. Command-line arguments - override for a single run

Example usage:
    from config import settings

    # Use settings
    results_dir = settings.OUTPUT_DIR / "results"
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class UserSettings:
    """
    User-configurable settings for confidence testing.

    Modify the values below or set environment variables to customize behavior.
    """

    # ============================================================================
    # PATHS (can be absolute or relative to project root)
    # ============================================================================

    # Base directory for the confidence testing module
    # Default: directory containing this config file
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent)

    # Output directory for all results
    # Default: confidence-testing/output
    OUTPUT_DIR: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "output"
    )

    # Results subdirectory (where aggregated CSVs are stored)
    # Default: output/results
    RESULTS_DIR: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "output" / "results"
    )

    # Analysis subdirectory (where analysis outputs go)
    # Default: output/analysis
    ANALYSIS_DIR: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "output" / "analysis"
    )

    # Path to gold standard CSV
    # Default: ../data/gold_standard/thyroid_gold_standard.csv
    GOLD_STANDARD_CSV: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
        / "data"
        / "gold_standard"
        / "thyroid_gold_standard.csv"
    )

    # ============================================================================
    # DATA SPLIT SETTINGS
    # ============================================================================

    # Default data split to analyze if not specified
    # Options: "dev", "test", "final"
    DEFAULT_SPLIT: str = "dev"

    # Available data splits
    AVAILABLE_SPLITS: tuple = ("dev", "test", "final")

    # ============================================================================
    # FIELDS TO ANALYZE
    # ============================================================================

    # Fields to analyze (must match gold standard columns)
    # These are the fields that will be extracted and analyzed
    FIELDS_TO_ANALYZE: tuple = (
        "histologic_variant",
        "tumor_site",
        "extrathyroidal_extension",
        "margins",
        "tumor_size",
    )

    # ============================================================================
    # CONFIDENCE LEVELS
    # ============================================================================

    # Valid confidence levels
    CONFIDENCE_LEVELS: tuple = ("high", "medium", "low")

    # ============================================================================
    # MODEL SETTINGS
    # ============================================================================

    # Default model to use for inference
    # Default: gpt-4o-mini
    DEFAULT_MODEL: str = "gpt-4o-mini"

    # Temperature for model inference (0.0 = deterministic, 1.0 = creative)
    # Default: 0.0
    TEMPERATURE: float = 0.0

    # ============================================================================
    # DISPLAY SETTINGS
    # ============================================================================

    # Whether to show verbose output
    VERBOSE: bool = True

    # Whether to print field-by-field progress
    SHOW_FIELD_PROGRESS: bool = True

    # Format for percentage display
    PERCENTAGE_FORMAT: str = ".1%"

    # ============================================================================
    # INTERNAL - DO NOT MODIFY BELOW
    # ============================================================================

    def __post_init__(self):
        """Initialize computed paths and apply environment variable overrides."""
        self._apply_environment_overrides()
        self._initialize_paths()

    def _apply_environment_overrides(self):
        """Apply environment variable overrides to settings."""
        # Path overrides
        if env_path := os.getenv("CONFIDENCE_BASE_DIR"):
            self.BASE_DIR = Path(env_path)

        if env_path := os.getenv("CONFIDENCE_OUTPUT_DIR"):
            self.OUTPUT_DIR = Path(env_path)

        if env_path := os.getenv("CONFIDENCE_GOLD_STANDARD"):
            self.GOLD_STANDARD_CSV = Path(env_path)

        # Split override
        if env_split := os.getenv("CONFIDENCE_DEFAULT_SPLIT"):
            self.DEFAULT_SPLIT = env_split

        # Model overrides
        if env_model := os.getenv("CONFIDENCE_MODEL"):
            self.DEFAULT_MODEL = env_model

        if env_temp := os.getenv("CONFIDENCE_TEMPERATURE"):
            self.TEMPERATURE = float(env_temp)

        # Display overrides
        if os.getenv("CONFIDENCE_QUIET"):
            self.VERBOSE = False

    def _initialize_paths(self):
        """Initialize computed paths based on BASE_DIR."""
        # Recompute dependent paths based on possibly updated BASE_DIR
        self.OUTPUT_DIR = self.BASE_DIR / "output"
        self.RESULTS_DIR = self.OUTPUT_DIR / "results"
        self.ANALYSIS_DIR = self.OUTPUT_DIR / "analysis"
        self.GOLD_STANDARD_CSV = (
            self.BASE_DIR.parent
            / "data"
            / "gold_standard"
            / "thyroid_gold_standard.csv"
        )

    def get_results_file(self, split: str) -> Path:
        """Get the path to results file for a given split."""
        return self.RESULTS_DIR / f"confidence_study_{split}_aggregated.csv"

    def get_analysis_dir(self, split: str) -> Path:
        """Get the analysis output directory for a given split."""
        return self.ANALYSIS_DIR / split

    def validate_split(self, split: str) -> str:
        """
        Validate a split name and return a helpful error if invalid.

        Args:
            split: The split name to validate

        Returns:
            The validated split name (lowercased)

        Raises:
            ValueError: If split is not valid
        """
        split = split.lower()
        if split not in self.AVAILABLE_SPLITS:
            raise ValueError(
                f"Invalid split: '{split}'\n"
                f"Available splits: {', '.join(self.AVAILABLE_SPLITS)}\n"
                f"\nTo use a different split:\n"
                f"  1. Modify DEFAULT_SPLIT in {__file__}\n"
                f"  2. Set CONFIDENCE_DEFAULT_SPLIT environment variable\n"
                f"  3. Use --split argument (for CLI tools)"
            )
        return split

    def check_results_exist(self, split: str) -> tuple[bool, Path]:
        """
        Check if results file exists for a split.

        Returns:
            Tuple of (exists: bool, path: Path)
        """
        results_file = self.get_results_file(split)
        return results_file.exists(), results_file

    def print_available_splits(self):
        """Print information about available splits and their status."""
        print("\n" + "=" * 60)
        print("Available Data Splits")
        print("=" * 60)

        for split in self.AVAILABLE_SPLITS:
            exists, path = self.check_results_exist(split)
            status = "✓ Ready" if exists else "✗ Not found"
            print(f"  {split:8s} - {status}")
            if not exists:
                print(f"           Expected at: {path}")

        print(f"\nDefault split: {self.DEFAULT_SPLIT}")
        print("=" * 60 + "\n")

    def validate_and_help(self, split: str) -> str:
        """
        Validate split and provide helpful guidance if results don't exist.

        Args:
            split: The split to validate

        Returns:
            Validated split name

        Raises:
            FileNotFoundError: If results file doesn't exist, with helpful message
            ValueError: If split is invalid
        """
        split = self.validate_split(split)
        exists, results_file = self.check_results_exist(split)

        if not exists:
            # Check which splits are available
            available = []
            for s in self.AVAILABLE_SPLITS:
                if self.check_results_exist(s)[0]:
                    available.append(s)

            msg = f"""
{"=" * 70}
ERROR: Results file not found
{"=" * 70}

Expected file: {results_file}

This file doesn't exist yet. You need to run the confidence study first.

TO FIX THIS:

1. Run the confidence study for the '{split}' split:
   
   python confidence-testing/run_confidence_study.py --split {split}

2. Or analyze a different split that already has results:
"""
            if available:
                msg += f"\n   Available splits with results:\n"
                for s in available:
                    msg += f"     - {s}\n"
                msg += f"\n   Run: python confidence-testing/analyze_confidence_results.py --split {available[0]}\n"
            else:
                msg += "\n   No splits have results yet. Run the study first.\n"

            msg += f"\n{'=' * 70}"
            raise FileNotFoundError(msg)

        return split


# Global settings instance - import this in other modules
settings = UserSettings()


# Convenience functions for common operations
def get_settings() -> UserSettings:
    """Get the global settings instance."""
    return settings


def set_default_split(split: str):
    """Programmatically set the default split."""
    settings.DEFAULT_SPLIT = settings.validate_split(split)


def set_verbose(verbose: bool):
    """Programmatically set verbosity."""
    settings.VERBOSE = verbose


if __name__ == "__main__":
    # If run directly, print current settings
    print("\nCurrent Confidence Testing Settings:")
    print("=" * 60)
    print(f"BASE_DIR: {settings.BASE_DIR}")
    print(f"OUTPUT_DIR: {settings.OUTPUT_DIR}")
    print(f"RESULTS_DIR: {settings.RESULTS_DIR}")
    print(f"ANALYSIS_DIR: {settings.ANALYSIS_DIR}")
    print(f"GOLD_STANDARD_CSV: {settings.GOLD_STANDARD_CSV}")
    print(f"DEFAULT_SPLIT: {settings.DEFAULT_SPLIT}")
    print(f"DEFAULT_MODEL: {settings.DEFAULT_MODEL}")
    print(f"TEMPERATURE: {settings.TEMPERATURE}")
    print(f"VERBOSE: {settings.VERBOSE}")
    print("=" * 60)

    settings.print_available_splits()
