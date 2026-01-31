import csv
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CSV_FILE = BASE_DIR / "data" / "gold_standard" / "thyroid_gold_standard.csv"

def run_checks():
    if not CSV_FILE.exists():
        print(f"Error: CSV file not found at {CSV_FILE}")
        return

    print(f"Running verification on {CSV_FILE}...\n")
    
    total_rows = 0
    incomplete_rows = 0
    column_missing_counts = {}
    value_distributions = {
        'histologic_type': {},
        'histologic_variant': {},
        'pathologic_T': {},
        'pathologic_N': {},
        'pathologic_M': {},
        'extrathyroidal_extension': {},
        'margins': {},
        'data_quality_flag': {}
    }
    file_existence_errors = []

    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            total_rows += 1
            if row['data_quality_flag'] == "INCOMPLETE":
                incomplete_rows += 1
            
            # Column missing counts
            for field in fieldnames:
                if row[field] == "Not Available" or not row[field]:
                    column_missing_counts[field] = column_missing_counts.get(field, 0) + 1
            
            # Value distributions
            for field in value_distributions:
                val = row.get(field)
                if val:
                    value_distributions[field][val] = value_distributions[field].get(val, 0) + 1
            
            # File existence check
            xml_path = BASE_DIR / row['xml_relative_path']
            pdf_path = BASE_DIR / row['pdf_relative_path'] if row['pdf_relative_path'] else None
            
            if not xml_path.exists():
                file_existence_errors.append(f"Missing XML: {xml_path}")
            if pdf_path and not pdf_path.exists():
                file_existence_errors.append(f"Missing PDF: {pdf_path}")

    # Summary
    print(f"Summary of {total_rows} cases:")
    print(f"  - Incomplete cases: {incomplete_rows} ({(incomplete_rows/total_rows)*100:.1f}%)")
    print(f"  - Files missing from disk: {len(file_existence_errors)}")
    for err in file_existence_errors[:5]:
        print(f"    - ERROR: {err}")
    if len(file_existence_errors) > 5:
        print(f"    - ... and {len(file_existence_errors)-5} more.")

    print("\nMissing values per column:")
    for field, count in column_missing_counts.items():
        if count > 0:
            print(f"  - {field:30}: {count} ({(count/total_rows)*100:.1f}%)")

    print("\nValue distributions:")
    for field, dist in value_distributions.items():
        print(f"  - {field}:")
        sorted_dist = sorted(dist.items(), key=lambda x: x[1], reverse=True)
        for val, count in sorted_dist:
            print(f"    - {val:25}: {count}")

if __name__ == "__main__":
    run_checks()
