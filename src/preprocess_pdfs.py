import os
import csv
import nest_asyncio
from pathlib import Path
from dotenv import load_dotenv
from llama_parse import LlamaParse

# Apply nest_asyncio to allow async execution within this script context if needed
nest_asyncio.apply()

# Load environment variables
load_dotenv()

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent # pathology-llm-data-extraction/
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PARSED_DIR = DATA_DIR / "parsed_reports"
GOLD_STANDARD_CSV = DATA_DIR / "gold_standard" / "thyroid_gold_standard.csv"

# Initialize LlamaParser
# We use 'markdown' result type for clean LLM consumption
parser = LlamaParse(
    result_type="markdown",
    verbose=True,
    language="en",
    num_workers=4
)

def main():
    if not GOLD_STANDARD_CSV.exists():
        print(f"Error: Gold standard CSV not found at {GOLD_STANDARD_CSV}")
        return

    # Ensure output directory exists
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Starting PDF processing...\nSource CSV: {GOLD_STANDARD_CSV}\nOutput Dir: {PARSED_DIR}")

    files_processed = 0
    files_skipped = 0
    files_failed = 0

    with open(GOLD_STANDARD_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        total_files = len(rows)

        print(f"Found {total_files} cases to process.")

        for i, row in enumerate(rows):
            patient_id = row['patient_id']
            pdf_rel_path = row['pdf_relative_path']

            if not pdf_rel_path or pdf_rel_path == "None":
                print(f"[{i+1}/{total_files}] Skipping {patient_id}: No PDF linked.")
                files_skipped += 1
                continue

            # Construct paths
            # The CSV path is like "data/raw/GDC Data Thyroid/..."
            # We join with BASE_DIR since the relative path already starts with data/raw/
            pdf_path = BASE_DIR / pdf_rel_path
            output_path = PARSED_DIR / f"{patient_id}.md"

            if output_path.exists():
                print(f"[{i+1}/{total_files}] Skipping {patient_id}: Already parsed.")
                files_skipped += 1
                continue

            if not pdf_path.exists():
                print(f"[{i+1}/{total_files}] Error {patient_id}: PDF not found at {pdf_path}")
                files_failed += 1
                continue

            try:
                print(f"[{i+1}/{total_files}] Parsing {patient_id} ({pdf_path.name})...")
                
                # Run LlamaParse
                # load_data returns a list of Document objects
                documents = parser.load_data(str(pdf_path))
                
                if not documents:
                    print(f"  -> Warning: No content extracted for {patient_id}")
                    files_failed += 1
                    continue

                # Combine content if multiple pages/docs
                full_text = "\n\n".join([doc.text for doc in documents])
                
                # Save to Markdown
                with open(output_path, "w", encoding="utf-8") as out:
                    out.write(full_text)
                
                print(f"  -> Saved to {output_path.name}")
                files_processed += 1

            except Exception as e:
                print(f"  -> Error parsing {patient_id}: {e}")
                files_failed += 1

    print("\nProcessing Complete!")
    print(f"Processed: {files_processed}")
    print(f"Skipped (Already Linked/Missing PDF): {files_skipped}")
    print(f"Failed: {files_failed}")

if __name__ == "__main__":
    main()
