"""
Confidence Calibration Study - Sequential Per-Field Inference
Processes each field separately with confidence scoring for GPT-OSS-120B
"""

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
import field_prompts as fp

# =============================================================================
# USER SETTINGS
# =============================================================================

DEFAULT_SPLIT = "dev"  # Will move to "final" later
DEFAULT_MODEL = "gpt-oss-120b"
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds between retries
API_DELAY = 0.3  # seconds between API calls

# =============================================================================
# SYSTEM CONFIGURATION
# =============================================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = OUTPUT_DIR / "logs"
RESULTS_DIR = OUTPUT_DIR / "results"
DATA_DIR = BASE_DIR.parent / "data"
PARSED_DIR = DATA_DIR / "parsed_reports"

# Create output directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_ID = "openai/gpt-oss-120b"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_log_path(patient_id: str, field: str, split_name: str) -> Path:
    """Get path for individual field log file."""
    return LOGS_DIR / f"{split_name}_{patient_id}_{field}.json"


def get_aggregated_path(split_name: str) -> Path:
    """Get path for aggregated results CSV."""
    return RESULTS_DIR / f"confidence_study_{split_name}_aggregated.csv"


def get_completed_patients(split_name: str) -> Set[str]:
    """Get set of patient IDs that have been fully processed."""
    completed = set()
    agg_path = get_aggregated_path(split_name)

    if not agg_path.exists():
        return completed

    try:
        with open(agg_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("patient_id"):
                    completed.add(row["patient_id"].strip())
    except Exception as e:
        print(f"Warning: Could not read completed patients: {e}")

    return completed


def call_llm_with_retry(
    field: str, report_text: str, max_retries: int = MAX_RETRIES
) -> Tuple[Optional[Dict], str, int]:
    """
    Call LLM for a single field with retry logic.

    Returns:
        Tuple of (parsed_result_dict, status, retry_count)
        - parsed_result_dict: The parsed JSON result or None if failed
        - status: "success" or "error"
        - retry_count: Number of retries used
    """
    if not groq_client:
        return None, "error_no_client", 0

    system_prompt = fp.get_field_prompt(field)
    user_prompt = f"Report:\n---\n{report_text}\n---"

    for attempt in range(max_retries + 1):
        try:
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=GROQ_MODEL_ID,
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            raw_content = response.choices[0].message.content

            # Parse JSON
            try:
                # Clean up any markdown code blocks
                clean = raw_content.replace("```json", "").replace("```", "").strip()
                result = json.loads(clean)

                # Validate required fields
                if "value" not in result:
                    if attempt < max_retries:
                        print(f"      Missing 'value' field, retrying...")
                        time.sleep(RETRY_DELAY)
                        continue
                    return None, "error_missing_value", attempt

                if "confidence" not in result:
                    if attempt < max_retries:
                        print(f"      Missing 'confidence' field, retrying...")
                        time.sleep(RETRY_DELAY)
                        continue
                    return None, "error_missing_confidence", attempt

                # Normalize confidence
                confidence = str(result.get("confidence", "")).strip().lower()
                if confidence not in ["high", "medium", "low"]:
                    # Try to normalize common variations
                    if confidence in ["h", "hi", "high confidence"]:
                        result["confidence"] = "High"
                    elif confidence in ["m", "med", "medium confidence"]:
                        result["confidence"] = "Medium"
                    elif confidence in ["l", "lo", "low confidence"]:
                        result["confidence"] = "Low"
                    else:
                        result["confidence"] = "Medium"  # Default to medium if unclear
                else:
                    result["confidence"] = confidence.capitalize()

                # Ensure reasoning exists
                if "reasoning" not in result:
                    result["reasoning"] = ""

                return result, "success", attempt

            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    print(f"      JSON parse error, retrying...")
                    time.sleep(RETRY_DELAY)
                    continue
                return None, f"error_json_parse: {str(e)}", attempt

        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries:
                print(f"      API error (attempt {attempt + 1}), retrying...")
                time.sleep(RETRY_DELAY)
                continue
            return None, f"error_api: {error_msg}", attempt

    return None, "error_max_retries", max_retries


def process_patient(
    patient_id: str, report_text: str, split_name: str, fields: List[str]
) -> Dict[str, Any]:
    """
    Process all fields for a single patient.

    Returns dict with all field results and metadata.
    """
    results = {
        "patient_id": patient_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fields": {},
    }

    print(f"\n  Processing {patient_id}...")

    for field in fields:
        print(f"    [{field}] ", end="", flush=True)

        # Check if already logged
        log_path = get_log_path(patient_id, field, split_name)
        if log_path.exists():
            # Load existing result
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    saved_result = json.load(f)
                results["fields"][field] = saved_result
                print(f"loaded (saved)")
                continue
            except:
                pass  # Will re-process if load fails

        # Call LLM with retry
        result, status, retries = call_llm_with_retry(field, report_text)

        # Build field result
        field_result = {
            "field": field,
            "status": status,
            "retries": retries,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if result and status == "success":
            field_result.update(
                {
                    "value": result["value"],
                    "confidence": result["confidence"],
                    "reasoning": result["reasoning"],
                }
            )
            print(f"OK (retries: {retries})")
        else:
            field_result.update(
                {
                    "value": None,
                    "confidence": "Low",  # Default to low on error
                    "reasoning": f"Error: {status}",
                }
            )
            print(f"FAILED ({status})")

        # Save individual field log
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(field_result, f, indent=2)

        results["fields"][field] = field_result

        # Delay between API calls
        time.sleep(API_DELAY)

    return results


def aggregate_and_save(patient_results: List[Dict], split_name: str):
    """Aggregate all patient results and save to CSV."""

    rows = []
    fields = fp.get_all_fields()

    for patient in patient_results:
        row = {"patient_id": patient["patient_id"], "timestamp": patient["timestamp"]}

        # Add each field's data
        for field in fields:
            field_data = patient["fields"].get(field, {})
            row[f"{field}_value"] = field_data.get("value", "")
            row[f"{field}_confidence"] = field_data.get("confidence", "")
            row[f"{field}_reasoning"] = field_data.get("reasoning", "")
            row[f"{field}_status"] = field_data.get("status", "")

        rows.append(row)

    # Write to CSV
    output_path = get_aggregated_path(split_name)

    if rows:
        fieldnames = ["patient_id", "timestamp"]
        for field in fields:
            fieldnames.extend(
                [
                    f"{field}_value",
                    f"{field}_confidence",
                    f"{field}_reasoning",
                    f"{field}_status",
                ]
            )

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"\nAggregated results saved to: {output_path}")
        print(f"Total patients: {len(rows)}")


def main():
    parser = argparse.ArgumentParser(description="Run confidence calibration study")
    parser.add_argument(
        "--split", default=DEFAULT_SPLIT, help="Data split to use (test/final)"
    )
    parser.add_argument("--patient", help="Process single patient ID (for testing)")
    args = parser.parse_args()

    # Load patient list
    split_file = DATA_DIR / f"{args.split}_split.csv"
    if not split_file.exists():
        print(f"Error: Split file not found: {split_file}")
        return

    with open(split_file, "r", encoding="utf-8") as f:
        patients = list(csv.DictReader(f))

    print(f"Loaded {len(patients)} patients from {args.split} split")

    # Get already completed patients
    completed = get_completed_patients(args.split)
    print(f"Already completed: {len(completed)} patients")

    # Filter to process
    if args.patient:
        # Process single patient
        to_process = [p for p in patients if p["patient_id"] == args.patient]
        if not to_process:
            print(f"Patient {args.patient} not found in split")
            return
    else:
        # Process all uncompleted
        to_process = [p for p in patients if p["patient_id"] not in completed]

    print(f"To process: {len(to_process)} patients")

    if not to_process:
        print("Nothing to process!")
        return

    # Get field list
    fields = fp.get_all_fields()
    print(f"Fields to extract: {', '.join(fields)}")
    print(
        f"Expected API calls: {len(to_process)} patients × {len(fields)} fields = {len(to_process) * len(fields)} calls"
    )

    # Process patients
    all_results = []

    for i, patient_row in enumerate(to_process):
        patient_id = patient_row["patient_id"]

        # Load report
        md_path = PARSED_DIR / f"{patient_id}.md"
        if not md_path.exists():
            print(f"Warning: Report not found for {patient_id}, skipping")
            continue

        with open(md_path, "r", encoding="utf-8") as f:
            report_text = f.read()

        # Process all fields for this patient
        result = process_patient(patient_id, report_text, args.split, fields)
        all_results.append(result)

        # Save progress after each patient
        aggregate_and_save(all_results, args.split)

        # Progress update
        if (i + 1) % 10 == 0:
            print(f"\n  === Progress: {i + 1}/{len(to_process)} patients complete ===")

    print(f"\n{'=' * 60}")
    print(f"Study complete!")
    print(f"Results saved to: {get_aggregated_path(args.split)}")
    print(f"Individual field logs in: {LOGS_DIR}")


if __name__ == "__main__":
    main()
