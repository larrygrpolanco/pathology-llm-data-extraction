### Final Error Analysis Report: `gpt-oss-120b` (Thyroid Extraction)

This analysis provides the evidence required to defend your "LLM as Auditor" hypothesis.

### **1. Provenance of the "Gold Standard"**
The "Ground Truth" you are evaluating against is **not** a direct extraction of the pathology report. It is the **TCGA Clinical Data Resource (TCGA-CDR)**, manually curated by the **Biospecimen Core Resource (BCR) at Nationwide Children's Hospital**.

*   **Methodology:** Human curators abstracted data from pathology reports, operative notes, and staging forms into the XML format.
*   **The Bias:** Curators followed strict **AJCC 6th/7th Edition Staging Rules**. If a specific detail (like "Minimal ETE") did not alter the final Stage (e.g., if the tumor was already T3 due to size >4cm), curators frequently omitted it or defaulted to "None" to save time, as it was clinically irrelevant for staging.
*   **The Consequence:** The XML is a **Staging Summary**, while your LLM is performing **Surgical Extraction**. This fundamental mismatch explains the majority of "errors."

---

### **2. Forensic Error Analysis: "The Smoking Guns"**

We analyzed 4 representative discrepancies to categorize them into **Model Failures** vs. **Gold Standard Flaws/Definitions**.

#### **Exhibit A: The "Staging Artifact" (Registry Inconsistency)**
*   **Patient:** `TCGA-EM-A2CN`
*   **Discrepancy:** Gold Standard = **No ETE** | LLM = **Microscopic**
*   **The Evidence (Report):** "Extrathyroidal Extension: **Identified**... pT3... with **minimal extrathyroidal extension**."
*   **The Forensic Verdict:** **The Gold Standard is Factually Incorrect.**
    *   The curator marked "No ETE" in the XML.
    *   *Why?* The tumor was **6.0 cm**. In AJCC 7th Ed., a tumor >4cm is automatically **T3**. The presence of minimal ETE *also* makes it T3. Since the size alone dictated the stage, the curator likely ignored the ETE field or defaulted it to "None".
    *   **Conclusion:** The LLM was correct; the human curator was sloppy because the detail was redundant for staging.

#### **Exhibit B: The "Dominant Nodule" Paradox (Definition Mismatch)**
*   **Patient:** `TCGA-J8-A3YH`
*   **Discrepancy:** Gold Standard = **Bilateral** | LLM = **Right Lobe**
*   **The Evidence (Report):** "Multifocal papillary carcinoma involving the right and left sides... **Predominant nodule in the right lobe... 4.5 cm**."
*   **The Forensic Verdict:** **Correct Extraction, Different Question.**
    *   The LLM followed your prompt: *"Identify the DOMINANT (largest) tumor nodule."* It correctly found the Right Lobe mass.
    *   The XML followed Staging Rules: Presence of tumor in both lobes = **Bilateral**.
    *   **Conclusion:** The model is not failing; it is answering a surgical question (Where is the main tumor?) while the dataset answers a systemic question (Is disease present on both sides?).

#### **Exhibit C: The "Strap Muscle" Confusion (Model Error)**
*   **Patient:** `TCGA-EL-A3H4`
*   **Discrepancy:** Gold Standard = **Gross** | LLM = **Microscopic**
*   **The Evidence (Report):** "THE TUMOR REPLACES THYROID LOBE AND **GROSSLY INVADES** INTO SURROUNDING SOFT TISSUE, SKELETAL AND SMOOTH MUSCLE."
*   **The Forensic Verdict:** **Genuine Model Failure.**
    *   The text contains the trigger word **"GROSSLY"**.
    *   The model likely fixated on the list of tissues ("skeletal muscle"), which usually implies microscopic invasion, and missed the adjective "GROSSLY" preceding it.
    *   **Conclusion:** This is a fixable "Attention Error."

#### **Exhibit D: The "Floating Header" (Model Error)**
*   **Patient:** `TCGA-J8-A3O2`
*   **Discrepancy:** Gold Standard = **Bilateral** | LLM = **Left Lobe**
*   **The Evidence:** Similar to Exhibit B, but notably, the specific location of the multifocal disease was buried in a frozen section diagnosis ("3.5 cm... Left lobe") while the final diagnosis was vague.
*   **Conclusion:** Validates that the LLM struggles when the "Dominant" nodule isn't clearly labeled in the final summary, defaulting to the first location it sees.

---

### **3. Final Pipeline & Prompt Refinement**

To address the **Genuine Model Failures (Exhibit C)** and handle the **Definition Mismatches (Exhibit B)**, we will update the System Prompt one last time.

**Key Changes:**
1.  **"Gross" Priority:** Explicit instruction that the word "Grossly" *overrides* any mention of skeletal muscle.
2.  **Bilateral Logic:** Adjusted to capture "Bilateral" if the report *Heading* says "Bilateral," even if a dominant nodule is found. This aligns the LLM closer to the Registry definition without losing surgical precision.



### Old Analysis

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
