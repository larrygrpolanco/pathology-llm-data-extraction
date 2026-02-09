"""
Confidence Calibration Analysis
Analyzes per-field extraction results with confidence scoring
"""

import pandas as pd
import json
import re
from pathlib import Path
from sklearn.metrics import (
    precision_recall_fscore_support,
    accuracy_score,
    confusion_matrix,
)
from collections import defaultdict
import sys

# Add parent directory to path to import post_processing_utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
try:
    import post_processing_utils as pp
except ImportError:
    # Fallback: import from current directory if copied
    import post_processing_utils as pp

# Import user settings from config module
from config import settings

# =============================================================================
# CONFIGURATION (Uses settings from config.py)
# =============================================================================

# Use paths from settings
BASE_DIR = settings.BASE_DIR
OUTPUT_DIR = settings.OUTPUT_DIR
RESULTS_DIR = settings.RESULTS_DIR
ANALYSIS_DIR = settings.ANALYSIS_DIR
GOLD_STANDARD_CSV = settings.GOLD_STANDARD_CSV

# Ensure directories exist
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

# Field configuration matching the original study
FIELDS_CONFIG = {
    "histologic_variant": {
        "type": "categorical",
        "norm": pp.normalize_histologic_variant,
    },
    "extrathyroidal_extension": {"type": "categorical", "norm": pp.normalize_ete},
    "margins": {"type": "categorical", "norm": pp.normalize_margins},
    "tumor_site": {"type": "categorical", "norm": pp.normalize_site},
    "tumor_size": {"type": "numeric", "norm": pp.normalize_numeric_float},
}

# Use field order from settings
FIELD_ORDER = list(settings.FIELDS_TO_ANALYZE)

# =============================================================================
# BASELINE METRICS (Same as original study)
# =============================================================================


def calculate_baseline_metrics(df, field):
    """Calculate standard accuracy metrics for a field."""
    y_true = df[f"{field}_gold_norm"].fillna("missing").astype(str).tolist()
    y_pred = df[f"{field}_llm_norm"].fillna("missing").astype(str).tolist()

    acc = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )

    return {"Accuracy": acc, "F1": f1, "Precision": precision, "Recall": recall}


# =============================================================================
# CONFIDENCE CALIBRATION METRICS
# =============================================================================


def calculate_confidence_calibration(df, field):
    """
    Calculate confidence calibration metrics for a field.

    Returns dict with:
    - counts by confidence level
    - accuracy by confidence level
    - calibration score (correlation between confidence and accuracy)
    """
    results = {
        "high": {"count": 0, "correct": 0, "wrong": 0, "accuracy": 0.0},
        "medium": {"count": 0, "correct": 0, "wrong": 0, "accuracy": 0.0},
        "low": {"count": 0, "correct": 0, "wrong": 0, "accuracy": 0.0},
    }

    for _, row in df.iterrows():
        confidence = str(row.get(f"{field}_confidence", "")).lower()
        is_correct = row.get(f"{field}_match") == "MATCH"

        if confidence in results:
            results[confidence]["count"] += 1
            if is_correct:
                results[confidence]["correct"] += 1
            else:
                results[confidence]["wrong"] += 1

    # Calculate accuracy for each confidence level
    for level in ["high", "medium", "low"]:
        count = results[level]["count"]
        if count > 0:
            results[level]["accuracy"] = results[level]["correct"] / count

    return results


