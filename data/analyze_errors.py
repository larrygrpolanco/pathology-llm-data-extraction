import csv
import glob
import os
from collections import Counter

def analyze_errors():
    # Load test split to get all patients
    test_split_path = 'data/test_split.csv'
    if not os.path.exists(test_split_path):
        print(f"Error: {test_split_path} not found.")
        return

    all_patients = set()
    with open(test_split_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_patients.add(row['patient_id'])
            
    print(f"Total patients in test split: {len(all_patients)}")

    # Error files
    error_files = [
        'output/study_results/errors_test_gpt-oss-20b.csv',
        'output/study_results/errors_test_gpt-oss-120b.csv',
        'output/study_results/errors_test_llama-3.1-8b.csv'
    ]

    patient_errors = {pid: 0 for pid in all_patients}

    for file_path in error_files:
        if not os.path.exists(file_path):
            print(f"Warning: {file_path} not found.")
            continue
        
        print(f"Processing {file_path}...")
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            # Identify match columns
            fieldnames = reader.fieldnames
            if not fieldnames:
                continue
                
            match_cols = [c for c in fieldnames if c.endswith('_match')]

            for row in reader:
                pid = row['patient_id']
                if pid not in patient_errors:
                    continue
                
                # Count mismatches
                mismatches = 0
                for col in match_cols:
                    if row.get(col) == 'MISMATCH':
                        mismatches += 1
                
                patient_errors[pid] += mismatches

    # Analyze distribution
    error_counts = list(patient_errors.values())
    error_counts.sort()
    
    if not error_counts:
        print("No errors found or no patients matched.")
        return

    print("\n--- Error Distribution (Total Mismatches across 3 models) ---")
    print(f"Min errors: {min(error_counts)}")
    print(f"Max errors: {max(error_counts)}")
    
    # Histogram-like output
    dist = Counter(error_counts)
    for k in sorted(dist.keys()):
        print(f"Patients with {k} errors: {dist[k]}")

    # Top 200 selection
    sorted_patients = sorted(patient_errors.items(), key=lambda item: item[1])
    top_200 = sorted_patients[:200]
    
    # Check cutoff
    if len(top_200) == 200:
        cutoff_errors = top_200[-1][1]
        print(f"\n--- Selection Proposal ---")
        print(f"Top 200 cutoff error count: {cutoff_errors}")
        
        # Determine strict cutoff index
        patients_at_cutoff = [p for p in patient_errors.values() if p == cutoff_errors]
        patients_below_cutoff = [p for p in patient_errors.values() if p < cutoff_errors]
        
        print(f"Patients strictly below cutoff (< {cutoff_errors} errors): {len(patients_below_cutoff)}")
        print(f"Patients at cutoff (= {cutoff_errors} errors): {len(patients_at_cutoff)}")
        print(f"Total needed to reach 200: 200")
        
        needed_from_cutoff = 200 - len(patients_below_cutoff)
        print(f"We need {needed_from_cutoff} patients from the {len(patients_at_cutoff)} with {cutoff_errors} errors.")
        
        # Show which ones would be picked (just first local list, but ideally random or alphabetical if stable)
        # Verify stability
        print("Note: Tie-breaking strategy needed if not random.")
    else:
        print(f"Warning: Only {len(top_200)} patients available.")

if __name__ == "__main__":
    analyze_errors()
