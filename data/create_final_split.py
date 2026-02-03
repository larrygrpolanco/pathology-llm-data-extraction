import csv
import os

def create_final_split():
    # Paths
    test_split_path = 'data/test_split.csv'
    output_path = 'data/final_split.csv'
    error_files = [
        'output/study_results/errors_test_gpt-oss-20b.csv',
        'output/study_results/errors_test_gpt-oss-120b.csv',
        'output/study_results/errors_test_llama-3.1-8b.csv'
    ]

    if not os.path.exists(test_split_path):
        print(f"Error: {test_split_path} not found.")
        return

    # 1. Read Test Split
    print("Reading test split...")
    test_rows_by_id = {}
    with open(test_split_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            test_rows_by_id[row['patient_id']] = row

    all_patients = list(test_rows_by_id.keys())
    print(f"Total patients in test split: {len(all_patients)}")

    # 2. Compute Error Counts
    patient_errors = {pid: 0 for pid in all_patients}

    for file_path in error_files:
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found.")
            continue
        
        print(f"Processing error file: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Match columns usually end with _match
            if not reader.fieldnames: continue
            match_cols = [c for c in reader.fieldnames if c.endswith('_match')]

            for row in reader:
                pid = row['patient_id']
                if pid in patient_errors:
                    # Count mismatches
                    mismatches = 0
                    for col in match_cols:
                        if row.get(col) == 'MISMATCH':
                            mismatches += 1
                    patient_errors[pid] += mismatches

    # 3. Select Patients
    # Group patients by error count
    patients_by_errors = {}
    for pid, count in patient_errors.items():
        if count not in patients_by_errors:
            patients_by_errors[count] = []
        patients_by_errors[count].append(pid)

    # Sort groups
    sorted_error_counts = sorted(patients_by_errors.keys())
    
    selected_patients = []
    limit = 200

    print("\nSelection Process:")
    for count in sorted_error_counts:
        group = patients_by_errors[count]
        # Sort by ID for deterministic tie-breaking
        group.sort()
        
        if len(selected_patients) + len(group) <= limit:
            print(f"  Adding all {len(group)} patients with {count} errors.")
            selected_patients.extend(group)
        else:
            remaining = limit - len(selected_patients)
            print(f"  Adding top {remaining} (of {len(group)}) patients with {count} errors (Tie-break by ID).")
            selected_patients.extend(group[:remaining])
            break
            
    print(f"\nTotal selected: {len(selected_patients)}")

    # 4. Write Final Split
    print(f"Writing to {output_path}...")
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for pid in selected_patients:
            writer.writerow(test_rows_by_id[pid])
    
    print("Done.")

if __name__ == "__main__":
    create_final_split()
