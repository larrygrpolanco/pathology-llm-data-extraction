# Confidence Calibration Experiment

Testing GPT-OSS-120B's ability to self-assess extraction accuracy using per-field prompting with High/Medium/Low confidence scoring.

## Overview

This experiment evaluates whether LLMs can accurately identify which pathology extractions need human review. Unlike the original study which extracted all fields in one prompt, this uses **sequential per-field prompting** (5 separate API calls per patient) with confidence calibration.

## Key Research Questions

1. **Does per-field prompting improve accuracy?** (Compare to original GPT-OSS-120B results)
2. **Is the model well-calibrated?** (Do High/Medium/Low confidence levels correlate with actual accuracy?)
3. **What's the optimal review workflow?** (Review only Low confidence? Low+Medium?)
4. **Which fields are hardest to self-assess?**

## Experiment Design

### Confidence Scale
- **High**: Information clearly stated and unambiguous
- **Medium**: Information present but requires interpretation or has minor ambiguity
- **Low**: Information unclear, conflicting, missing, or requires significant inference

### Per-Field Processing
Each patient requires 5 sequential API calls:
1. histologic_variant
2. tumor_site
3. extrathyroidal_extension
4. margins
5. tumor_size

Each call returns: `value`, `confidence`, `reasoning`

### Data Flow
```
Patient Report
    ↓
5 Sequential API Calls (one per field)
    ↓
Individual Field Logs (JSON)
    ↓
Aggregated Results (CSV)
    ↓
Analysis + Metrics
```

## Files

### Core Scripts
- **`field_prompts.py`** - Individual prompts for each field (easy to edit confidence instructions)
- **`run_confidence_study.py`** - Main inference script with retry logic
- **`analyze_confidence_results.py`** - Comprehensive analysis (baseline + confidence metrics)

### Output Structure
```
confidence-testing/output/
├── logs/                          # Individual field results (JSON)
│   ├── test_TCGA-xxx_histologic_variant.json
│   ├── test_TCGA-xxx_tumor_site.json
│   └── ...
├── results/                       # Aggregated results
│   └── confidence_study_test_aggregated.csv
└── analysis/                      # Analysis outputs
    └── test/                      # Split-specific analysis
        ├── confidence_summary.csv
        ├── field_comparison.csv
        ├── workflow_efficiency.csv
        ├── master_summary.csv
        └── [field]_detailed.csv   # Per-field detailed breakdowns
```

## Running the Experiment

### Prerequisites
- Groq API key in `.env` file (shared with main project)
- Test data split prepared (`data/test_split.csv`)
- Parsed reports available (`data/parsed_reports/*.md`)

### Step 1: Run the Study

```bash
cd confidence-testing

# Run on test split (default)
python run_confidence_study.py

# Run on final split
python run_confidence_study.py --split final

# Process single patient (for testing)
python run_confidence_study.py --patient TCGA-DE-A69J
```

**Expected Runtime:** ~10 minutes for 200 patients (1000 API calls)

**Progress Tracking:**
- Script saves progress after each patient
- Can be stopped and resumed anytime
- Individual field logs prevent data loss

### Step 2: Analyze Results

```bash
# Analyze test split results
python analyze_confidence_results.py

# Analyze final split results
python analyze_confidence_results.py --split final
```

## Metrics Generated

### 1. Baseline Performance (Same as Original Study)
- Per-field accuracy, precision, recall, F1
- Overall performance metrics
- Direct comparison to original GPT-OSS-120B results

### 2. Confidence Calibration

**Overall Summary:**
```
Confidence    Count    Correct    Wrong    Accuracy    % of Total
High          435      420        15       96.7%       43.5%
Medium        220      168        52       76.4%       22.0%
Low           145      65         80       44.8%       15.0%
```

**Per-Field Breakdown:**
- Accuracy at each confidence level
- Distribution of confidence levels
- Calibration quality by field

### 3. Workflow Efficiency

**Review Strategies Compared:**

| Strategy | Cases to Review | Errors Caught | Time Saved |
|----------|----------------|---------------|------------|
| Review ALL | 100% | 100% | 0% |
| Review LOW only | ~15% | ~47% | ~85% |
| Review LOW+MEDIUM | ~40% | ~87% | ~60% |

### 4. Error Analysis

Saved for each field:
- `*_detailed.csv` - All extractions with confidence and reasoning
- `*_mismatches_low_conf.csv` - Errors correctly flagged as uncertain
- `*_mismatches_high_conf.csv` - Overconfident errors (model was wrong but didn't know it)

## Customization

### Editing Confidence Instructions

Modify `field_prompts.py` at the top:

```python
CONFIDENCE_INSTRUCTIONS = """
CONFIDENCE CALIBRATION:
Return your confidence level as "High", "Medium", or "Low" based on:
- High: The information is clearly stated and unambiguous
- Medium: The information is present but requires some interpretation
- Low: The information is unclear, conflicting, or missing

Provide concise reasoning (1-2 sentences) explaining your confidence choice.
"""
```

### Adjusting Retry Logic

In `run_confidence_study.py`:
```python
MAX_RETRIES = 3          # Increase for more retries
RETRY_DELAY = 1.0        # Seconds between retries
API_DELAY = 0.3         # Seconds between API calls
```

## Key Outputs for Comparison

### File: `analysis/{split}/master_summary.csv`

Contains all metrics needed to compare with original study:
- Baseline accuracy/F1
- Confidence distribution
- Accuracy at each confidence level
- Workflow efficiency metrics

### Example Comparison Table

| Field | Original F1 | Per-Field F1 | High Conf Acc | Med Conf Acc | Low Conf Acc |
|-------|-------------|--------------|---------------|--------------|--------------|
| histologic_variant | 0.94 | 0.96 | 98.2% | 72.1% | 38.5% |
| tumor_site | 0.86 | 0.89 | 92.1% | 68.4% | 42.3% |
| ... | ... | ... | ... | ... | ... |

## Troubleshooting

### API Rate Limits
If you hit rate limits:
- Increase `API_DELAY` in `run_confidence_study.py`
- Script has built-in retry logic for transient errors

### Missing Gold Standard
Ensure `data/gold_standard/thyroid_gold_standard.csv` exists (from main project)

### Partial Runs
Script automatically resumes from where it left off by checking completed patients in aggregated results.

## Notes

- **Model**: Fixed to GPT-OSS-120B (`openai/gpt-oss-120b`)
- **Split**: Defaults to "test", change to "final" for full experiment
- **Cost**: 1000 API calls (200 patients × 5 fields) at current pricing
- **Isolation**: All outputs confined to `confidence-testing/output/` to avoid interfering with main study