def calculate_workflow_metrics(df, field):
    """
    Calculate practical workflow metrics.

    Returns:
    - Metrics for different review strategies
    """
    total_cases = len(df)
    total_errors = len(df[df[f"{field}_match"] == "MISMATCH"])

    # Count by confidence level
    low_conf = df[df[f"{field}_confidence"].str.lower() == "low"]
    med_conf = df[df[f"{field}_confidence"].str.lower() == "medium"]
    high_conf = df[df[f"{field}_confidence"].str.lower() == "high"]

    # Strategy 1: Review only LOW confidence
    low_review_count = len(low_conf)
    low_caught = len(low_conf[low_conf[f"{field}_match"] == "MISMATCH"])
    low_missed = total_errors - low_caught

    # Strategy 2: Review LOW + MEDIUM confidence
    low_med_review_count = len(low_conf) + len(med_conf)
    low_med_caught = low_caught + len(
        med_conf[med_conf[f"{field}_match"] == "MISMATCH"]
    )
    low_med_missed = total_errors - low_med_caught

    return {
        "total_cases": total_cases,
        "total_errors": total_errors,
        "error_rate": total_errors / total_cases if total_cases > 0 else 0,
        # Strategy 1: Review LOW only
        "review_low_count": low_review_count,
        "review_low_pct": low_review_count / total_cases * 100
        if total_cases > 0
        else 0,
        "low_caught": low_caught,
        "low_caught_pct": low_caught / total_errors * 100 if total_errors > 0 else 0,
        "low_missed": low_missed,
        # Strategy 2: Review LOW + MEDIUM
        "review_low_med_count": low_med_review_count,
        "review_low_med_pct": low_med_review_count / total_cases * 100
        if total_cases > 0
        else 0,
        "low_med_caught": low_med_caught,
        "low_med_caught_pct": low_med_caught / total_errors * 100
        if total_errors > 0
        else 0,
        "low_med_missed": low_med_missed,
    }


# =============================================================================
# REPORTING FUNCTIONS
# =============================================================================


def create_confidence_summary_table(all_confidence_data):
    """Create overall confidence summary across all fields."""
    summary = {
        "high": {"count": 0, "correct": 0, "wrong": 0},
        "medium": {"count": 0, "correct": 0, "wrong": 0},
        "low": {"count": 0, "correct": 0, "wrong": 0},
    }

    for field_data in all_confidence_data.values():
        for level in ["high", "medium", "low"]:
            summary[level]["count"] += field_data[level]["count"]
            summary[level]["correct"] += field_data[level]["correct"]
            summary[level]["wrong"] += field_data[level]["wrong"]

    rows = []
    for level in ["High", "Medium", "Low"]:
        level_key = level.lower()
        count = summary[level_key]["count"]
        correct = summary[level_key]["correct"]
        wrong = summary[level_key]["wrong"]
        accuracy = correct / count * 100 if count > 0 else 0
        pct_of_total = (
            count / sum(summary[l]["count"] for l in ["high", "medium", "low"]) * 100
        )

        rows.append(
            {
                "Confidence": level,
                "Count": count,
                "Correct": correct,
                "Wrong": wrong,
                "Accuracy": f"{accuracy:.1f}%",
                "% of Total": f"{pct_of_total:.1f}%",
            }
        )

    return pd.DataFrame(rows)


def create_field_comparison_table(all_baseline_metrics, all_confidence_data):
    """Create comparison table showing baseline accuracy and confidence calibration by field."""
    rows = []

    for field in FIELD_ORDER:
        baseline = all_baseline_metrics[field]
        conf_data = all_confidence_data[field]

        row = {
            "Field": field.replace("_", " ").title(),
            "Accuracy": f"{baseline['Accuracy']:.3f}",
            "F1": f"{baseline['F1']:.3f}",
            "High Conf Acc": f"{conf_data['high']['accuracy']:.1%}"
            if conf_data["high"]["count"] > 0
            else "N/A",
            "Med Conf Acc": f"{conf_data['medium']['accuracy']:.1%}"
            if conf_data["medium"]["count"] > 0
            else "N/A",
            "Low Conf Acc": f"{conf_data['low']['accuracy']:.1%}"
            if conf_data["low"]["count"] > 0
            else "N/A",
            "High Count": conf_data["high"]["count"],
            "Med Count": conf_data["medium"]["count"],
            "Low Count": conf_data["low"]["count"],
        }
        rows.append(row)

    return pd.DataFrame(rows)


