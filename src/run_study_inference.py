import os
import csv
import json
import time
import argparse
import requests
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional
from dotenv import load_dotenv
from groq import Groq

# -----------------------------------------------------------------------------
# USER SETTINGS (Edit these to quickly change script behavior)
# -----------------------------------------------------------------------------

# default split: "dev" or "test"
DEFAULT_SPLIT = "dev"

# Define the models you want to run. Comment/Uncomment as needed.
# Note: "alias" is used for filenames, "id" is the API model name.
MODELS = {
    # Groq Models (Fast & Cheap)
    # "llama-3.1-8b": {"id": "llama-3.1-8b-instant", "provider": "groq"},
    # "llama-3.3-70b": {"id": "llama-3.3-70b-versatile", "provider": "groq"},
    "gpt-oss-120b": {"id": "openai/gpt-oss-120b", "provider": "groq"},
    
    # OpenRouter Models (Broader selection)
    # "mistral-large": {"id": "mistralai/mistral-large-2411", "provider": "openrouter"},
    # "kimi-k2.5": {"id": "moonshotai/kimi-k2.5", "provider": "openrouter"},
}

# -----------------------------------------------------------------------------
# SYSTEM CONFIGURATION
# -----------------------------------------------------------------------------

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PARSED_DIR = DATA_DIR / "parsed_reports"
OUTPUT_DIR = BASE_DIR / "output" / "study_logs"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq Client
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Refined System Prompt

SYSTEM_PROMPT = """Role: Specialized Pathologist Assistant for Thyroid Cancer Data Extraction.

Context: Extract structured data from surgical pathology reports.

Objective: Return a valid JSON object.

--- EXTRACTION RULES ---

1. histologic_type:
   - "Papillary Thyroid Carcinoma" (includes Microcarcinoma) or "Other".

2. histologic_variant:
   - Priority: 1. Explicit mention (e.g., "Follicular Variant", "Tall Cell"). 2. "Papillary Carcinoma" alone -> "Classical".
   - Ignore "follicular architecture" if the diagnosis is simply PTC.

3. tumor_size:
   - Extract the size of the DOMINANT (largest) tumor nodule in cm.
   - CHECK HEADERS: Look for sizes in parentheses at the start of diagnosis lines (e.g., "(3.5 CM) PAPILLARY CARCINOMA"). Use this if it is the largest.

4. extrathyroidal_extension (ETE):
   - "Gross": Explicit use of "Gross", "Grossly", "Macroscopic". 
   - CRITICAL RULE: If the text says "Grossly invades skeletal muscle", output "Gross". Do NOT default to Microscopic just because muscle is mentioned.
   - "Microscopic": Invasion into soft tissue/muscle WITHOUT the word "Gross".
   - "No ETE": "Confined to thyroid", "capsular invasion only".

5. margins:
   - "R0" (Negative/Clear), "R1" (Microscopic Positive), "R2" (Gross Positive).

6. tumor_site:
   - Options: "Right lobe", "Left lobe", "Isthmus", "Bilateral".
   - Rule: Default to the location of the DOMINANT nodule. 
   - EXCEPTION: If the Final Diagnosis Heading explicitly states "Bilateral Papillary Carcinoma", output "Bilateral" even if one side is larger.

7. focality:
   - "Unifocal" (Single focus) vs "Multifocal" (Multiple foci/Bilateral).

8. lymph_nodes_resected:
   - "yes" if nodes/tissue received, else "no".

9. lymph_nodes_positive_count:
   - Count of positive nodes. 0 if none.

--- FORMATTING ---
- Use null for missing values.
"""


def get_output_path(model_alias: str, split_name: str) -> Path:
    """Returns the path to the log file for a specific model and split."""
    sanitized_name = model_alias.replace("/", "_").replace(":", "_")
    return OUTPUT_DIR / f"study_{split_name}_{sanitized_name}.csv"

