import os
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
import re

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "GDC Data Thyroid" 
MANIFEST_FILE = RAW_DIR / "gdc_manifest.2026-01-23.102905.txt"
DOWNLOAD_DIR = RAW_DIR / "gdc_download_20260123_154153.943271"
OUTPUT_CSV = DATA_DIR / "gold_standard" / "thyroid_gold_standard.csv"

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
            sub_parts = part.split('-')
            if len(sub_parts) >= 3:
                return "-".join(sub_parts[:3])
    return None

def parse_clinical_xml(xml_path):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        disease_code_elem = root.find(".//admin:disease_code", NAMESPACES)
        if disease_code_elem is None or disease_code_elem.text != "THCA":
            return None
            
        patient = root.find(".//thca:patient", NAMESPACES)
        if patient is None: return None

        data = {}
        
        # 1. Histology
        hist_raw = patient.find(".//shared:histological_type", NAMESPACES)
        hist_text = (hist_raw.text if (hist_raw is not None and hist_raw.text) else "Not Available").strip()
        data['histologic_type'] = "Papillary Thyroid Carcinoma"
        data['histologic_variant'] = "Not Available"
        
        if hist_text != "Not Available":
            if " - " in hist_text:
                variant_raw = hist_text.split(" - ")[1]
                if "Classical" in variant_raw: data['histologic_variant'] = "Classical"
                elif "Follicular" in variant_raw: data['histologic_variant'] = "Follicular"
                elif "Tall Cell" in variant_raw: data['histologic_variant'] = "Tall Cell"
                elif "Columnar" in variant_raw: data['histologic_variant'] = "Columnar Cell"
                else: data['histologic_variant'] = variant_raw
            elif "Other" in hist_text:
                data['histologic_type'] = "Other"
        
        # 2. Pathologic T Stage (CRITICAL FOR AUDIT)
        data['pathologic_T'] = "Not Available"
        tnm = patient.find(".//shared_stage:tnm_categories/shared_stage:pathologic_categories", NAMESPACES)
        if tnm is not None:
            t = tnm.find("shared_stage:pathologic_T", NAMESPACES)
            data['pathologic_T'] = t.text if t is not None else "Not Available"
            
            # Extract N and M for completeness
            n = tnm.find("shared_stage:pathologic_N", NAMESPACES)
            data['pathologic_N'] = n.text if n is not None else "Not Available"
            m = tnm.find("shared_stage:pathologic_M", NAMESPACES)
            data['pathologic_M'] = m.text if m is not None else "Not Available"

        # 3. Extrathyroidal Extension
        ete_raw = patient.find(".//thca:extrathyroid_carcinoma_present_extension_status", NAMESPACES)
        ete_text = (ete_raw.text if (ete_raw is not None and ete_raw.text) else "Not Available").strip().lower()
        
        if any(x in ete_text for x in ["none", "not identified"]):
            data['extrathyroidal_extension'] = "No ETE"
        elif "minimal" in ete_text:
            data['extrathyroidal_extension'] = "Microscopic"
        elif any(x in ete_text for x in ["moderate", "advanced", "gross"]):
            data['extrathyroidal_extension'] = "Gross"
        elif ete_text == "not available":
            data['extrathyroidal_extension'] = "Not Available"
        else:
            # Fallback cleaning
            clean_ete = re.sub(r'\(T\d[abc]?\)', '', ete_text).strip().capitalize()
            data['extrathyroidal_extension'] = clean_ete if clean_ete else "Not Available"

        # 4. Margins
        margins_raw = patient.find(".//clin_shared:residual_tumor", NAMESPACES)
        margins_text = (margins_raw.text if (margins_raw is not None and margins_raw.text) else "Not Available").strip().upper()
        data['margins'] = margins_text if margins_text in ["R0", "R1", "R2"] else "Not Available"
        
        # 5. Focality
        focality = patient.find(".//thca:primary_neoplasm_focus_type", NAMESPACES)
        data['focality'] = focality.text if focality is not None else "Not Available"
        
        # 6. Lymph Nodes
        nodes_examined_status = patient.find(".//clin_shared:primary_lymph_node_presentation_assessment", NAMESPACES)
        exam_status = nodes_examined_status.text if nodes_examined_status is not None else "Not Available"
        data['lymph_nodes_examined_status'] = exam_status
        
        nodes_examined = patient.find(".//clin_shared:lymph_node_examined_count", NAMESPACES)
        nodes_positive = patient.find(".//clin_shared:number_of_lymphnodes_positive_by_he", NAMESPACES)
        data['lymph_nodes_examined_count'] = nodes_examined.text if nodes_examined is not None else "Not Available"
        data['lymph_nodes_positive_count'] = nodes_positive.text if nodes_positive is not None else "Not Available"
        
        if data['lymph_nodes_examined_count'] not in ["Not Available", None]:
            try:
                count = int(data['lymph_nodes_examined_count'])
                data['lymph_nodes_resected'] = "yes" if count > 0 else "no"
            except:
                data['lymph_nodes_resected'] = "yes" if exam_status == "YES" else "no"
        else:
            data['lymph_nodes_resected'] = "yes" if exam_status == "YES" else "no"
        
        # 7. Tumor Site
        site = patient.find(".//thca:primary_thyroid_gland_neoplasm_location_anatomic_site", NAMESPACES)
        data['tumor_site'] = site.text if site is not None else "Not Available"
        
        # 8. Tumor Size
        tumor_size = 0.0
        dims = patient.find(".//thca:neoplasm_dimension", NAMESPACES)
        if dims is not None:
            for dim_tag in ["thca:neoplasm_length", "thca:neoplasm_width", "thca:neoplasm_depth"]:
                dim_elem = dims.find(dim_tag, NAMESPACES)
                if dim_elem is not None and dim_elem.text:
                    try:
                        val = float(dim_elem.text)
                        if val > tumor_size:
                            tumor_size = val
                    except ValueError:
                        pass
        data['tumor_size'] = tumor_size if tumor_size > 0 else "Not Available"
        
        return data

    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
        return None

