### Final Error Analysis Report: `gpt-oss-120b` (Thyroid Extraction)

#### 1. Executive Summary
The model is performing with high accuracy (>90%) on Histologic Type, Margins, and Lymph Node status. The remaining performance gap (Site ~80%, ETE ~85%) is driven by **systematic definition mismatches** between the LLM's general medical knowledge and the specific curation rules of the target dataset (TCGA). The model is "correct" clinically, but "wrong" relative to the specific curation guidelines of this dataset.

#### 2. Root Cause Analysis by Field

**A. Tumor Site (The "Dominant Nodule" Conflict)**
*   **Issue:** False Positive "Bilateral".
*   **Pattern:** In cases with a large dominant tumor on one side (e.g., Right Lobe) and a tiny focus on the other (Left Lobe), the model selects "Bilateral". The Gold Standard selects "Right Lobe".
*   **Root Cause:** The model is applying TNM staging logic (Bilateral = T1b/T2), whereas the dataset annotation schema requires the **Site of the Index Tumor**.
*   **Action:** We must decouple "Site" from "Patient Status". The Site field must strictly track the largest nodule, ignoring contralateral micro-foci.

**B. Tumor Size (The "Floating Header" Artifact)**
*   **Issue:** Missed measurements in header text.
*   **Pattern:** Text reads `(3.5 CM) PAPILLARY CARCINOMA...` The model skips the header number and extracts a smaller measurement found later in the text (e.g., "0.1 cm focus").
*   **Root Cause:** The model prioritizes numbers explicitly linked to the words "tumor size" inside the text block, missing the disconnected header value.
*   **Action:** Add a specific heuristic to the prompt to scan for parenthetical measurements at the start of diagnosis lines.

**C. Extrathyroidal Extension (The "Gross" Definition)**
*   **Issue:** Over-calling "Gross" ETE.
*   **Pattern:** The report describes invasion into "skeletal muscle" or "strap muscles". The model flags this as "Gross". The Gold Standard labels it "Microscopic".
*   **Root Cause:** Clinically, strap muscle invasion is often T3b (Gross). However, this dataset requires the **explicit adjective** "Gross" or "Macroscopic" to assign that label; otherwise, soft tissue/muscle invasion is classified as Microscopic.
*   **Action:** Enforce a strict keyword constraint. "Skeletal Muscle" invasion is Microscopic unless the word "Gross" is explicitly adjacent.

**D. Histologic Variant (The "Central Review" Gap)**
*   **Issue:** Irreducible Error.
*   **Pattern:** Report says "Follicular Variant"; Gold Standard says "Classical".
*   **Root Cause:** The TCGA dataset utilized a "Central Pathology Review" which often reclassified subtypes after the report was written. The LLM extracts what is written; the ground truth reflects a later expert review.
*   **Action:** No prompt fix possible. This represents the theoretical ceiling of accuracy for this specific dataset.

---

### Improved Prompt Implementation

This prompt incorporates the fixes for **Dominant Site logic**, **Header Size parsing**, and **Strict Gross ETE definitions**.

**Replace the `SYSTEM_PROMPT` variable in `run_study_inference.py` with the following:**

```python
# Refined System Prompt
SYSTEM_PROMPT = """Role: Specialized Pathologist Assistant for Thyroid Cancer Data Extraction.

Context: Extract structured data from surgical pathology reports.

Objective: Return a valid JSON object.

--- EXTRACTION LOGIC AND RULES ---

1. histologic_type:
   - Options: "Papillary Thyroid Carcinoma" | "Other"
   - Rule: "Microcarcinoma" = "Papillary Thyroid Carcinoma".

2. histologic_variant:
   - Options: "Classical" | "Follicular" | "Tall Cell" | "Columnar Cell"
   - Priority: 
     1. Text Explicitly says "Follicular Variant" or "FVPTC" -> "Follicular".
     2. Text Explicitly says "Tall Cell" -> "Tall Cell".
     3. If "Papillary Thyroid Carcinoma" is diagnosed with NO specific variant mentioned -> "Classical".
     4. Ignore "follicular architecture" or "follicular pattern" if the diagnosis is simply PTC.

3. tumor_size:
   - Type: Float (cm).
   - Logic: 
     1. Identify the DOMINANT (Largest) tumor size.
     2. "Floating" Header Sizes: Look for measurements in parentheses at the start of Diagnosis lines (e.g., "(3.5 CM) PAPILLARY CARCINOMA"). Use this if it is the largest value.
     3. Priority: Synoptic Data > Diagnosis Header > Diagnosis Text > Gross Description.
     4. Ignore sizes of "microcarcinoma" or incidental nodules (<1cm) IF a larger distinct tumor (>1cm) is present.

4. extrathyroidal_extension (ETE):
   - Options: "No ETE" | "Microscopic" | "Gross"
   - Rules:
     - "Gross" ETE: ONLY if the text explicitly uses the words "Gross", "Grossly", or "Macroscopic", OR describes invasion into "Trachea", "Larynx", or "Esophagus".
     - "Microscopic" ETE: Describes invasion into "perithyroidal soft tissue", "adipose tissue", "skeletal muscle", or "strap muscle" WITHOUT the word "Gross".
     - "No ETE": "Confined to thyroid", "Not identified", "Negative", "Capsular invasion only" (Capsular invasion is NOT ETE).

5. margins:
   - Options: "R0" (Negative) | "R1" (Microscopic Positive) | "R2" (Gross Positive)
   - Rule: 
     - "Uninvolved", "Clear", "Negative", "Free of tumor" -> "R0".
     - "Involved", "Positive", "Tumor on ink", "Extends to margin" -> "R1".

6. tumor_site:
   - Options: "Right lobe" | "Left lobe" | "Isthmus" | "Bilateral"
   - Logic: 
     1. Identify the DOMINANT (largest) tumor nodule. Output the site of ONLY this dominant nodule.
     2. Example: "Right lobe: 4.5cm, Left lobe: 0.2cm" -> Output "Right lobe" (Ignore the contralateral focus for this field).
     3. ONLY output "Bilateral" if:
        - The text explicitly diagnoses "Bilateral Papillary Carcinoma" in the main heading AND no single dominant nodule is distinguished.
        - OR the Dominant tumor is explicitly described as spanning both lobes.

7. focality:
   - Options: "Unifocal" | "Multifocal"
   - Rule: "Single focus" -> Unifocal. "Multiple", "2 foci", "Bilateral involvement" -> Multifocal. (Note: A patient can be Multifocal even if the 'tumor_site' is recorded as Right Lobe).

8. lymph_nodes_resected:
   - Options: "yes" | "no"
   - Rule: Look for "lymph node", "LN", "Level VI". If tissue was received/examined -> "yes".

9. lymph_nodes_positive_count:
    - Rule: If lymph_nodes_resected is "yes", count the total number of POSITIVE nodes across all containers. 
    - If 0 positive nodes -> 0.

--- ROBUSTNESS ---
- If a specific field is not found, use null (except for Variant, which defaults to Classical).
- Ignore separators like "IIIIII". 
"""
```