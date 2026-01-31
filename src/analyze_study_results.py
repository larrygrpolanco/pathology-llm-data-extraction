
import pandas as pd
import json
import numpy as np
from pathlib import Path
from sklearn.metrics import precision_recall_fscore_support, accuracy_score
import sys

# Add src to path if needed or handle import
try:
    import src.post_processing_utils as pp
except ImportError:
    import post_processing_utils as pp

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
GOLD_STANDARD_CSV = BASE_DIR / "data" / "gold_standard" / "thyroid_gold_standard.csv"
LOGS_DIR = BASE_DIR / "output" / "study_logs"
OUTPUT_DIR = BASE_DIR / "output" / "study_results"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FIELDS_CONFIG = {
    "histologic_type": {"type": "categorical", "norm": pp.normalize_text},
    "histologic_variant": {"type": "categorical", "norm": pp.normalize_histologic_variant},
    "extrathyroidal_extension": {"type": "categorical", "norm": pp.normalize_ete},
    "margins": {"type": "categorical", "norm": pp.normalize_margins},
    "tumor_site": {"type": "categorical", "norm": pp.normalize_site},
    "focality": {"type": "categorical", "norm": pp.normalize_text},
    "lymph_nodes_resected": {"type": "categorical", "norm": pp.normalize_text},
    "tumor_size": {"type": "numeric", "norm": pp.normalize_numeric_float},
    "lymph_nodes_positive_count": {"type": "numeric", "norm": pp.normalize_numeric_int},
}

def load_logs():
    return list(LOGS_DIR.glob("*.csv"))

def parse_json_col(row):
    try:
        return json.loads(row['parsed_json'])
    except:
        return {}

def calculate_metrics(df, field, config):
    y_true = df[f"{field}_gold_norm"].fillna("missing").astype(str).tolist()
    y_pred = df[f"{field}_llm_norm"].fillna("missing").astype(str).tolist()
    
    # Exact Match Accuracy
    acc = accuracy_score(y_true, y_pred)
    
    # F1 (Weighted)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted', zero_division=0)
    
    return {
        "Accuracy": acc,
        "F1": f1,
        "Precision": precision,
        "Recall": recall
    }

def main():
    if not GOLD_STANDARD_CSV.exists():
        print("Gold standard missing.")
        return

    gold_df = pd.read_csv(GOLD_STANDARD_CSV)
    # Ensure correct types for merging
    gold_df['patient_id'] = gold_df['patient_id'].astype(str).str.strip()
    
    log_files = load_logs()
    if not log_files:
        print("No log files found in output/study_logs/.")
        return

    all_metrics = []

    for log_file in log_files:
        model_name = log_file.stem.replace("study_dev_", "").replace("study_test_", "").replace("model_", "")
        split_name = "test" if "test" in log_file.name else "dev" if "dev" in log_file.name else "unknown"
        
        print(f"Processing {model_name} ({split_name})...")
        
        try:
            llm_df = pd.read_csv(log_file)
        except Exception as e:
            print(f"Error reading {log_file}: {e}")
            continue
            
        llm_df = llm_df[llm_df['status'] == 'success']
        if len(llm_df) == 0:
            print("No success rows.")
            continue
            
        # Parse JSON
        json_data = llm_df.apply(parse_json_col, axis=1)
        json_df = pd.json_normalize(json_data)
        
        # Merge extraction back to log
        llm_df = pd.concat([llm_df.reset_index(drop=True), json_df.reset_index(drop=True)], axis=1)
        llm_df['patient_id'] = llm_df['patient_id'].astype(str).str.strip()
        
        # Join with Gold
        merged = pd.merge(llm_df, gold_df, on='patient_id', suffixes=('_llm', '_gold'))
        
        # Normalize and Compare
        for field, config in FIELDS_CONFIG.items():
            norm_func = config['norm']
            
            # Helper to safely apply normalization
            def safe_norm(val):
                return norm_func(val)

            # Check if columns exist
            col_llm = f"{field}_llm" if f"{field}_llm" in merged.columns else field
            col_gold = f"{field}_gold" if f"{field}_gold" in merged.columns else field
            
            if col_llm not in merged.columns: 
                merged[col_llm] = None
            if col_gold not in merged.columns:
                merged[col_gold] = None

            merged[f"{field}_llm_norm"] = merged[col_llm].apply(safe_norm)
            merged[f"{field}_gold_norm"] = merged[col_gold].apply(safe_norm)
            
            # Metrics
            metrics = calculate_metrics(merged, field, config)
            metrics['Model'] = model_name
            metrics['Split'] = split_name
            metrics['Field'] = field
            all_metrics.append(metrics)
            
        # Save detailed comparison
        out_path = OUTPUT_DIR / f"detailed_{split_name}_{model_name}.csv"
        # Select relevant cols
        cols = ['patient_id']
        for field in FIELDS_CONFIG.keys():
            cols.extend([f"{field}_gold", f"{field}_llm", f"{field}_llm_norm"])
        
        merged[cols].to_csv(out_path, index=False)
        print(f"Saved detailed comparison to {out_path}")

    # Save Summary
    if all_metrics:
        summary_df = pd.DataFrame(all_metrics)
        summary_df = summary_df[['Model', 'Split', 'Field', 'Accuracy', 'F1', 'Precision', 'Recall']]
        summary_df.to_csv(OUTPUT_DIR / "summary_metrics.csv", index=False)
        print(f"\nSummary saved to {OUTPUT_DIR / 'summary_metrics.csv'}")
        print(summary_df)
    else:
        print("No metrics computed.")

if __name__ == "__main__":
    main()