def create_workflow_summary_table(all_workflow_metrics):
    """Create summary of workflow efficiency across fields."""
    # Aggregate across fields (average the percentages)
    total_cases = sum(m["total_cases"] for m in all_workflow_metrics.values())
    total_errors = sum(m["total_errors"] for m in all_workflow_metrics.values())

    avg_error_rate = sum(m["error_rate"] for m in all_workflow_metrics.values()) / len(
        all_workflow_metrics
    )
    avg_review_low_pct = sum(
        m["review_low_pct"] for m in all_workflow_metrics.values()
    ) / len(all_workflow_metrics)
    avg_low_caught_pct = sum(
        m["low_caught_pct"] for m in all_workflow_metrics.values()
    ) / len(all_workflow_metrics)
    avg_review_low_med_pct = sum(
        m["review_low_med_pct"] for m in all_workflow_metrics.values()
    ) / len(all_workflow_metrics)
    avg_low_med_caught_pct = sum(
        m["low_med_caught_pct"] for m in all_workflow_metrics.values()
    ) / len(all_workflow_metrics)

    rows = [
        {"Metric": "Baseline Error Rate", "Value": f"{avg_error_rate:.1%}"},
        {
            "Metric": "Review Only LOW Conf",
            "Cases to Review": f"{avg_review_low_pct:.1f}%",
            "Errors Caught": f"{avg_low_caught_pct:.1f}%",
            "Efficiency": f"Save {100 - avg_review_low_pct:.1f}% of review time, catch {avg_low_caught_pct:.1f}% of errors",
        },
        {
            "Metric": "Review LOW + MEDIUM Conf",
            "Cases to Review": f"{avg_review_low_med_pct:.1f}%",
            "Errors Caught": f"{avg_low_med_caught_pct:.1f}%",
            "Efficiency": f"Save {100 - avg_review_low_med_pct:.1f}% of review time, catch {avg_low_med_caught_pct:.1f}% of errors",
        },
    ]

    return pd.DataFrame(rows)


def save_detailed_field_analysis(df, field, output_dir):
    """Save detailed analysis for a specific field."""

    # Create detailed breakdown
    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "patient_id": row["patient_id"],
                "gold_value": row[field],  # Original gold standard value
                "llm_value": row[f"{field}_value"],  # LLM extracted value
                "llm_normalized": row[f"{field}_llm_norm"],
                "gold_normalized": row[f"{field}_gold_norm"],
                "match": row[f"{field}_match"],
                "confidence": row[f"{field}_confidence"],
                "reasoning": row[f"{field}_reasoning"],
            }
        )

    detail_df = pd.DataFrame(rows)

    # Save full detail
    detail_df.to_csv(output_dir / f"{field}_detailed.csv", index=False)

    # Save only mismatches with low confidence (potential issues)
    mismatches_low = detail_df[
        (detail_df["match"] == "MISMATCH")
        & (detail_df["confidence"].str.lower() == "low")
    ]
    mismatches_low.to_csv(output_dir / f"{field}_mismatches_low_conf.csv", index=False)

    # Save mismatches with high confidence (overconfident errors)
    mismatches_high = detail_df[
        (detail_df["match"] == "MISMATCH")
        & (detail_df["confidence"].str.lower() == "high")
    ]
    mismatches_high.to_csv(
        output_dir / f"{field}_mismatches_high_conf.csv", index=False
    )


# =============================================================================
# MAIN ANALYSIS
# =============================================================================