def main():
    print("Starting data extraction pipeline...")
    data_map = {}
    if not MANIFEST_FILE.exists():
        print(f"Error: Manifest file not found at {MANIFEST_FILE}")
        return

    with open(MANIFEST_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            file_id = row['id']
            filename = row['filename']
            barcode = get_patient_barcode(filename)
            if not barcode: continue
            if barcode not in data_map: data_map[barcode] = {'xml': None, 'pdf': None, 'xml_path': None, 'pdf_path': None}
            file_path = DOWNLOAD_DIR / file_id / filename
            if filename.endswith(".xml") and "clinical" in filename:
                data_map[barcode]['xml'] = filename
                data_map[barcode]['xml_path'] = str(file_path.relative_to(BASE_DIR))
            elif filename.endswith(".PDF") or filename.endswith(".pdf"):
                data_map[barcode]['pdf'] = filename
                data_map[barcode]['pdf_path'] = str(file_path.relative_to(BASE_DIR))

    results = []
    for barcode, files in data_map.items():
        if not files['xml_path']: continue
        full_xml_path = BASE_DIR / files['xml_path']
        pathology_data = parse_clinical_xml(full_xml_path)
        if pathology_data is None: continue
            
        entry = {'patient_id': barcode, 'xml_filename': files['xml'], 'pdf_filename': files['pdf'], 'xml_relative_path': files['xml_path'], 'pdf_relative_path': files['pdf_path']}
        entry.update(pathology_data)
        
        # QC Logic
        is_incomplete = False
        pathologic_n = pathology_data.get('pathologic_N', "Not Available")
        needs_lymph_nodes = ("1" in pathologic_n) if pathologic_n != "Not Available" else False
        for key, value in pathology_data.items():
            if value == "Not Available" or value is None:
                if not needs_lymph_nodes and key in ['lymph_nodes_examined_count', 'lymph_nodes_positive_count']: continue
                is_incomplete = True
                break
        entry['data_quality_flag'] = "INCOMPLETE" if is_incomplete else "OK"
        results.append(entry)

    if results:
        fieldnames = list(results[0].keys())
        with open(OUTPUT_CSV, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"Gold standard saved to: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()