def get_completed_runs(output_csv: Path) -> Set[str]:
    """Returns a set of patient_ids that have already been processed in the target CSV."""
    if not output_csv.exists():
        return set()
    
    completed_ids = set()
    try:
        with open(output_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('patient_id'):
                    completed_ids.add(row['patient_id'].strip())
    except Exception:
        pass
    return completed_ids

def call_openrouter(model_id: str, prompt: str) -> Tuple[str, str]:
    """Makes an API call via OpenRouter."""
    if not OPENROUTER_API_KEY:
        return "OpenRouter API Key Missing", "error"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/pathology-llm-extraction",
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
        if 'error' in result:
            return f"API Error: {json.dumps(result['error'])}", "error"
        content = result['choices'][0]['message']['content']
        return content, "success"
    except Exception as e:
        return str(e), "error"

def call_groq(model_id: str, prompt: str) -> Tuple[str, str]:
    """Makes an API call via Groq."""
    if not groq_client:
        return "Groq client not initialized", "error"
        
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            model=model_id,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        content = chat_completion.choices[0].message.content
        return content, "success"
    except Exception as e:
        return str(e), "error"

def run_inference_for_model(
    model_alias: str, 
    model_config: Dict[str, str], 
    split: str, 
    patients: List[Dict[str, str]]
):
    """Processes all patients for a single model configuration."""
    model_id = model_config["id"]
    provider = model_config["provider"]
    output_csv = get_output_path(model_alias, split)
    
    # Initialize CSV if it doesn't exist
    if not output_csv.exists():
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['patient_id', 'model_alias', 'model_id', 'timestamp', 'status', 'raw_response', 'parsed_json'])
    
    completed_ids = get_completed_runs(output_csv)
    remaining_patients = [p for p in patients if p['patient_id'] not in completed_ids]
    
    print(f"\n>>> Model: {model_alias} ({provider}) | Progress: {len(completed_ids)}/{len(patients)}")
    if not remaining_patients:
        print("    All cases already processed.")
        return

    for i, row in enumerate(remaining_patients):
        patient_id = row['patient_id']
        md_path = PARSED_DIR / f"{patient_id}.md"
        
        if not md_path.exists():
            print(f"    [!] Skipping {patient_id}: File not found at {md_path}")
            continue
            
        with open(md_path, 'r', encoding='utf-8') as f:
            report_text = f.read()
        
        print(f"    [{i+1}/{len(remaining_patients)}] {patient_id}...", end=" ", flush=True)
        
        # API Call
        if provider == "groq":
            raw_response, status = call_groq(model_id, report_text)
        else:
            raw_response, status = call_openrouter(model_id, report_text)
        
        # Parse Validation
        parsed_json = ""
        if status == "success":
            try:
                # Basic cleaning for models that ignore "json_object" instruction
                clean_resp = raw_response.replace("```json", "").replace("```", "").strip()
                json_obj = json.loads(clean_resp)
                parsed_json = json.dumps(json_obj)
                print("OK")
            except Exception:
                parsed_json = "JSON_ERROR"
                print("JSON_PARSE_FAILED")
        else:
            print(f"FAILED ({status})")
        
        # Log Result
        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
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
        
        # Rate limiting
        time.sleep(0.5)

def main():
    parser = argparse.ArgumentParser(description="Run pathology extraction inference.")
    parser.add_argument("--split", type=str, default=DEFAULT_SPLIT, help=f"Which split to run on (default: {DEFAULT_SPLIT})")
    parser.add_argument("--models", nargs="+", help="Explicit list of model aliases to run. If omitted, runs all active models in the registry.")
    
    args = parser.parse_args()
    
    # Determine which models to run
    active_models = {}
    if args.models:
        for alias in args.models:
            if alias in MODELS:
                active_models[alias] = MODELS[alias]
            else:
                print(f"Warning: Model alias '{alias}' not found in registry.")
    else:
        active_models = MODELS

    if not active_models:
        print("No models selected to run. Check the registry or your CLI arguments.")
        return

    # Load Split Data
    split_file = DATA_DIR / f"{args.split}_split.csv"
    if not split_file.exists():
        print(f"Split file not found: {split_file}")
        return
        
    patients = []
    with open(split_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        patients = [row for row in reader] # Stratification already filters for 'OK' flags
        
    print(f"Loaded {len(patients)} cases from {args.split} split.")
    print(f"Running for models: {', '.join(active_models.keys())}")

    for alias, config in active_models.items():
        run_inference_for_model(alias, config, args.split, patients)

if __name__ == "__main__":
    main()
