import os
import csv
import json
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Clients
groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# Model definition (Alias: {id, provider})
MODELS = {
    # Groq Models
    # "llama-3.1-8b-instant": {"id": "llama-3.1-8b-instant", "provider": "groq"},
    # "llama-3.3-70b-versatile": {"id": "llama-3.3-70b-versatile", "provider": "groq"},
    # "gpt-oss-120b": {"id": "openai/gpt-oss-120b", "provider": "groq"},
    # "gpt-oss-20b": {"id": "openai/gpt-oss-20b", "provider": "groq"},
    # "kimi-k2-instruct": {"id": "moonshotai/kimi-k2-instruct-0905", "provider": "groq"},
    # "qwen3-32b": {"id": "qwen/qwen3-32b", "provider": "groq"},
    
    # OpenRouter Models
    # "mistral-large": {"id": "mistralai/mistral-large", "provider": "openrouter"},
    # "llama-3.1-405b": {"id": "meta-llama/llama-3.1-405b-instruct", "provider": "openrouter"},
    "deepseek-v3.2": {"id": "deepseek/deepseek-v3.2", "provider": "openrouter"},
    # "claude-3.7-sonnet": {"id": "anthropic/claude-3.7-sonnet", "provider": "openrouter"},

}

# Prompt

SYSTEM_PROMPT = """You are an expert pathologist assistant. Your task is to extract structured data from the provided Thyroid Pathology Report.

Extract the following fields into a standard JSON format:
1. histologic_type (Use "Papillary Thyroid Carcinoma" or "Other")
2. histologic_variant (Extracted variant. MUST be one of: "Classical", "Follicular", "Tall Cell", "Columnar Cell", or "Not Available")
   *Note: If "Papillary Thyroid Carcinoma" is indicated without a specific variant, or if "Classical", "Usual", "Conventional", or "FVPTC" (Follicular Variant) is mentioned, use the appropriate label ("Classical" or "Follicular").*
3. tumor_size (Float representing the maximum dimension of the principal tumor in cm, e.g., 2.5. Convert mm to cm if necessary. Use null if not available.)
4. extrathyroidal_extension (Categorize based on report text. Use null if unknown)
   - "No ETE": Literal "none", "not identified", "confined to thyroid", "encapsulated", or "no extension".
   - "Microscopic": Literal "minimal", "microscopic", or "extension to perithyroidal soft tissues" WITHOUT gross involvement.
   - "Gross": Literal "gross", "macroscopic", or involvement of "strap muscles", "trachea", "esophagus", or "vessels".
   *Note: If "extension" is mentioned without a qualifier, default to "Microscopic" unless "gross" is explicitly stated.*
5. margins (Categorize based on final sign-out status. Use null if unknown)
   - "R0": Negative margins, "no residual tumor", or "margins uninvolved". 
   *Note: If margins are described as "narrow" (e.g. <1mm) but signed out as "Negative", use "R0".*
   - "R1": Microscopic involvement of margins.
   - "R2": Gross involvement of margins or gross residual tumor.
6. tumor_site (Text: "Right lobe", "Left lobe", "Isthmus", or "Bilateral" if both lobes involved. Use null if unknown.)
7. focality ("Unifocal" or "Multifocal")
8. lymph_nodes_resected (Use "yes" or "no" to indicate if any lymph nodes were resected/examined.)
9. lymph_nodes_examined_count (Integer. CRITICAL: Sum counts from ALL mentioned specimens/levels, e.g., "Level VI (4 nodes) + Right Neck (10 nodes)" = 14. Use 0 if "no nodes resected", null if unknown.)
10. lymph_nodes_positive_count (Integer. Sum positive counts from ALL specimens/levels. Must be <= examined_count. Use 0 if all nodes are negative.)

Return ONLY valid JSON. If a field is not present in the report, use null.
Do not attempt to assess pathologic staging (T, N, M); focus only on extraction.
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

def call_openrouter(model_id, prompt):
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

def call_groq(model_id, prompt):
    if not groq_client:
        return "Groq client not initialized (check GROQ_API_KEY)", "error"
        
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

def main():
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
        patients = [row for row in reader if row.get('data_quality_flag') == 'OK']

    print(f"Starting inference on {len(patients)} cases across {len(MODELS)} models...")

    for i, row in enumerate(patients):
        patient_id = row['patient_id']
        
        # Check for parsed markdown
        md_path = PARSED_DIR / f"{patient_id}.md"
        if not md_path.exists():
            continue
            
        with open(md_path, 'r', encoding='utf-8') as f:
            report_text = f.read()

        for model_alias, config in MODELS.items():
            if (patient_id, model_alias) in completed_runs:
                continue
                
            print(f"[{i+1}/{len(patients)}] Processing {patient_id} on {model_alias} ({config['provider']})...")
            
            # API Call
            if config['provider'] == 'groq':
                raw_response, status = call_groq(config['id'], report_text)
            else:
                raw_response, status = call_openrouter(config['id'], report_text)
            
            # Try parsing JSON to ensure it's valid
            parsed_json = ""
            if status == "success":
                try:
                    # Clean markdown code blocks if present
                    clean_resp = raw_response.replace("```json", "").replace("```", "").strip()
                    json_obj = json.loads(clean_resp)
                    parsed_json = json.dumps(json_obj)
                except json.JSONDecodeError:
                    parsed_json = "JSON_DECODE_ERROR"
            
            # Append to CSV
            with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    patient_id,
                    model_alias,
                    config['id'],
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    status,
                    raw_response,
                    parsed_json
                ])
                
            # Rate limiting / Politeness (Groq is faster, but let's keep it safe)
            time.sleep(0.5)

    print("Inference run complete (or caught up).")

if __name__ == "__main__":
    main()
