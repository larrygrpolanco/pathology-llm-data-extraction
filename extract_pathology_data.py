import os
import csv
import xml.etree.ElementTree as ET
from pathlib import Path

# Paths
BASE_DIR = Path("/Users/larrygrpolanco/Documents/GitHub/pathology-llm-data-extraction")
DATA_DIR = BASE_DIR / "GDC Data Thyroid"
MANIFEST_FILE = DATA_DIR / "gdc_manifest.2026-01-23.102905.txt"
DOWNLOAD_DIR = DATA_DIR / "gdc_download_20260123_154153.943271"
OUTPUT_CSV = BASE_DIR / "thyroid_gold_standard.csv"

# Namespaces
NAMESPACES = {
    'admin': 'http://tcga.nci/bcr/xml/administration/2.7',
    'shared': 'http://tcga.nci/bcr/xml/shared/2.7',
    'clin_shared': 'http://tcga.nci/bcr/xml/clinical/shared/2.7',
    'shared_stage': 'http://tcga.nci/bcr/xml/clinical/shared/stage/2.7',
    'thca': 'http://tcga.nci/bcr/xml/clinical/thca/2.7'
}

def get_patient_barcode(filename):
    """Extracts TCGA-XX-YYYY barcode from filename."""
    parts = filename.split('.')
    for part in parts:
        if part.startswith("TCGA-"):
            # Barcode format is TCGA-XX-YYYY
            sub_parts = part.split('-')
            if len(sub_parts) >= 3:
                return "-".join(sub_parts[:3])
    return None

