# Pathology Data Extraction: Error Analysis

## 1. Error Definitions

- **Curator Error (CE)**: Gold standard is incorrect based on the text.
- **Definition Mismatch (DM)**: Curation logic/schema difference (e.g., "Dominant Nodule Rule").
- **LLM Error (LE)**: Model failed to extract accurately despite clear text.
- **Parsing Issue (PI)**: Bad scan, OCR errors, or handwriting issues.
- **Ambiguous (AC)**: Conflicting information in report making it unclear.

---

## 2. Review Table

| Patient ID | Variable | Gold Label | LLM Output | Error Type | Reviewer Notes / Text Evidence |
| :--------- | :------- | :--------- | :--------- | :--------: | :----------------------------- |
|            |          |            |            |            |                                |

---

## 3. Findings & Observations

### **Variable:** `histologic_variant`
**The Core Story:** The LLM consistently fails when the report mentions **multiple** variants. It struggles to determine which variant is "Dominant" or "Primary" and tends to latch onto the most specific/rare word it finds, ignoring the boring "Classical" label.

#### **Error Type 1: Specificity Bias (The "Keyword Trap")**
**Definition:** The text contains two conflicting concepts (e.g., "Classical" AND "Follicular"). The LLM incorrectly prioritizes the *rare* or *specific* term over the generic one, whereas the Gold Standard prioritizes the dominant or standard classification.

*   **The Scenario (Mixed Subtypes):** The report diagnosis is "Mixed Classical and Follicular Variant."
    *   **The Conflict:** The LLM sees the word "Follicular"—a specific keyword it was trained to look for—and outputs `Follicular`. The Gold Standard follows a coding rule: *If Mixed, default to Classical.*
    *   **Evidence (TCGA-DE-A69K):** The diagnosis explicitly states "mixed classical and follicular variant." The LLM output `Follicular`; the Gold Standard is `Classical`.

*   **The Scenario (Multicentricity):** The patient has two tumors. The big one is Classical; the tiny one is Tall Cell.
    *   **The Conflict:** The LLM scans the whole document, finds "Tall Cell" (a high-risk variant), and flags the whole patient as `Tall Cell`. The Gold Standard only codes the dominant (largest) tumor.
    *   **Evidence (TCGA-DJ-A3VA):** The header says "Papillary carcinoma, classical." Deep in the notes, it mentions a small secondary focus of "tall cell variant." The LLM output `Tall Cell`.

#### **Error Type 2: Clinical Ambiguity (The "Gray Area")**
**Definition:** The report text is linguistically vague or contradictory, forcing a subjective judgment call. The LLM interprets the text literally, while the human annotator interprets the "spirit" of the diagnosis.

*   **The Scenario:** The report describes a tumor as having "Focal tall cell **features**" but does not explicitly diagnose it as "Tall Cell **Variant**."
    *   **The Conflict:** The prompt told the LLM to be precise. "Features" $\neq$ "Variant," so the LLM output `Classical`. The human annotator decided the features were significant enough to warrant the `Tall Cell` label.
    *   **Evidence (TCGA-ET-A25L):** The diagnosis was "Papillary carcinoma with focal tall cell features." The LLM played it safe (`Classical`); the Gold Standard upgraded it (`Tall Cell`).

---


Based on the provided reports, XML gold standards, and error logs, here is the error analysis for **Extrathyroidal Extension (ETE)**.

Performance on this variable is high (F1 > 0.96 across models), meaning errors are not systemic failures of reading ability. Instead, they represent specific **Edge Cases** where the models struggle with the ambiguity of clinical documentation vs. strict staging rules.

### Error Taxonomy: Extrathyroidal Extension

We can categorize the failures into three distinct types: **Template Artifacts**, **Staging Definition Conflicts**, and **Implicit vs. Explicit Logic**.

---

#### 1. Template Artifact Errors (Hallucination from Form Data)
*The model "reads" text that is present in the document but is actually unedited template boilerplate that should be ignored.*

