import pandas as pd
import json
import re
from pathlib import Path
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

try:
    import src.post_processing_utils as pp
except ImportError:
    import post_processing_utils as pp

BASE_DIR = Path(__file__).resolve().parent.parent
GOLD_STANDARD_CSV = BASE_DIR / "data" / "gold_standard" / "thyroid_gold_standard.csv"
LOGS_DIR = BASE_DIR / "output" / "study_logs"
OUTPUT_DIR = BASE_DIR / "output" / "study_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FIELDS_CONFIG = {
    # "histologic_type": {"type": "categorical", "norm": pp.normalize_text},
    "histologic_variant": {
        "type": "categorical",
        "norm": pp.normalize_histologic_variant,
    },
    "extrathyroidal_extension": {"type": "categorical", "norm": pp.normalize_ete},
    "margins": {"type": "categorical", "norm": pp.normalize_margins},
    "tumor_site": {"type": "categorical", "norm": pp.normalize_site},
    # "focality": {"type": "categorical", "norm": pp.normalize_text},
    # "lymph_nodes_resected": {"type": "categorical", "norm": pp.normalize_text},
    "tumor_size": {"type": "numeric", "norm": pp.normalize_numeric_float},
    # "lymph_nodes_positive_count": {"type": "numeric", "norm": pp.normalize_numeric_int},
}


def calculate_metrics(df, field):
    y_true = df[f"{field}_gold_norm"].fillna("missing").astype(str).tolist()
    y_pred = df[f"{field}_llm_norm"].fillna("missing").astype(str).tolist()
    acc = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )
    return {"Accuracy": acc, "F1": f1, "Precision": precision, "Recall": recall}


def main():
    if not GOLD_STANDARD_CSV.exists():
        return
    gold_df = pd.read_csv(GOLD_STANDARD_CSV)
    gold_df["patient_id"] = gold_df["patient_id"].astype(str).str.strip()

    log_files = list(LOGS_DIR.glob("*.csv"))
    all_metrics = []

    for log_file in log_files:
        # File format: study_{split}_{model_alias}_{mode}.csv
        # We want the "Model" column to be "{model_alias}_{mode}" for comparison
        filename = log_file.stem

        # Regex to extract components
        # Matches: study_dev_gpt-oss-120b_reasoning -> split=dev, model_key=gpt-oss-120b_reasoning
        match = re.match(r"study_([a-z]+)_(.+)", filename)
        if not match:
            continue

        split_name = match.group(1)
        model_display_name = match.group(
            2
        )  # This will be "gpt-oss-120b_standard" or "gpt-oss-120b_reasoning"

        print(f"Processing {model_display_name} ({split_name})...")

        try:
            llm_df = pd.read_csv(log_file)
        except:
            continue

        llm_df = llm_df[llm_df["status"] == "success"]
        if len(llm_df) == 0:
            continue

        # Parse JSON
        json_data = llm_df.apply(
            lambda r: json.loads(r["parsed_json"]) if r["status"] == "success" else {},
            axis=1,
        )
        json_df = pd.json_normalize(json_data)
        llm_df = pd.concat(
            [llm_df.reset_index(drop=True), json_df.reset_index(drop=True)], axis=1
        )
        llm_df["patient_id"] = llm_df["patient_id"].astype(str).str.strip()

        merged = pd.merge(llm_df, gold_df, on="patient_id", suffixes=("_llm", "_gold"))

        for field, config in FIELDS_CONFIG.items():
            norm_func = config["norm"]
            col_llm = f"{field}_llm" if f"{field}_llm" in merged.columns else field

            # Normalize
            merged[f"{field}_llm_norm"] = merged[col_llm].apply(
                lambda x: norm_func(x) if pd.notnull(x) else "not available"
            )
            merged[f"{field}_gold_norm"] = merged[f"{field}_gold"].apply(
                lambda x: norm_func(x) if pd.notnull(x) else "not available"
            )

            # Match
            merged[f"{field}_match"] = (
                merged[f"{field}_llm_norm"] == merged[f"{field}_gold_norm"]
            )
            merged[f"{field}_match"] = merged[f"{field}_match"].map(
                {True: "MATCH", False: "MISMATCH"}
            )

            # Metrics
            met = calculate_metrics(merged, field)
            met["Model"] = model_display_name
            met["Split"] = split_name
            met["Field"] = field
            all_metrics.append(met)

        # Output Detailed File
        # Check for reasoning fields
        reasoning_col = None
        if "_reasoning" in merged.columns:
            reasoning_col = "_reasoning"
        elif "_logic_verification" in merged.columns:
            reasoning_col = "_logic_verification"

        # Detect evidence columns from the JSON data
        evidence_cols = [col for col in merged.columns if col.startswith("evidence_")]

        output_cols = ["patient_id"]
        if reasoning_col:
            output_cols.append(reasoning_col)

        for field in FIELDS_CONFIG:
            output_cols.extend([f"{field}_gold", f"{field}_llm", f"{field}_match"])
            # Add evidence column after match if it exists
            evidence_field = f"evidence_{field}"
            if evidence_field in evidence_cols:
                output_cols.append(evidence_field)

        final_cols = [c for c in output_cols if c in merged.columns]

        # Save Error Audit
        errors_mask = (
            merged[[f"{f}_match" for f in FIELDS_CONFIG]].values == "MISMATCH"
        ).any(axis=1)
        error_df = merged[errors_mask]
        error_df[final_cols].to_csv(
            OUTPUT_DIR / f"errors_{split_name}_{model_display_name}.csv", index=False
        )

    if all_metrics:
        pd.DataFrame(all_metrics).to_csv(
            OUTPUT_DIR / "summary_metrics.csv", index=False
        )
        print("Summary saved.")


if __name__ == "__main__":
    main()
