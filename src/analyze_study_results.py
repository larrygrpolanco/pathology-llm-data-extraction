import pandas as pd
import json
import re
import numpy as np
from pathlib import Path
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

# Add src to path if needed
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

class ExplainableErrorAnalyzer:
    """
    Forensic audit logic to classify why the LLM disagreed with the Gold Standard.
    """
    @staticmethod
    def classify_ete_error(row):
        gold = str(row['extrathyroidal_extension_gold_norm'])
        llm = str(row['extrathyroidal_extension_llm_norm'])
        t_stage = str(row['pathologic_T']) # e.g., "T3", "T1b"
        size = float(row['tumor_size_gold']) if pd.notnull(row['tumor_size_gold']) and row['tumor_size_gold'] != 'Not Available' else 0.0

        if gold == llm: return "Correct"
        
        # LOGIC 1: The T3 Discrepancy (Gold says "No ETE", but Stage is T3 and Size < 4cm)
        # In AJCC 6/7th, T3 is >4cm OR Minimal ETE.
        # If Size < 4cm and it's T3, ETE *must* be present. If Gold says "No ETE", Gold is wrong/inconsistent.
        if gold == "no ete" and llm == "microscopic":
            if "T3" in t_stage and size < 4.0 and size > 0:
                return "Registry_Inconsistency_T3_Definition"
        
        # LOGIC 2: The "Gross" vs "Micro" Staging Artifact
        # T3b (Strap muscles) is often coded as "Gross/Advanced" in some registries, but clinically "Microscopic" in others.
        if gold == "gross" and llm == "microscopic":
            return "Definition_Mismatch_StrapMuscle"

        return "Model_Error"

    @staticmethod
    def classify_site_error(row):
        gold = str(row['tumor_site_gold_norm'])
        llm = str(row['tumor_site_llm_norm'])
        
        if gold == llm: return "Correct"
        
        # LOGIC: Bilateral Staging vs Dominant Nodule
        if gold == "bilateral" and llm in ["right lobe", "left lobe", "isthmus"]:
            return "Definition_Mismatch_Bilateral_vs_Dominant"
            
        return "Model_Error"

def calculate_metrics(df, field, config):
    y_true = df[f"{field}_gold_norm"].fillna("missing").astype(str).tolist()
    y_pred = df[f"{field}_llm_norm"].fillna("missing").astype(str).tolist()
    
    acc = accuracy_score(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='weighted', zero_division=0)
    
    return {"Accuracy": acc, "F1": f1, "Precision": precision, "Recall": recall}

def main():
    if not GOLD_STANDARD_CSV.exists():
        print("Gold standard missing.")
        return

    gold_df = pd.read_csv(GOLD_STANDARD_CSV)
    gold_df['patient_id'] = gold_df['patient_id'].astype(str).str.strip()
    
    log_files = list(LOGS_DIR.glob("*.csv"))
    if not log_files:
        print("No log files found.")
        return

    all_metrics = []
    error_audit = []

    for log_file in log_files:
        model_name = log_file.stem.replace("study_dev_", "").replace("study_test_", "").replace("model_", "")
        split_name = "test" if "test" in log_file.name else "dev"
        print(f"Processing {model_name} ({split_name})...")
        
        try:
            llm_df = pd.read_csv(log_file)
        except: continue
            
        llm_df = llm_df[llm_df['status'] == 'success']
        if len(llm_df) == 0: continue
            
        # Parse and Merge
        json_data = llm_df.apply(lambda r: json.loads(r['parsed_json']) if r['status']=='success' else {}, axis=1)
        json_df = pd.json_normalize(json_data)
        llm_df = pd.concat([llm_df.reset_index(drop=True), json_df.reset_index(drop=True)], axis=1)
        llm_df['patient_id'] = llm_df['patient_id'].astype(str).str.strip()
        
        # Merge with Gold (Including pathologic_T from updated extraction)
        merged = pd.merge(llm_df, gold_df, on='patient_id', suffixes=('_llm', '_gold'))
        
        # Normalize
        for field, config in FIELDS_CONFIG.items():
            norm_func = config['norm']
            col_llm = f"{field}_llm" if f"{field}_llm" in merged.columns else field
            col_gold = f"{field}_gold" if f"{field}_gold" in merged.columns else field
            
            merged[f"{field}_llm_norm"] = merged[col_llm].apply(norm_func)
            merged[f"{field}_gold_norm"] = merged[col_gold].apply(norm_func)
            
            # Calc Metrics
            metrics = calculate_metrics(merged, field, config)
            metrics.update({'Model': model_name, 'Split': split_name, 'Field': field})
            all_metrics.append(metrics)

        # --- FORENSIC AUDIT ---
        # Analyze ETE
        merged['ete_error_type'] = merged.apply(ExplainableErrorAnalyzer.classify_ete_error, axis=1)
        
        # Analyze Site
        merged['site_error_type'] = merged.apply(ExplainableErrorAnalyzer.classify_site_error, axis=1)
        
        # Save Audit File
        audit_cols = ['patient_id', 'pathologic_T', 'tumor_size_gold', 
                      'extrathyroidal_extension_gold_norm', 'extrathyroidal_extension_llm_norm', 'ete_error_type',
                      'tumor_site_gold_norm', 'tumor_site_llm_norm', 'site_error_type']
        
        audit_df = merged[audit_cols].copy()
        audit_out = OUTPUT_DIR / f"error_audit_{split_name}_{model_name}.csv"
        audit_df.to_csv(audit_out, index=False)
        print(f"  Saved forensic audit to {audit_out}")

    # Summary
    if all_metrics:
        pd.DataFrame(all_metrics).to_csv(OUTPUT_DIR / "summary_metrics.csv", index=False)
        print("Summary metrics saved.")

if __name__ == "__main__":
    main()