*   **Evidence (TCGA-E8-A416):**
    *   **Gold Standard:** "No ETE"
    *   **Models (20B & 120B):** "Microscopic"
    *   **The Discrepancy:** The text contains a metadata header that looks like a form field: *"Laterality: ... Tumor invades in capsule or vessel or benign tissue or muscle."* The pathologist did not cross this out or circle it. However, later in the specific Synoptic Table, the report explicitly states: *"Extension beyond capsule: Not specified"*.
    *   **Analysis:** The models prioritized the descriptive list in the header (interpreting "Tumor invades..." as a statement of fact) rather than the "Not specified" in the structured table. This is a failure to distinguish **active clinical data** from **passive form templates**.

#### 2. Staging Definition Conflicts (Literal vs. Clinical Logic)
*The model correctly extracts the anatomical finding, but the Prompt and the Gold Standard disagree on the staging severity (Gross vs. Microscopic).*

*   **Evidence (TCGA-DJ-A2PT):**
    *   **Gold Standard:** "Microscopic" (XML notes: "Minimal (T3)")
    *   **Models (20B & 120B):** "Gross"
    *   **The Text:** *"Extrathyroid Extension: tissue and **skeletal muscle**"*
    *   **The Prompt Rule:** *"Invades strap muscles/trachea -> 'Gross'"*
    *   **Analysis:** The model followed the prompt perfectly: it saw "skeletal muscle" and categorized it as "Gross." However, the Gold Standard (using AJCC 7th Ed) coded this as T3 ("Minimal").
    *   **The Error:** This is not an extraction error (the model read "skeletal muscle" correctly); it is a **Definition Alignment** error. The prompt instructs the model to treat muscle invasion as "Gross" (conceptually accurate for advanced disease), but the registry treated it as "Microscopic/Minimal" for that specific staging edition.

#### 3. Inference Failures (Absence of Evidence vs. Evidence of Absence)
*The Gold Standard infers ETE from context clues (like positive margins), while the model requires an explicit statement.*

*   **Evidence (TCGA-DJ-A3V5):**
    *   **Gold Standard:** "Microscopic"
    *   **Models (120B & 20B):** "No ETE"
    *   **The Text:** The section for Extrathyroid Extension is effectively blank or vague, but the report notes: *"Surgical Margins: Positive for tumor"* and *"Tumor Encapsulation: None Identified"*.
    *   **Analysis:** The Gold Standard likely inferred that if margins are positive on an unencapsulated tumor, there is microscopic extension into surrounding tissue. The model adhered strictly to the "Not identified -> No ETE" rule because "Extrathyroid Extension" was not explicitly described as "Present."
    *   **The Error:** The model lacks the clinical reasoning to **infer** a finding when it is not explicitly stated in its designated field.


Based on the comparison between the provided text (Pathology Reports) and the Ground Truth (XML files), here is the error analysis for the **`margins`** variable.

### Variable: `margins`

The primary error type observed for this variable stems from the difference between **Pathological Evaluation** (what is seen under the microscope) and **Clinical Staging** (what the surgeon sees in the patient).

#### Error Type: Source Data Scope Limitation (Clinical vs. Pathological Discordance)

**Description:**
The Ground Truth (XML) utilizes the **Clinical Residual Tumor (R) Classification**. This classification aggregates data from multiple sources: the Pathology Report (for microscopic margins) *and* the Operative Report (for macroscopic tumor left behind).

The LLM is restricted to the **Pathology Report**. Consequently, the LLM can identify Microscopic Residual Tumor (R1) based on "positive margins," but it often fails to identify Macroscopic Residual Tumor (R2) because "visible tumor left in the neck" is typically documented in the surgeon's operative note, not the pathology report.

**Evidence:**

