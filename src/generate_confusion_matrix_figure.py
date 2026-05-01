"""
Generate averaged confusion matrix figure for tumor_site across all 7 models.
Each model's confusion matrix is row-normalized, then averaged.
Output: figures/tumor_site_confusion_matrix.png
"""

import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from sklearn.metrics import confusion_matrix

try:
    import post_processing_utils as pp
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import post_processing_utils as pp

BASE_DIR = Path(__file__).resolve().parent.parent
GOLD_CSV = BASE_DIR / "data" / "gold_standard" / "thyroid_gold_standard.csv"
FINAL_SPLIT = BASE_DIR / "data" / "final_split.csv"
LOGS_DIR = BASE_DIR / "output" / "study_logs"
OUT_DIR = BASE_DIR / "figures"
OUT_DIR.mkdir(exist_ok=True)

MODELS = [
    "kimi-k2",
    "llama-3.3-70b",
    "llama-3.1-8b",
    "qwen3-32b",
    "gpt-oss-120b",
    "gpt-oss-20b",
    "mistral-large-2512",
]

# Display order for classes (most common → least common)
CLASSES = ["Right lobe", "Left lobe", "Bilateral", "Isthmus"]
CLASS_LABELS = ["Right\nLobe", "Left\nLobe", "Bilateral", "Isthmus"]


def load_predictions(model_name, final_ids, gold_df):
    log_path = LOGS_DIR / f"study_final_{model_name}.csv"
    df = pd.read_csv(log_path)
    df = df[df["status"] == "success"]
    parsed = df["parsed_json"].apply(lambda x: json.loads(x))
    df2 = pd.json_normalize(parsed)
    df = pd.concat(
        [df[["patient_id"]].reset_index(drop=True), df2.reset_index(drop=True)], axis=1
    )
    df = df[df["patient_id"].isin(final_ids)]
    merged = df.merge(gold_df[["patient_id", "tumor_site"]], on="patient_id")
    merged["pred"] = merged["tumor_site_x"].apply(
        lambda x: pp.normalize_site(x) if pd.notnull(x) else None
    )
    merged["gold"] = merged["tumor_site_y"].apply(pp.normalize_site)
    merged = merged[merged["pred"].notnull() & merged["gold"].notnull()]
    return merged["gold"].tolist(), merged["pred"].tolist()


def compute_normalized_cm(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred, labels=CLASSES)
    row_sums = cm.sum(axis=1, keepdims=True)
    return np.where(row_sums > 0, cm / row_sums, 0)


def main():
    gold_df = pd.read_csv(GOLD_CSV)
    final_ids = set(pd.read_csv(FINAL_SPLIT)["patient_id"].astype(str))

    # Gold class counts for y-axis labels
    gold_sub = gold_df[gold_df["patient_id"].isin(final_ids)].copy()
    gold_sub["site_norm"] = gold_sub["tumor_site"].apply(pp.normalize_site)
    class_counts = gold_sub["site_norm"].value_counts().to_dict()

    all_cms = []
    for model in MODELS:
        y_true, y_pred = load_predictions(model, final_ids, gold_df)
        cm_norm = compute_normalized_cm(y_true, y_pred)
        all_cms.append(cm_norm)

    avg_cm = np.mean(all_cms, axis=0)

    # --- Figure ---
    fig, ax = plt.subplots(figsize=(4.8, 4.8))
    fig.patch.set_facecolor("white")

    ax.imshow(avg_cm, interpolation="nearest", cmap="Blues", vmin=0, vmax=1)

    # Cell annotations
    thresh = 0.5
    for i in range(len(CLASSES)):
        for j in range(len(CLASSES)):
            val = avg_cm[i, j]
            color = "white" if val > thresh else "#1a1a1a"
            weight = "bold" if i == j else "normal"
            ax.text(
                j, i, f"{val:.2f}",
                ha="center", va="center",
                fontsize=11, color=color, fontweight=weight,
            )

    # Axis labels
    y_labels = [
        f"{CLASS_LABELS[i]}\n(n={class_counts.get(CLASSES[i], 0)})"
        for i in range(len(CLASSES))
    ]
    ax.set_xticks(range(len(CLASSES)))
    ax.set_yticks(range(len(CLASSES)))
    ax.set_xticklabels(CLASS_LABELS, fontsize=10)
    ax.set_yticklabels(y_labels, fontsize=9.5)

    ax.set_xlabel("Model Prediction", fontsize=11, labelpad=8)
    ax.set_ylabel("Reference Label", fontsize=11, labelpad=8)
    # ax.set_title("Tumor Site: LLM vs. Reference Label\n(avg. across 7 models, N=200)", fontsize=11, pad=10)

    # Light grid lines between cells
    for i in range(len(CLASSES) + 1):
        ax.axhline(i - 0.5, color="white", linewidth=1.2)
        ax.axvline(i - 0.5, color="white", linewidth=1.2)

    plt.tight_layout()
    out_path = OUT_DIR / "tumor_site_confusion_matrix.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"Saved: {out_path}")
    plt.close()


if __name__ == "__main__":
    main()