def analyze_split(split_name: str):
    """Run full analysis on a data split."""

    # Validate split and provide helpful error messages
    try:
        split_name = settings.validate_and_help(split_name)
    except (ValueError, FileNotFoundError) as e:
        print(f"\n{str(e)}\n")
        return

    print(f"\n{'=' * 60}")
    print(f"Analyzing {split_name} split")
    print(f"{'=' * 60}\n")

    # Load gold standard
    if not GOLD_STANDARD_CSV.exists():
        print(f"Error: Gold standard not found at {GOLD_STANDARD_CSV}")
        return

    gold_df = pd.read_csv(GOLD_STANDARD_CSV)
    gold_df["patient_id"] = gold_df["patient_id"].astype(str).str.strip()
    print(f"Loaded {len(gold_df)} gold standard records")

    # Load confidence study results
    results_file = RESULTS_DIR / f"confidence_study_{split_name}_aggregated.csv"
    results_df = pd.read_csv(results_file)
    results_df["patient_id"] = results_df["patient_id"].astype(str).str.strip()
    print(f"Loaded {len(results_df)} confidence study results")

    # Merge datasets
    merged = pd.merge(results_df, gold_df, on="patient_id", how="inner")
    print(f"Merged dataset: {len(merged)} patients")

    # Storage for all metrics
    all_baseline_metrics = {}
    all_confidence_data = {}
    all_workflow_metrics = {}

    # Analyze each field
    for field in FIELD_ORDER:
        print(f"\n--- Analyzing {field} ---")

        # Normalize values (same as original study)
        norm_func = FIELDS_CONFIG[field]["norm"]

        # Get LLM value column
        llm_col = f"{field}_value"
        gold_col = field  # In gold standard, column names don't have suffixes

        merged[f"{field}_llm_norm"] = merged[llm_col].apply(
            lambda x: norm_func(x) if pd.notnull(x) and x != "" else "not available"
        )
        merged[f"{field}_gold_norm"] = merged[gold_col].apply(
            lambda x: norm_func(x) if pd.notnull(x) else "not available"
        )

        # Determine match
        merged[f"{field}_match"] = (
            merged[f"{field}_llm_norm"] == merged[f"{field}_gold_norm"]
        )
        merged[f"{field}_match"] = merged[f"{field}_match"].map(
            {True: "MATCH", False: "MISMATCH"}
        )

        # Calculate baseline metrics
        baseline = calculate_baseline_metrics(merged, field)
        all_baseline_metrics[field] = baseline
        print(
            f"  Baseline F1: {baseline['F1']:.3f}, Accuracy: {baseline['Accuracy']:.3f}"
        )

        # Calculate confidence calibration
        conf_cal = calculate_confidence_calibration(merged, field)
        all_confidence_data[field] = conf_cal

        print(
            f"  High conf: {conf_cal['high']['count']} cases, {conf_cal['high']['accuracy']:.1%} accurate"
        )
        print(
            f"  Med conf:  {conf_cal['medium']['count']} cases, {conf_cal['medium']['accuracy']:.1%} accurate"
        )
        print(
            f"  Low conf:  {conf_cal['low']['count']} cases, {conf_cal['low']['accuracy']:.1%} accurate"
        )

        # Calculate workflow metrics
        workflow = calculate_workflow_metrics(merged, field)
        all_workflow_metrics[field] = workflow

        print(
            f"  Review LOW only: catch {workflow['low_caught_pct']:.1f}% of errors by reviewing {workflow['review_low_pct']:.1f}% of cases"
        )

    # Create output directory for this split
    split_analysis_dir = ANALYSIS_DIR / split_name
    split_analysis_dir.mkdir(parents=True, exist_ok=True)

    # Generate reports
    print(f"\n{'=' * 60}")
    print("GENERATING REPORTS")
    print(f"{'=' * 60}\n")

    # 1. Overall confidence summary
    conf_summary = create_confidence_summary_table(all_confidence_data)
    print("\n=== CONFIDENCE CALIBRATION SUMMARY (All Fields) ===")
    print(conf_summary.to_string(index=False))
    conf_summary.to_csv(split_analysis_dir / "confidence_summary.csv", index=False)

    # 2. Field comparison table
    field_comparison = create_field_comparison_table(
        all_baseline_metrics, all_confidence_data
    )
    print("\n=== FIELD COMPARISON ===")
    print(field_comparison.to_string(index=False))
    field_comparison.to_csv(split_analysis_dir / "field_comparison.csv", index=False)

    # 3. Workflow efficiency summary
    workflow_summary = create_workflow_summary_table(all_workflow_metrics)
    print("\n=== WORKFLOW EFFICIENCY ===")
    print(workflow_summary.to_string(index=False))
    workflow_summary.to_csv(split_analysis_dir / "workflow_efficiency.csv", index=False)

    # 4. Detailed field analyses
    print("\n=== SAVING DETAILED FIELD ANALYSES ===")
    for field in FIELD_ORDER:
        save_detailed_field_analysis(merged, field, split_analysis_dir)
        print(f"  Saved {field} detailed analysis")

    # 5. Save master comparison file
    # Create a comprehensive summary for easy comparison with original study
    summary_rows = []
    for field in FIELD_ORDER:
        baseline = all_baseline_metrics[field]
        conf = all_confidence_data[field]
        workflow = all_workflow_metrics[field]

        summary_rows.append(
            {
                "field": field,
                "accuracy": baseline["Accuracy"],
                "f1_score": baseline["F1"],
                "precision": baseline["Precision"],
                "recall": baseline["Recall"],
                "high_conf_count": conf["high"]["count"],
                "high_conf_accuracy": conf["high"]["accuracy"],
                "medium_conf_count": conf["medium"]["count"],
                "medium_conf_accuracy": conf["medium"]["accuracy"],
                "low_conf_count": conf["low"]["count"],
                "low_conf_accuracy": conf["low"]["accuracy"],
                "review_low_pct": workflow["review_low_pct"],
                "review_low_catch_rate": workflow["low_caught_pct"],
                "review_low_med_pct": workflow["review_low_med_pct"],
                "review_low_med_catch_rate": workflow["low_med_caught_pct"],
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(split_analysis_dir / "master_summary.csv", index=False)

    print(f"\n{'=' * 60}")
    print(f"Analysis complete! Results saved to: {split_analysis_dir}")
    print(f"{'=' * 60}")

    # Print key takeaways
    print("\n=== KEY TAKEAWAYS ===")
    total_high = sum(all_confidence_data[f]["high"]["count"] for f in FIELD_ORDER)
    total_correct_high = sum(
        all_confidence_data[f]["high"]["correct"] for f in FIELD_ORDER
    )
    total_low = sum(all_confidence_data[f]["low"]["count"] for f in FIELD_ORDER)
    total_correct_low = sum(
        all_confidence_data[f]["low"]["correct"] for f in FIELD_ORDER
    )

    if total_high > 0:
        print(
            f"When GPT says HIGH confidence: {total_correct_high / total_high:.1%} are correct"
        )
    if total_low > 0:
        print(
            f"When GPT says LOW confidence: {total_correct_low / total_low:.1%} are correct"
        )

    avg_catch_low = sum(
        all_workflow_metrics[f]["low_caught_pct"] for f in FIELD_ORDER
    ) / len(FIELD_ORDER)
    avg_review_low = sum(
        all_workflow_metrics[f]["review_low_pct"] for f in FIELD_ORDER
    ) / len(FIELD_ORDER)
    print(
        f"By reviewing only LOW confidence cases ({avg_review_low:.1f}% of data), you catch {avg_catch_low:.1f}% of errors"
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze confidence calibration results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Configuration:
  Default split: {settings.DEFAULT_SPLIT}
  Available splits: {", ".join(settings.AVAILABLE_SPLITS)}
  Results directory: {settings.RESULTS_DIR}

To change defaults, edit: {settings.BASE_DIR / "config.py"}
Or set environment variables:
  CONFIDENCE_DEFAULT_SPLIT=dev
  CONFIDENCE_OUTPUT_DIR=/path/to/output
        """,
    )
    parser.add_argument(
        "--split",
        default=settings.DEFAULT_SPLIT,
        choices=settings.AVAILABLE_SPLITS,
        help=f"Data split to analyze (default: {settings.DEFAULT_SPLIT})",
    )
    parser.add_argument(
        "--list-splits",
        action="store_true",
        help="Show available splits and their status",
    )
    args = parser.parse_args()

    if args.list_splits:
        settings.print_available_splits()
        return

    analyze_split(args.split)


if __name__ == "__main__":
    main()