*   **Case:** `TCGA-EL-A3CN`
    *   **Source Text (Pathology Report):** "TUMOR FOCALLY EXTENDS TO INKED MARGIN OF RESECTION." / "The nodule abuts the anterior surgical margin."
    *   **LLM Extraction (Based on Text):** **R1** (Positive/Involved margins).
    *   **Ground Truth (XML):** `clin_shared:residual_tumor`: **R2**.
    *   **Analysis:** The pathology report confirms the tumor went to the edge of the removed tissue (R1). However, the XML indicates **R2** (Macroscopic Residual), implying the surgeon knew they left visible tumor behind that could not be resected. The LLM correctly interpreted the text provided but failed to match the XML because the determining factor (macroscopic residual) was absent from the text.

*   **Case:** `TCGA-DJ-A3V5` (Control/Correct Instance)
    *   **Source Text (Pathology Report):** "Surgical Margins: Positive for tumor".
    *   **LLM Extraction (Based on Text):** **R1**.
    *   **Ground Truth (XML):** `clin_shared:residual_tumor`: **R1**.
    *   **Analysis:** In this case, the clinical reality matched the pathological finding (no gross tumor was left behind, but the margins were microscopically positive). Therefore, the LLM and XML aligned.

#### Summary of Overarching Code for this Variable

| Error Code | Definition | Impact |
| :--- | :--- | :--- |
| **Information Silo (Missing Context)** | The extracted variable requires integration of clinical observation (Surgeon's visual assessment) which is not present in the provided source text (Pathologist's specimen assessment). | The LLM will consistently under-classify **R2** (Gross Residual) as **R1** (Microscopic Residual) when the text describes positive margins but lacks explicit mention of "grossly unresected tumor." |

Based on an analysis of the mismatch data in `errors_final_gpt-oss-120b.csv` and `errors_final_gpt-oss-120bold.csv` alongside the provided pathology reports, the errors for **tumor_site** can be categorized into three distinct error codes.

The primary driver of error (accounting for >80% of mismatches) is not a failure of reading comprehension, but a **divergence between the Prompt Logic and the Gold Standard definition**. The prompt strictly enforces a "Bilateral" label if *any* carcinoma is present in the contralateral lobe, whereas the Gold Standard (TCGA metadata) frequently ignores contralateral microcarcinomas (<1cm) in favor of the dominant nodule's location.

### Error Taxonomy: Tumor Site

#### Code 1: Rule-Induced Over-Sensitivity (The Microcarcinoma Trap)
**Definition:** The LLM correctly identifies a dominant tumor in one lobe and a secondary focus (often a microcarcinoma) in the contralateral lobe. Following the prompt's explicit instruction ("Check for ANY carcinoma in the contralateral lobe... If carcinoma is present in BOTH lobes -> Output Bilateral"), the LLM outputs "Bilateral." However, the Gold Standard classifies the site based solely on the dominant tumor.

*   **Nature of Error:** Logic Alignment (Prompt vs. Registry Standard). The LLM is factually correct based on the prompt but "incorrect" based on the Gold Standard.
*   **Frequency:** High.
*   **Evidence:**
    *   **Case TCGA-DJ-A13M:**
        *   *Report:* "Tumor Location: Left lobe... Tumor Multicentricity: Separate focus of papillary microcarcinoma... in **right lobe (0.7 cm)**."
        *   *LLM Output:* **Bilateral** (Correctly saw Left Dominant + Right Micro).
        *   *Gold Standard:* **Left lobe** (Ignored the Right Micro).
    *   **Case TCGA-DJ-A13T:**
        *   *Report:* "Tumor Location: Right lobe... Tumor Multicentricity: Two microscopic foci noted... 2.4mm focus on the **left**."
        *   *LLM Output:* **Bilateral**.
        *   *Gold Standard:* **Right lobe**.
    *   **Case TCGA-DJ-A1QI:**
        *   *Report:* "Tumor Location: Right lobe... Six papillary microcarcinomas, in **both lobes** and isthmus."
        *   *LLM Output:* **Bilateral**.
        *   *Gold Standard:* **Right lobe**.

