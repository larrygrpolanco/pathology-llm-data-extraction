# Pathology LLM Data Extraction - Thyroid Cancer Pilot

This project evaluates the accuracy and generalizability of Large Language Models (LLMs) in automating the extraction of structured data from thyroid cancer pathology reports. By benchmarking against the TCGA-THCA (The Cancer Genome Atlas Thyroid Carcinoma) dataset, we assess how well these models can replace manual abstraction in a clinical research workflow.

## 📁 Project Structure

```
pathology-llm-data-extraction/
├── data/
│   ├── raw/                  # Original GDC folders (XML + PDF)
│   ├── parsed_reports/       # Markdown files (LlamaParse output)
│   └── gold_standard/        # thyroid_gold_standard.csv (XML Ground Truth)
├── src/
│   ├── extract_pathology_data.py # Creates gold standard from XML
│   ├── preprocess_pdfs.py       # PDF -> MD (LlamaParse)
│   ├── run_inference.py         # Runs LLM extraction (OpenRouter/Groq)
│   └── analyze_models.py        # Accuracy/F1 comparison against XML
├── output/
│   ├── inference_logs/       # model_outputs.csv (Raw LLM JSON)
│   └── analysis/             # Metrics, Summary, and Review CSVs
├── requirements.txt
├── .env                      # API Keys (OpenRouter, Groq, Llama Cloud)
└── README.md
```

## 🚀 Getting Started

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the root directory:

```env
# Essential for Inference
OPENROUTER_API_KEY=your_key
GROQ_API_KEY=your_key

# Essential for PDF Parsing
LLAMA_CLOUD_API_KEY=your_key
```

## 🛠 Workflow

Follow these steps in order to replicate the study or test new models.

### Step 1: Generate Ground Truth (XML -> CSV)

Extracts the clinician-validated data from TCGA clinical XMLs to use as the "Gold Standard".

```bash
python3 src/extract_pathology_data.py
```

### Step 2: Preprocess Reports (PDF -> Markdown)

Converts raw pathology PDF scans into clean Markdown using LlamaParse. This ensures the LLM sees the text without layout artifacts.

```bash
python3 src/preprocess_pdfs.py
```

### Step 3: Run LLM Extraction (Inference)

Processes the reports through various LLMs (GPT-4o, Llama 3.3, etc.). The prompt enforces a structured JSON output for 9 key clinical data points.

```bash
python3 src/run_inference.py
```

### Step 4: Evaluate Performance (Analysis)

Compares LLM extractions against the ground truth. Generates F1-scores, precision, and "Review CSVs" for manual auditing of mismatches.

```bash
python3 src/analyze_models.py
```

## 📊 Data Points Extracted

The pipeline targets 9 high-impact prognostic factors:

- Histologic Type & Variant
- Tumor Site (Laterality)
- Tumor Size (Max cm)
- Tumor Focality
- Extrathyroidal Extension (ETE)
- Margin Status (R0/R1/R2)
- Nodes Examined & Positive Count

## 🧪 Models Supported

The project uses **Groq** and **OpenRouter** to test a wide range of models, including:


