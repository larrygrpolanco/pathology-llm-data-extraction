import os
import csv
import json
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PARSED_DIR = DATA_DIR / "parsed_reports"
GOLD_STANDARD_CSV = DATA_DIR / "gold_standard" / "thyroid_gold_standard.csv"
OUTPUT_DIR = BASE_DIR / "output" / "inference_logs"
OUTPUT_CSV = OUTPUT_DIR / "model_outputs.csv"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model definition (Scale: Large, Medium, Small)
MODELS = {
    # Large
    "mistral-large": "mistralai/mistral-large",
    "llama-3.1-405b": "meta-llama/llama-3.1-405b-instruct",
    # Medium
    "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",
    "mixtral-8x7b": "mistralai/mixtral-8x7b-instruct",
    # Small
    "llama-3.1-8b": "meta-llama/llama-3.1-8b-instruct",
    "mistral-7b": "mistralai/mistral-7b-instruct",
}

# Prompt
SYSTEM_PROMPT = """You are an expert pathologist assistant. Your task is to extract structured data from the provided Thyroid Pathology Report.

Extract the following fields into a standard JSON format:
1. histologic_type (Text, e.g., "Papillary carcinoma")
2. pathologic_T (Text, e.g., "pT1a")
3. pathologic_N (Text, e.g., "pN0", "pNx")
4. pathologic_M (Text, e.g., "pM0", "Not Available")
5. extrathyroidal_extension (Text, present/absent/minimal/etc.)
6. focality (Text, e.g., "Unifocal", "Multifocal")
7. lymph_nodes_examined_count (Integer or null if not stating a count)
8. lymph_nodes_positive_count (Integer or null if not stating a count)

Return ONLY valid JSON. Do not include markdown formatting (```json ... ```).
If a field is not available or not applicable, use null or "Not Available".
"""

def get_completed_runs():
    """Returns a set of (patient_id, model_name) that have already been processed."""
    if not OUTPUT_CSV.exists():
        return set()
    
    try:
        df = pd.read_csv(OUTPUT_CSV)
        # Create a set of tuples
        return set(zip(df['patient_id'], df['model_name']))
    except Exception:
        return set()

def call_openrouter(model_id, prompt, model_alias):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/pathology-llm-extraction", # Required by OpenRouter
    }
    
    data = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        return content, "success"
    except Exception as e:
        return str(e), "error"

def main():
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not found in .env")
        return

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize CSV if needed
    if not OUTPUT_CSV.exists():
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['patient_id', 'model_name', 'model_id', 'timestamp', 'status', 'raw_response', 'parsed_json'])

    completed_runs = get_completed_runs()
    
    # Load Gold Standard
    if not GOLD_STANDARD_CSV.exists():
        print("Gold standard CSV not found.")
        return
        
    patients = []
    with open(GOLD_STANDARD_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        patients = list(reader)

    print(f"Starting inference on {len(patients)} cases across {len(MODELS)} models...")

    for i, row in enumerate(patients):
        patient_id = row['patient_id']
        
        # Check for parsed markdown
        md_path = PARSED_DIR / f"{patient_id}.md"
        if not md_path.exists():
            # If parsing is still running or failed, skip
            # print(f"Skipping {patient_id}: parsed MD not found (yet).")
            continue
            
        with open(md_path, 'r', encoding='utf-8') as f:
            report_text = f.read()

        for model_alias, model_id in MODELS.items():
            if (patient_id, model_alias) in completed_runs:
                continue
                
            print(f"[{i+1}/{len(patients)}] Processing {patient_id} on {model_alias}...")
            
            # API Call
            raw_response, status = call_openrouter(model_id, report_text, model_alias)
            
            # Try parsing JSON to ensure it's valid (metrics script will do deep check)
            parsed_json = ""
            if status == "success":
                try:
                    # Clean markdown code blocks if present
                    clean_resp = raw_response.replace("```json", "").replace("```", "").strip()
                    json_obj = json.loads(clean_resp)
                    parsed_json = json.dumps(json_obj)
                except json.JSONDecodeError:
                    parsed_json = "JSON_DECODE_ERROR"
            
            # Allow saving invalid JSON to debug later
            
            # Append to CSV
            with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    patient_id,
                    model_alias,
                    model_id,
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    status,
                    raw_response,
                    parsed_json
                ])
                
            # Rate limiting / Politeness
            time.sleep(1)

    print("Inference run complete (or caught up).")

if __name__ == "__main__":
    main()