#### Code 2: Anatomical Contiguity Ambiguity (The Isthmus Problem)
**Definition:** The tumor is centered in the Isthmus or near the midline. The Gross Description or Microscopic Description notes that the tumor extends into or abuts the adjacent lobes (e.g., "Isthmic nodule present in blocks from Right and Left lobes"). The LLM interprets this physical presence in both lobes as "Bilateral," while the Gold Standard classifies it by the epicenter (Isthmus).

*   **Nature of Error:** Semantic Interpretation (Center of Mass vs. Physical Extent).
*   **Frequency:** Moderate.
*   **Evidence:**
    *   **Case TCGA-MK-A4N7:**
        *   *Report:* Diagnosis says "Tumor Laterality: **Isthmic**." However, Gross Description says: "Specimen bisected... blocks 1-8 right... blocks 9-14 left... nodule present in blocks 5-8 [Right]... nodule present in blocks 12-14 [Left]."
        *   *LLM Output:* **Bilateral** (120bold) or **Right Lobe** (120b - likely confused by Gross description headers).
        *   *Gold Standard:* **Isthmus**.
        *   *Analysis:* The LLM was likely triggered by the presence of tumor in tissue blocks explicitly labeled "Right" and "Left."

#### Code 3: Tissue Entity Attribution (Node vs. Lobe)
**Definition:** The patient has a tumor in one thyroid lobe and metastatic carcinoma in a *lymph node* on the contralateral side. The LLM extracts the location of the metastatic lymph node ("Right level 3") and incorrectly attributes it to the *thyroid gland* ("Right lobe"), triggering the Bilateral rule.

*   **Nature of Error:** Contextual Extraction (Failing to distinguish Neck Dissection contents from Thyroid contents).
*   **Frequency:** Low.
*   **Evidence:**
    *   **Case TCGA-EM-A2P1:**
        *   *Report:* "Widely invasive papillary carcinoma... **Left**... Metastatic papillary thyroid carcinoma... Lymph nodes (bilateral neck)... Lymph node, 1 of 1 (**right level III**)."
        *   *LLM Output:* **Bilateral**.
        *   *Gold Standard:* **Left lobe**.
        *   *Analysis:* The LLM saw "Carcinoma" + "Left" (Thyroid) and "Carcinoma" + "Right" (Lymph Node) and conflated the anatomical boundaries, assuming the Right-sided disease was intralobar rather than nodal.

### Summary Table

| Error Code | Description | Logic | Example ID |
| :--- | :--- | :--- | :--- |
| **Micro-1** | **Rule-Induced Over-Sensitivity** | LLM includes contralateral microcarcinoma as "Bilateral"; Gold Standard ignores it. | TCGA-DJ-A13M |
| **Anat-2** | **Anatomical Contiguity** | Tumor centered in Isthmus extends physically into lobes; LLM calls it Bilateral. | TCGA-MK-A4N7 |
| **Ent-3** | **Tissue Attribution** | LLM confuses contralateral lymph node metastasis for contralateral thyroid tumor. | TCGA-EM-A2P1 |

### Conclusion for `tumor_site`
The 120B models demonstrate high semantic fidelity (they are reading the text correctly). The majority of errors are not "hallucinations" but are caused by the **Strict Logic Adherence** of the LLM to the provided prompt ("Check for ANY carcinoma"), which conflicts with the implicit exclusion criteria used by human abstractors creating the Gold Standard (who exclude microcarcinomas when determining site).

---

Here is the error analysis for **Tumor Size**.

This variable is unique because it requires the LLM to perform three distinct cognitive steps: **Extraction** (finding numbers), **Attribution** (linking numbers to the correct object), and **Prioritization** (selecting the correct number based on a hierarchy of sources).

The errors for `tumor_size` fall into three distinct categories.

