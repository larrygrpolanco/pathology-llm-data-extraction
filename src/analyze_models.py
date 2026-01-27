import csv
import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import precision_recall_fscore_support

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
GOLD_STANDARD_CSV = BASE_DIR / "data" / "gold_standard" / "thyroid_gold_standard.csv"
MODEL_OUTPUTS_CSV = BASE_DIR / "output" / "inference_logs" / "model_outputs.csv"
ANALYSIS_OUTPUT_DIR = BASE_DIR / "output" / "analysis"

FIELDS_TO_COMPARE = [
    "histologic_type",
    "pathologic_T",
    "pathologic_N",
    "pathologic_M",
    "extrathyroidal_extension",
    "focality",
    "lymph_nodes_examined_count",
    "lymph_nodes_positive_count"
]

def normalize_value(val):
    """Normalize values for comparison (handles strings and numbers)."""
    if val is None or pd.isna(val):
        return "not available"
    
    # Convert to string and lowercase
    s = str(val).lower().strip()
    
    # Basic cleanup
    s = s.replace("stage ", "").replace("thyroid ", "")
    
    if s in ["null", "none", "nan", "not available", "not applicable", "unknown"]:
        return "not available"
        
    # Remove 'p' prefix for TNM (e.g. pt1b -> t1b, pn1 -> n1)
    if s.startswith("p") and len(s) > 1 and s[1] in ["t", "n", "m"]:
        s = s[1:]
        
    # Attempt numeric normalization for counts
    try:
        if s.replace('.', '', 1).isdigit():
            return str(int(float(s)))
    except:
        pass
        
    return s

def is_match(pred, true):
    """Determine if prediction matches gold standard."""
    p = normalize_value(pred)
    t = normalize_value(true)
    
    if p == t:
        return True
    
    if t == "not available":
        # If ground truth is missing, we only match if pred is also missing
        return p == "not available"
    
    if p == "not available":
        return False
        
    # Fuzzy match for strings (only for non-numeric looking values)
    if not (p.isdigit() or t.isdigit()):
        if p in t or t in p:
            return True
            
    return False

def calculate_metrics(y_true, y_pred):
    """Calculate Precision, Recall, and F1."""
    # We treat any non-match as incorrect.
    # To use sklearn metrics, we need to map values to integers or handle them as classes.
    # However, since we want F1/Precision/Recall per model per field, and our 'classes' are arbitrary,
    # we can simplify: 
    # Accuracy = Matches / Total
    # For Precision/Recall/F1 in a multi-class setting where we care about "correctness" overall:
    
    matches = [is_match(p, t) for p, t in zip(y_pred, y_true)]
    accuracy = sum(matches) / len(matches) if matches else 0
    
    # For a more nuanced F1, we could treat each unique value as a class, 
    # but the user asked for F1 per data point (field). 
    # Usually, F1 per field in this context means treating the extraction as a classification task.
    
    # Let's provide a simple report based on matches for now, 
    # but also use sklearn for macro-averaging if possible.
    try:
        # Normalize all for sklearn
        y_true_norm = [normalize_value(v) for v in y_true]
        y_pred_norm = [normalize_value(v) for v in y_pred]
        
        # We use 'weighted' to account for class imbalance in the specific values
        p, r, f1, _ = precision_recall_fscore_support(y_true_norm, y_pred_norm, average='weighted', zero_division=0)
        return accuracy, p, r, f1
    except:
        return accuracy, 0, 0, 0

def main():
    if not MODEL_OUTPUTS_CSV.exists():
        print("No model outputs found.")
        return

    ANALYSIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load Data
    gold_df = pd.read_csv(GOLD_STANDARD_CSV)
    model_df = pd.read_csv(MODEL_OUTPUTS_CSV)
    
    # Filter for success
    model_df = model_df[model_df['status'] == 'success']
    
    # Parse JSON in model outputs
    def parse_json(row):
        try:
            return json.loads(row['parsed_json'])
        except:
            return {}
            
    model_df['json_data'] = model_df.apply(parse_json, axis=1)
    
    # Expand JSON columns
    json_df = pd.json_normalize(model_df['json_data'])
    # Ensure all FIELDS_TO_COMPARE exist in json_df
    for field in FIELDS_TO_COMPARE:
        if field not in json_df.columns:
            json_df[field] = "Not Available"
            
    model_df = pd.concat([model_df.reset_index(drop=True), json_df.reset_index(drop=True)], axis=1)
    
    # Merge with gold standard
    merged_df = pd.merge(model_df, gold_df, on='patient_id', suffixes=('_llm', '_gold'))
    
    print(f"Loaded {len(merged_df)} predictions matching gold standard.")
    
    models = merged_df['model_name'].unique()
    summary_data = []

    for model in models:
        print(f"\n--- Model: {model} ---")
        subset = merged_df[merged_df['model_name'] == model].copy()
        
        # Prepare comparison CSV for this model
        comparison_rows = []
        
        model_metrics = {}

        for field in FIELDS_TO_COMPARE:
            llm_col = f"{field}_llm"
            gold_col = f"{field}_gold"
            
            # Check if columns exist (might be renamed during merge if names were same)
            if llm_col not in subset.columns: llm_col = field
            if gold_col not in subset.columns: gold_col = field
            
            y_gold = subset[gold_col].tolist()
            y_llm = subset[llm_col].tolist()
            
            acc, p, r, f1 = calculate_metrics(y_gold, y_llm)
            
            print(f"{field:25} | Acc: {acc:.1%} | P: {p:.2f} | R: {r:.2f} | F1: {f1:.2f}")
            
            model_metrics[field] = {"acc": acc, "p": p, "r": r, "f1": f1}
            summary_data.append({
                "model": model,
                "field": field,
                "accuracy": acc,
                "precision": p,
                "recall": r,
                "f1_score": f1
            })

        # Generate detailed comparison CSV for manual review
        review_cols = ['patient_id']
        for field in FIELDS_TO_COMPARE:
            subset[f"{field}_match"] = subset.apply(lambda row: "MATCH" if is_match(row[f"{field}_llm"], row[f"{field}_gold"]) else "MISMATCH", axis=1)
            review_cols.extend([f"{field}_llm", f"{field}_gold", f"{field}_match"])
        
        model_filename = ANALYSIS_OUTPUT_DIR / f"review_{model.replace('/', '_')}.csv"
        subset[review_cols].to_csv(model_filename, index=False)
        print(f"Generated review CSV: {model_filename}")

    # Save summary metrics
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(ANALYSIS_OUTPUT_DIR / "summary_metrics.csv", index=False)
    print(f"\nSummary metrics saved to {ANALYSIS_OUTPUT_DIR / 'summary_metrics.csv'}")

if __name__ == "__main__":
    main()


            
            # Detailed report for one field if interesting
            # print(classification_report(y_true, y_pred))

if __name__ == "__main__":
    main()