def parse_clinical_xml(xml_path):
    """Parses the THCA clinical XML for specific pathology elements."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Determine disease code to ensure we are processing THCA
        disease_code_elem = root.find(".//admin:disease_code", NAMESPACES)
        disease_code = disease_code_elem.text if disease_code_elem is not None else None
        
        if disease_code != "THCA":
            return None # Skip non-thyroid cases
            
        patient = root.find(".//thca:patient", NAMESPACES)
        if patient is None:
            return None

        data = {}
        
        # 1. Histologic Type
        hist_type = patient.find(".//shared:histological_type", NAMESPACES)
        data['histologic_type'] = hist_type.text if hist_type is not None else "Not Available"
        
        # 2. Pathologic Stage
        stage = patient.find(".//shared_stage:pathologic_stage", NAMESPACES)
        data['pathologic_stage'] = stage.text if stage is not None else "Not Available"
        
        # TNM Categories
        data['pathologic_T'] = "Not Available"
        data['pathologic_N'] = "Not Available"
        data['pathologic_M'] = "Not Available"
        
        tnm = patient.find(".//shared_stage:tnm_categories/shared_stage:pathologic_categories", NAMESPACES)
        if tnm is not None:
            t = tnm.find("shared_stage:pathologic_T", NAMESPACES)
            n = tnm.find("shared_stage:pathologic_N", NAMESPACES)
            m = tnm.find("shared_stage:pathologic_M", NAMESPACES)
            data['pathologic_T'] = t.text if t is not None else "Not Available"
            data['pathologic_N'] = n.text if n is not None else "Not Available"
            data['pathologic_M'] = m.text if m is not None else "Not Available"
            
        # 6. Extrathyroidal Extension
        ete = patient.find(".//thca:extrathyroid_carcinoma_present_extension_status", NAMESPACES)
        data['extrathyroidal_extension'] = ete.text if ete is not None else "Not Available"
        
        # 7. Focality
        focality = patient.find(".//thca:primary_neoplasm_focus_type", NAMESPACES)
        data['focality'] = focality.text if focality is not None else "Not Available"
        
        # 8. Lymph Node Count and Assessment
        nodes_examined_status = patient.find(".//clin_shared:primary_lymph_node_presentation_assessment", NAMESPACES)
        data['lymph_nodes_examined_status'] = nodes_examined_status.text if nodes_examined_status is not None else "Not Available"
        
        nodes_examined = patient.find(".//clin_shared:lymph_node_examined_count", NAMESPACES)
        nodes_positive = patient.find(".//clin_shared:number_of_lymphnodes_positive_by_he", NAMESPACES)
        data['lymph_nodes_examined_count'] = nodes_examined.text if nodes_examined is not None else "Not Available"
        data['lymph_nodes_positive_count'] = nodes_positive.text if nodes_positive is not None else "Not Available"
        
        return data

    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
        return None

def main():
    print("Starting data extraction pipeline...")
    
    # Load manifest
    data_map = {}
    if not MANIFEST_FILE.exists():
        print(f"Error: Manifest file not found at {MANIFEST_FILE}")
        return

    with open(MANIFEST_FILE, mode='r', encoding='utf-8') as f:
        # The manifest is tab-separated
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            file_id = row['id']
            filename = row['filename']
            barcode = get_patient_barcode(filename)
            
            if not barcode:
                continue
                
            if barcode not in data_map:
                data_map[barcode] = {'xml': None, 'pdf': None, 'xml_path': None, 'pdf_path': None}
                
            file_path = DOWNLOAD_DIR / file_id / filename
            if not file_path.exists():
                print(f"Warning: File not found: {file_path}")
                continue
                
            if filename.endswith(".xml") and "clinical" in filename:
                data_map[barcode]['xml'] = filename
                data_map[barcode]['xml_path'] = str(file_path.relative_to(BASE_DIR))
            elif filename.endswith(".PDF") or filename.endswith(".pdf"):
                data_map[barcode]['pdf'] = filename
                data_map[barcode]['pdf_path'] = str(file_path.relative_to(BASE_DIR))

    # Extract data and generate gold standard
    results = []
    skipped_non_thca = 0
    missing_xml = 0
    missing_pdf = 0
    
    for barcode, files in data_map.items():
        if not files['xml_path']:
            missing_xml += 1
            print(f"Skipping {barcode}: Missing clinical XML")
            continue
            
        full_xml_path = BASE_DIR / files['xml_path']
        pathology_data = parse_clinical_xml(full_xml_path)
        
        if pathology_data is None:
            skipped_non_thca += 1
            continue
            
        if not files['pdf_path']:
            missing_pdf += 1
            print(f"Warning: {barcode} has XML but no PDF")
            
        entry = {
            'patient_id': barcode,
            'xml_filename': files['xml'],
            'pdf_filename': files['pdf'],
            'xml_relative_path': files['xml_path'],
            'pdf_relative_path': files['pdf_path'],
        }
        entry.update(pathology_data)
        
        # Data Quality Flag Logic
        # We flag as incomplete if any required field is "Not Available"
        # BUT: if lymph_nodes_examined_status is "NO", then missing counts are OK.
        is_incomplete = False
        skip_node_counts = (pathology_data.get('lymph_nodes_examined_status') == "NO")
        
        for key, value in pathology_data.items():
            if value == "Not Available" or value is None:
                if skip_node_counts and key in ['lymph_nodes_examined_count', 'lymph_nodes_positive_count']:
                    continue
                is_incomplete = True
                break
                
        entry['data_quality_flag'] = "INCOMPLETE" if is_incomplete else "OK"
        
        results.append(entry)

    # Save to CSV
    if results:
        fieldnames = list(results[0].keys())
        with open(OUTPUT_CSV, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
            
        print(f"\nPipeline completed successfully!")
        print(f"Total THCA cases extracted: {len(results)}")
        print(f"Total cases skipped (non-THCA): {skipped_non_thca}")
        print(f"Total cases missing XML: {missing_xml}")
        print(f"Total THCA cases missing PDF: {missing_pdf}")
        print(f"Gold standard saved to: {OUTPUT_CSV}")
    else:
        print("\nNo data extracted. Check manifest and directory structure.")

if __name__ == "__main__":
    main()