### 1. Source Hierarchy Conflict (The "Right Number, Wrong Section" Error)
**Definition:** The pathology report contains conflicting measurements for the tumor in different sections (e.g., the *Final Diagnosis* header lists one size, while the *Synoptic Report* or *Gross Description* lists another). The Prompt established a hierarchy (Synoptic > Gross), but the LLM and the Gold Standard disagreed on which source was "authoritative" in edge cases.

*   **Evidence:**
    *   **TCGA-DE-A0Y2:**
        *   **Gold:** 2.4 cm | **LLM:** 2.3 cm
        *   **Context:** The *Final Diagnosis* states "Tumor size: 2.3 cm." However, the *Synoptic Report* lists dimensions as "2.4 x 2.2 x 1.3 cm."
        *   **Analysis:** The LLM prioritized the explicit statement in the Diagnosis header. The Gold Standard prioritized the largest dimension found in the Synoptic table. Both are "correct" interpretations of the text, but resulted in a mismatch.
    *   **TCGA-DJ-A1QL:**
        *   **Gold:** 2.1 cm | **LLM:** 2.2 cm
        *   **Context:** *Final Diagnosis* says "Greatest diameter is 2.2 cm." *Gross Description* says "mass... measuring 2.1 x 1.8 x 1.8 cm."
        *   **Analysis:** The LLM followed the prompt's instruction to prioritize the Diagnosis. The Gold Standard appears to have derived the value from the Gross Description.

### 2. Entity Attribution Error (The "Wrong Object" Error)
**Definition:** The LLM successfully extracted a measurement, but it belonged to the wrong clinical entity. This occurred most frequently when the report described the dimensions of the **Thyroid Lobe** or a **Benign Nodule** in close proximity to the malignant tumor description.

*   **Evidence:**
    *   **TCGA-EL-A3GQ:**
        *   **Gold:** 4.0 cm | **LLM:** 1.3 cm
        *   **Context:** The report describes a large 4.0 cm mass (Gold). However, there is likely a secondary focus or a specific tissue slice measurement of 1.3 cm that the LLM latched onto.
    *   **TCGA-EL-A3ZL:**
        *   **Gold:** 4.0 cm | **LLM:** 1.5 cm
        *   **Context:** The report likely lists the *Lobe* dimensions or a *Benign* nodule near the tumor. The LLM failed to semantically link the measurement to the "Carcinoma" label, defaulting to the nearest available measurement string.

### 3. Rule Over-Application (The "Exception" Error)
**Definition:** The prompt included a complex exception rule: *Trust Synoptic Data UNLESS the diagnosis says 'Microcarcinoma' but Gross Description measures it >1cm.* The LLM occasionally applied this "override" logic incorrectly, favoring the Gross Description even when the "Microcarcinoma" trigger condition was not met.

*   **Evidence:**
    *   **TCGA-FY-A3R9:**
        *   **Gold:** 0.7 cm | **LLM:** 1.0 cm
        *   **Context:** The *Synoptic Report* explicitly lists "Greatest dimension: 0.7 cm". However, the *Gross Description* mentions a nodule that "inferiorly measures 1.0 cm."
        *   **Analysis:** The Gold Standard accepted the Synoptic summary (0.7). The LLM likely detected a discrepancy, prioritized the larger value found in the text (1.0), and assumed the "Exception Rule" applied, resulting in a mismatch.

### Summary of Error Codes for `tumor_size`

| Error Code | Description | Frequency |
| :--- | :--- | :--- |
| **HIERARCHY** | LLM selected a valid tumor measurement from the Diagnosis/Gross section, but Gold Standard used Synoptic (or vice versa). | High |
| **ATTRIBUTION** | LLM measured the wrong entity (e.g., Lobe size vs. Tumor size). | Moderate |
| **LOGIC_OVERRIDE** | LLM applied the "Microcarcinoma Exception" rule too aggressively, favoring Gross text over Synoptic tables. | Low |