import os
import csv
import json
import time
import argparse
import requests
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
from dotenv import load_dotenv
from groq import Groq

# -----------------------------------------------------------------------------
# USER SETTINGS 
# -----------------------------------------------------------------------------

DEFAULT_SPLIT = "dev"

# Define the models
MODELS = {
    "gpt-oss-120b": {"id": "openai/gpt-oss-120b", "provider": "groq"},
    # "gpt-oss-20b": {"id": "openai/gpt-oss-20b", "provider": "groq"},
    # "llama-3.1-8b": {"id": "llama-3.1-8b-instant", "provider": "groq"},
    # "llama-3.3-70b": {"id": "llama-3.3-70b-versatile", "provider": "groq"},
    # "qwen3-32b": {"id": "qwen/qwen3-32b", "provider": "groq"},
    # "kimi-k2": {"id": "moonshotai/kimi-k2-instruct-0905", "provider": "groq"},
    # "mistral-large-2512": {"id": "mistralai/mistral-large-2512", "provider": "openrouter"}
}

# -----------------------------------------------------------------------------
# SYSTEM CONFIGURATION
# -----------------------------------------------------------------------------

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PARSED_DIR = DATA_DIR / "parsed_reports"
OUTPUT_DIR = BASE_DIR / "output" / "study_logs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# -----------------------------------------------------------------------------
# PROMPT DEFINITION
# -----------------------------------------------------------------------------


PROMPT = """Role: Clinical data abstractor for cancer registry coding.
Task: Extract structured variables from pathology reports following rules below.

--- EXTRACTION RULES ---

1. histologic_variant:
   - Options: "Classical" | "Follicular" | "Tall Cell"
   - RULES:
     A. Extract variant ONLY from the final diagnosis line, NOT from microscopic descriptions.
     B. "Follicular/Tall Cell features" or "architecture" → ignore (these describe cellular patterns, not the variant).
     C. If multiple variants mentioned, use the one in the PRIMARY/DOMINANT tumor only.
     D. DEFAULT: If diagnosis says "Papillary Thyroid Carcinoma" without specifying variant → "Classical".

2. tumor_site (The Bilateral Rule):
   - Options: "Right lobe" | "Left lobe" | "Isthmus" | "Bilateral"
   - Rules:
     A. Identify the location of the DOMINANT nodule (e.g., Right Lobe).
     B. Check for clinically significant carcinoma (>1cm) in the contralateral lobe
     C. If carcinoma is present in BOTH lobes -> Output "Bilateral".
     D. Otherwise, output the site of the dominant nodule.
     E. Only use "Isthmus" if the dominant center is the isthmus.

3. extrathyroidal_extension:
   - Options: "No ETE" | "Microscopic" | "Gross"
   - Rules: 
     A. Check Synoptic table first and trust the *descriptive text* over the TNM stage code (as staging criteria vary by year).
     B. "Not identified", "Absent", "Intrathyroidal", "Confined/limited to thyroid" -> "No ETE"
     C. "Present", "Identified", "Microscopic extension", "Invades fat/soft tissue" -> "Microscopic"
     D. "Gross extension", "Macroscopic", "Invades strap muscles/trachea" -> "Gross"

4. margins:
   - Options: "R0" | "R1" | "R2"
   - Rules: 
     A. "Uninvolved", "Negative", "Clear", or if no involvement is mentioned -> "R0" (even if close). 
     B. "Involved", "Positive", or "Focal involvement" -> "R1".

5. tumor_size (Header Priority):
   - Type: Float (cm).
   - Rules: 
     A. Synoptic Data / Final Diagnosis for the DOMINANT (largest) tumor.
     B. EXCEPTION: If Diagnosis uses the term "Microcarcinoma" AND Gross Description measures 
the same nodule as ≥1.0 cm, use the Gross measurement.
     C. Convert mm to cm.

--- OUTPUT FORMAT ---
Return a JSON object:
{
  "histologic_variant": "Classical | Follicular | Tall Cell",
  "tumor_site": "Right lobe | Left lobe | Isthmus | Bilateral",
  "extrathyroidal_extension": "No ETE | Microscopic | Gross",
  "margins": "R0 | R1 | R2",
  "tumor_size": Float
}
"""

USER_PROMPT_TEMPLATE = """Report:
---
{report_text}
---
"""




# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def get_output_path(model_alias: str, split_name: str) -> Path:
    sanitized_name = model_alias.replace("/", "_").replace(":", "_")
    return OUTPUT_DIR / f"study_{split_name}_{sanitized_name}.csv"

def get_completed_runs(output_csv: Path) -> Set[str]:
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

def call_llm(provider: str, model_id: str, system_prompt: str, user_prompt: str) -> Tuple[str, str]:
    try:
        if provider == "groq":
            if not groq_client: return "Groq client missing", "error"
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=model_id,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            return chat_completion.choices[0].message.content, "success"
        
        elif provider == "openrouter":
            if not OPENROUTER_API_KEY: return "OpenRouter Key missing", "error"
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
            data = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            resp = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=60)
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content'], "success"
            
    except Exception as e:
        return str(e), "error"
    
    return "Unknown provider", "error"

def run_inference(model_alias: str, model_config: Dict, split: str, patients: List[Dict]):
    output_csv = get_output_path(model_alias, split)
    
    if not output_csv.exists():
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['patient_id', 'model_alias', 'timestamp', 'status', 'raw_response', 'parsed_json'])
    
    completed = get_completed_runs(output_csv)
    to_process = [p for p in patients if p['patient_id'] not in completed]
    
    print(f"\n>>> {model_alias}: Processing {len(to_process)} cases...")
    
    for i, row in enumerate(to_process):
        pid = row['patient_id']
        md_path = PARSED_DIR / f"{pid}.md"
        
        if not md_path.exists(): continue
        
        with open(md_path, 'r', encoding='utf-8') as f:
            report_text = f.read()
            
        print(f"    [{i+1}/{len(to_process)}] {pid}...", end=" ", flush=True)
        
        system_prompt = PROMPT
        user_content = USER_PROMPT_TEMPLATE.format(report_text=report_text)
        
        raw_resp, status = call_llm(model_config["provider"], model_config["id"], system_prompt, user_content)
        
        parsed_json = ""
        if status == "success":
            try:
                clean = raw_resp.replace("```json", "").replace("```", "").strip()
                json.loads(clean) 
                parsed_json = clean
                print("OK")
            except:
                parsed_json = "JSON_ERROR"
                print("JSON_FAIL")
        else:
            print(f"FAIL ({status}): {raw_resp}")
            
        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([pid, model_alias, time.strftime("%Y-%m-%d %H:%M:%S"), status, raw_resp, parsed_json])
        
        time.sleep(0.3)

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default=DEFAULT_SPLIT)
    parser.add_argument("--models", nargs="+")
    args = parser.parse_args()
    
    target_models = MODELS
    if args.models:
        target_models = {k: v for k, v in MODELS.items() if k in args.models}
    
    if not target_models:
        print("No valid models selected.")
        return

    split_file = DATA_DIR / f"{args.split}_split.csv"
    if not split_file.exists():
        print("Split file missing.")
        return
        
    with open(split_file, 'r', encoding='utf-8') as f:
        patients = list(csv.DictReader(f))

    for alias, config in target_models.items():
        run_inference(alias, config, args.split, patients)

if __name__ == "__main__":
    main()