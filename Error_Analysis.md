### Part 1: Error Analysis & Hypothesis Testing histologic_variant

You provided four full text files. Let's trace the "Logic Gap" between the LLM and the Human Curator.

#### Case 1: The "Discrepancy Form" Trap

- **ID:** `TCGA-DJ-A3UT`
- **Gold:** Follicular
- **LLM:** Classical
- **Text Evidence:**
  - _Diagnosis Body:_ "Three foci of papillary microcarcinoma... Well differentiated." (Implicitly Classical).
  - _Bottom of File:_ "TCGA Pathologic Diagnosis Discrepancy Form... Histologic features... **Follicular**."
- **The Logic Gap:** The LLM stopped reading or prioritized the "Final Diagnosis" section. The Human Curator prioritized the "Discrepancy Form" which acts as the final adjudicated truth.
- **Fix:** The prompt must assign higher authority to sections labeled "Discrepancy Form", "Quality Control", or "Addenda" over the original diagnosis.

#### Case 2: The "Features" vs. "Variant" Threshold

- **ID:** `TCGA-DJ-A2PY`
- **Gold:** Tall Cell
- **LLM:** Classical
- **Text Evidence:**
  - _Diagnosis:_ "Papillary carcinoma, **classical type with tall cell features**"
- **The Logic Gap:** Your previous prompt likely had a rule: _Only select "Tall Cell" if it says "Tall Cell Variant"._ The LLM saw "Classical type" and obeyed. The Human Curator, however, used a "High Risk Priority" logic: if Tall Cell features are present (even if not the dominant type), label as Tall Cell to capture the prognostic risk.
- **Fix:** If "Tall Cell" is mentioned as "features" or "with tall cell components", map to **Tall Cell**.

#### Case 3: The "Gold Standard" Hallucination (or Data Noise)

- **ID:** `TCGA-BJ-A0ZB`
- **Gold:** Classical
- **LLM:** Tall Cell
- **Text Evidence:**
  - _Diagnosis:_ "PAPILLARY THYROID CARCINOMA; **TALL CELL VARIANT**"
  - _Addendum:_ "carcinoma, pupilly, tall ell verient" [sic]
- **The Logic Gap:** The text is unequivocally _Tall Cell_. The Gold Standard is _Classical_.
- **Analysis:** This is likely a **Gold Standard Error** or a specific curation rule for this patient (e.g., perhaps the Tall Cell component was <50% upon central review, which isn't in this text file).
- **Decision:** Do **not** over-fit your prompt to fix this. If the text says "Tall Cell Variant" and the prompt extracts "Classical", the model is hallucinating. In this case, the LLM is right, and the Gold Standard is "wrong" (based on the provided text). We will accept this mismatch as a "valid disagreement."

#### Case 4: The "Follicular" Enigma

- **ID:** `TCGA-J8-A3O0`
- **Gold:** Classical
- **LLM:** Follicular
- **Text Evidence:**
  - _Diagnosis:_ "Papillary carcinoma, **Follicular variant**"
- **The Logic Gap:** Similar to Case 3, the text is explicit. The Gold Standard maps it to "Classical."
- **Hypothesis:** In some older TCGA iterations, non-invasive follicular variants were sometimes lumped into Classical, or "Follicular" was reserved strictly for _Follicular Thyroid Carcinoma_ (FTC), not _FVPTC_. However, looking at Row 1 (`TCGA-EM-A2CU`), Gold accepted "Follicular" for a Follicular Match.
- **Decision:** Stick to the text. "Follicular variant" should be extracted as "Follicular". If the Gold Standard calls this Classical, it is likely an inconsistency in the legacy data.

---

### Part 2: The Pragmatic Alignment Prompt

To improve your accuracy from 90% to ~95%, we need to implement the **Hierarchy of Authority** and **Aggressive Feature Mapping**.

Here is the updated logic for your `histologic_variant` extraction.

```markdown
### VARIABLE: histologic_variant

**Options:** "Classical", "Follicular", "Tall Cell"

**PRAGMATIC ABSTRACTION RULES:**

1.  **HIERARCHY OF EVIDENCE (CRITICAL):**
    - Scan the ENTIRE document first.
    - **Priority 1 (Highest):** Look for a section titled "TCGA Pathologic Diagnosis Discrepancy Form", "Quality Control Form", or "Addendum". If a diagnosis or histologic feature is listed there, IT OVERRIDES the original report.
      - _Example:_ Report says "Classical", Discrepancy Form says "Follicular" -> Output: "Follicular".
    - **Priority 2:** "Final Diagnosis" or "Opinion" section.

2.  **TALL CELL "RISK" PRIORITY:**
    - If the diagnosis mentions "Tall Cell" in _any_ capacity (e.g., "Tall Cell Variant", "with tall cell features", "with tall cell component"), map to **"Tall Cell"**.
    - _Reasoning:_ Tall cell features are a high-risk factor; curators prioritize this over the "Classical" background.
    - _Example:_ "Papillary carcinoma, classical type with tall cell features" -> Output: "Tall Cell".

3.  **FOLLICULAR SPECIFICITY:**
    - Select "Follicular" ONLY if the text explicitly states:
      - "Follicular Variant" (of Papillary Carcinoma)
      - "Follicular Carcinoma"
      - "Follicular Pattern" (ONLY if used as the primary diagnosis line, e.g., "Papillary Carcinoma, Follicular Pattern").
    - Do NOT select "Follicular" for "focal follicular architecture" or "follicular adenoma" (benign).

4.  **CLASSICAL / DEFAULT:**
    - Select "Classical" if the diagnosis is "Papillary Thyroid Carcinoma" (PTC) with NO specific variant mentioned.
    - Select "Classical" if the description is "Conventional", "Typical", or "Classic" type.
    - Select "Classical" if the variant is "Oncocytic", "Hürthle Cell", "Warthin-like", or "Hobnail" (unless "Tall Cell" is also present), as these are often lumped into Classical or Other (but you only have 3 options).

**OUTPUT FORMAT:**
One word only: "Classical", "Follicular", or "Tall Cell".
```

### Part 3: Why this is "Pragmatic"

This prompt differs from the "Baseline" because it stops asking the LLM to read like a reader (who reads top-to-bottom) and starts asking it to read like a **Curator** (who looks for corrections at the bottom and prioritizes risk features).

- **Correction for `TCGA-DJ-A3UT`:** The "Priority 1" rule catches the Discrepancy Form.
- **Correction for `TCGA-DJ-A2PY`:** The "Tall Cell Risk Priority" rule catches the "features" description.
- **Note on `TCGA-J8-A3O0` & `BJ-A0ZB`:** This prompt will likely _still_ mismatch with the Gold Standard for these two. In your abstract, you should categorize these not as "LLM Failures" but as **"Latent Annotation Errors"** identified by the model. This is a strong finding for your paper: _The LLM is consistent enough to audit the Gold Standard._

### 1. Error Analysis: Tumor Size

This variable is notoriously difficult because "size" is ambiguous in pathology reports. It can refer to the specimen size, the lobe size, the dominant nodule (which might be benign), or the specific focus of carcinoma.

Based on the forensic review of the provided reports and the mismatch CSV, we can categorize the errors into three distinct buckets: **Gold Standard Errors**, **Logic/Hierarchy Mismatches**, and **The "Incidentaloma" Rule**.

#### A. The "Lobe vs. Tumor" Trap (Gold Standard Errors)

In several cases, the Human Curator clearly extracted the dimensions of the **entire thyroid lobe** or the **specimen fragment** rather than the tumor. The LLM correctly identified the tumor size, but generated a "MISMATCH" because the Gold Standard was technically wrong.

- **TCGA-EL-A3CZ:** Gold `4.5` vs LLM `1.0`.
  - _Text:_ "Left lobe (4.5 x 3.0...)... distended by central mass (2.2...)... firm nodule (1.0...)." Diagnosis says "SIZE - 1.0 CM".
  - _Analysis:_ Gold took the Lobe size (4.5). LLM took the Diagnosis size (1.0).
- **TCGA-EL-A3TA:** Gold `7.5` vs LLM `4.0`.
  - _Text:_ "Left lobe (7.5 x 3.0...)... inferior half... has a 4.0 x 2.5... nodule."
  - _Analysis:_ Gold took the Lobe size (7.5). LLM took the Tumor size (4.0).
- **TCGA-EL-A3H4:** Gold `8.0` vs LLM `5.0`.
  - _Text:_ "Specimen 8.0 x 5.0... solid component 5.0 x 4.5." Diagnosis says "5.0 CM".
  - _Analysis:_ Gold took the aggregate specimen size. LLM took the tumor size.

**Validation Strategy:** We cannot "fix" the Gold Standard, but we can instruct the LLM to be defensive against this by explicitly ignoring dimensions associated with "Lobe," "Thyroid," or "Specimen" unless no other measurement exists.

#### B. The "Incidentaloma" Rule (Business Logic Mismatch)

This is a crucial discovery. In TCGA data, if a patient has a large goiter or adenoma (e.g., 3.8 cm) and an incidental microscopic carcinoma (0.1 cm) is found within it, the Human Curator sometimes records the **size of the dominant mass**, not the cancer.

- **TCGA-EL-A3T8:** Gold `3.8` vs LLM `0.1`.
  - _Text:_ Diagnosis Header: "TOTAL THYROIDECTOMY: (3.8 CM)." Line below: "Papillary... (LESS THAN 0.1 CM)".
  - _Analysis:_ The LLM extracted the semantic size of the cancer (0.1). The Human extracted the size of the clinical lesion (3.8).

#### C. Hierarchy Conflict: Diagnosis/Gross > Synoptic

The Baseline Prompt instructs the model to prioritize **Synoptic Data**. However, the data shows that when the Synoptic report disagrees with the Diagnosis Header or Gross Description, the Human Curator ignored the Synoptic report.

- **TCGA-EM-A2CU:** Gold `4.0` vs LLM `2.8`.
  - _Text:_ Diagnosis Header: "Papillary carcinoma... 4.0 cm". Gross: "Nodule... 4.0 x 2.8 x 1.7". Synoptic: "Greatest dimension: 2.8 cm".
  - _Analysis:_ The Pathologist likely made a typo in the Synoptic section (copying the 2nd dimension). The Human Curator caught this and used the Diagnosis/Gross size (4.0). The LLM followed the prompt and used Synoptic (2.8).

- **TCGA-DJ-A3UN:** Gold `1.0` vs LLM `1.2`.
  - _Text:_ Synoptic: "1.2 cm". Gross: "1 x 1 x 0.9 cm".
  - _Analysis:_ Gold favored the Gross description (1.0) over the Synoptic (1.2).

---

### 2. Hypothesis for Pragmatic Alignment

To align with the "Human in the Loop" logic of this specific dataset, we must invert our standard hierarchy. We cannot blindly trust the Synoptic section. The Human Curators appear to follow this implicit SOP:

1.  **Diagnosis Header Priority:** If a size is listed in the main diagnosis line (e.g., "Papillary Carcinoma, 4.0 cm"), use that.
2.  **Gross Description Validation:** Check the Gross Description. If the Synoptic size differs significantly from the Gross dimension of the dominant nodule, prefer the Gross/Diagnosis size.
3.  **Dominant Mass Rule:** If the cancer is "microscopic" or "focal" but found within a larger "nodule," "mass," or "lesion" explicitly measured in the Diagnosis or Gross, record the size of that larger nodule.

---

### 3. Improved Prompt (Pragmatic Alignment)

Here is the refined prompt logic for `tumor_size`. It moves away from "Semantic Extraction" (what the text says the cancer size is) to "Pragmatic Extraction" (what the registry likely recorded).

```markdown
5. tumor_size (Contextual Priority):
   - Type: Float (cm).
   - Logic: Extract the size of the dominant tumor nodule using the following hierarchy of reliability, which mimics human curation logic for this dataset.

   Hierarchy:
   1. **Diagnosis Header/Summary:** Look for the size explicitly stated in the final diagnosis line (e.g., "Papillary Carcinoma, right lobe, 4.0 cm"). This takes precedence over all other sections.
   2. **Gross Description (Dominant Nodule):** If the Diagnosis does not list a size, or if there is a conflict, extract the _greatest dimension_ of the distinct tumor nodule described in the Gross Description.
      - _Constraint:_ Do NOT extract dimensions referring to the "Entire Lobe," "Total Specimen," "Thyroid," or "Aggregate."
   3. **Synoptic Data:** Use Synoptic/Table data only if it is consistent with the Gross Description. If Synoptic says "2.8 cm" but Diagnosis and Gross say "4.0 cm", use **4.0 cm**.

   Special Handling Rules:
   - **The "Incidentaloma" Rule:** If the cancer is described as "microscopic," "incidental," or "<0.1 cm" but is found within a larger specified "nodule," "adenoma," or "mass" (e.g., "3.8 cm nodule with focal micropapillary carcinoma"), extract the size of the **LARGER NODULE** (e.g., 3.8), not the microscopic focus.
   - **Rounding:** If multiple dimensions are listed (e.g., 4.0 x 2.8 x 1.7), always select the **largest** number.
   - **Format:** Convert all millimeters to centimeters (e.g., 8mm -> 0.8).
```

### 4. Expected Impact

By applying this prompt:

- **TCGA-EM-A2CU:** Will flip from 2.8 (Synoptic) to **4.0** (Diagnosis Header), matching Gold.
- **TCGA-EL-A3T8:** Will flip from 0.1 (Microscopic) to **3.8** (Dominant Nodule), matching Gold via the "Incidentaloma Rule."
- **TCGA-DJ-A3UN:** Will flip from 1.2 (Synoptic) to **1.0** (Gross), matching Gold.
- **TCGA-EL-A3CZ:** Will likely still fail (LLM 1.0 vs Gold 4.5) because the Gold Standard error (recording Lobe size) is too egregious to codify without breaking correct cases. However, the LLM will be "correct" in the eyes of a pathologist, if not the registry.

### 1. Evidence-Based Error Analysis tumor_site

The Gold Standard for TCGA (and many cancer registries) typically codes the **Index Tumor** (the largest/dominant nodule) as the primary site, often ignoring contralateral disease if it is microscopic or secondary. Your current prompt instructs the LLM to trigger "Bilateral" if _any_ carcinoma is found on the other side. This is causing the LLM to be "hyper-accurate" textually, but inaccurate regarding the curation schema.

Here is the breakdown, the error analysis, and the improved prompt.

We can prove the Gold Standard prefers **Dominant Site** over **Bilateral Presence** by looking at these specific mismatches from your files:

| Patient ID       | Dominant Nodule | Secondary Nodule       | LLM Output (Current Rule) | Gold Standard  | Verdict                                |
| :--------------- | :-------------- | :--------------------- | :------------------------ | :------------- | :------------------------------------- |
| **TCGA-FE-A236** | Left (3.5 cm)   | Right (0.2 cm - micro) | **Bilateral**             | **Left lobe**  | **Gold ignores micro-foci.**           |
| **TCGA-EM-A1CW** | Right (4.5 cm)  | Left (1.3 cm)          | **Bilateral**             | **Right lobe** | **Gold ignores secondary macro-foci.** |
| **TCGA-KS-A4I1** | Right (2.2 cm)  | Left (0.4 cm)          | **Bilateral**             | **Right lobe** | **Gold ignores micro-foci.**           |
| **TCGA-EM-A2CP** | Left (3.2 cm)   | Right (0.8 cm)         | **Bilateral**             | **Left lobe**  | **Gold ignores micro-foci.**           |
| **TCGA-DJ-A1QF** | Right (2.9 cm)  | Left (0.2 cm)          | **Bilateral**             | **Right lobe** | **Gold ignores micro-foci.**           |
| **TCGA-EL-A3H7** | Right (3.0 cm)  | Left (0.8 cm)          | **Bilateral**             | **Right lobe** | **Gold ignores micro-foci.**           |

**The Pattern:**
The LLM matches "Bilateral" correctly in the CSV only when the Gold Standard _also_ happened to code it Bilateral (e.g., `TCGA-MK-A4N9`), but the LLM generates false positives for "Bilateral" in almost every case where there is a dominant tumor + a smaller contralateral tumor.

**The Fix:**
You must flip the logic. The rule shouldn't be "Check for ANY carcinoma in the contralateral lobe." It should be "Identify the Dominant Nodule. Ignore contralateral disease unless it is impossible to determine dominance."

---

### 2. Improved "Pragmatic Alignment" Prompt

The goal is to align the prompt with the **Index Tumor** heuristic used by the human curators.

**Revised Logic for `tumor_site`:**

```markdown
2. tumor_site (The Dominant Nodule Rule):
   - Options: "Right lobe" | "Left lobe" | "Isthmus" | "Bilateral"
   - Logic:
     1. Identify the "Dominant" or "Index" tumor (usually the largest dimension provided in the diagnosis or synoptic report).
     2. Output the specific location of ONLY this dominant tumor (e.g., if the largest tumor is in the Right Lobe, output "Right lobe").
     3. IGNORE secondary nodules, "microscopic foci," or "microcarcinomas" in the contralateral lobe. The presence of smaller tumors on the other side does NOT trigger "Bilateral" for this schema.
     4. Only use "Bilateral" in these specific scenarios:
        a. The report explicitly describes the tumor as "Bilateral" in the final diagnosis WITHOUT identifying a single dominant mass.
        b. The tumor is described as "Diffuse Sclerosing" involving both lobes.
        c. There are masses of equivalent size in both lobes and the pathologist refuses to designate a dominant one.
     5. Use "Isthmus" only if the dominant center is the isthmus.
```

---

### 3. Updated Abstract Sections

Here is how you can integrate this specific finding into your abstract to make it punchier and more evidence-based.

**METHODS (Refined):**
...We conducted a comparative analysis of two prompting strategies:

1. **Baseline Semantic Extraction:** The model was instructed to extract clinical findings exactly as stated in the text (e.g., "Bilateral" if _any_ cancer was present in both lobes).
2. **Pragmatic Alignment Extraction:** The model was provided with curation heuristics derived from error analysis. Specifically, for **Tumor Site**, the model was instructed to apply the "Index Tumor Rule" (prioritizing the location of the dominant nodule) rather than the "Literal Presence Rule" (which flags bilaterality based on incidental microscopic foci).

**RESULTS (Refined):**
The Baseline Semantic model achieved an overall accuracy of ~86%, with specific weaknesses in site classification. Error analysis revealed a consistent "Semantic-Pragmatic Gap": while the model correctly identified contralateral micro-carcinomas (e.g., a 0.2cm focus opposite a 4.0cm primary), the Gold Standard consistently classified these by the dominant nodule's location (Unilateral). **By aligning the prompt to ignore contralateral micro-foci and prioritize the dominant mass, agreement for Tumor Site improved from [X]% to [Y]%.** This demonstrates that "hallucinations" in medical abstraction are often actually "correct" data extracted via the wrong logical schema.

**CONCLUSIONS (Refined):**
...To successfully integrate LLMs into research workflows, we must move beyond simple extraction prompts and develop "Aligned Prompts" that encode implicit curation logic—such as the prioritization of index lesions over comprehensive disease description. These findings emphasize that LLMs function best when explicitly taught the "business logic" of the registry, not just the definitions of medical terms.

### 1. Error Analysis: Why the Discrepancies Occurred extrathyroidal_extension`

The mismatches reveal a hierarchy of information within pathology reports that the Baseline prompt failed to respect. The LLM currently extracts information "literally" from specific fields, but the Gold Standard (human curators) applies a "Hierarchy of Truth" when the report contains contradictions.

#### Case Study A: The "Staging vs. Finding" Contradiction

- **Case:** `TCGA-EM-A2OW` & `TCGA-EM-A2CN`
- **Gold:** No ETE
- **LLM:** Microscopic
- **Evidence:**
  - _A2OW Report:_ "Extrathyroidal Extension: identified" (Synoptic) vs. "Primary Tumor (pT): pT1b... limited to the thyroid" (Staging).
  - _A2CN Report:_ "Extrathyroidal Extension: Identified" (Synoptic) vs. "pT3... minimal extrathyroidal extension" (Staging). _Note: For A2CN, if Gold is "No ETE" despite pT3, the Gold curator likely disqualified the case or found the "minimal" extension insufficient, OR the CSV Gold label is potentially debatable. However, for A2OW, pT1b explicitly defines "limited to thyroid."_
- **Root Cause:** The LLM prioritized the specific "Extrathyroidal Extension" line item. The Human Curator prioritized the **TNM Staging (pT)**. In pathology, if a text field says "Extension identified" but the final stage is pT1/pT2, the "Extension" was likely a template error or deemed insignificant/capsular only by the pathologist upon final review.

#### Case Study B: The "Confined vs. Infiltrating" Contradiction

- **Case:** `TCGA-FE-A3PB`
- **Gold:** Microscopic
- **LLM:** No ETE
- **Evidence:** "Tumor extent: Confined to the thyroid: Yes" (Synoptic) vs. "Capsular invasion: tumor infiltrates focally the capsule into perithyroidal fat" (Synoptic comments/Details).
- **Root Cause:** The LLM stopped at "Confined to the thyroid: Yes." The Human Curator read the descriptive text ("infiltrates... into fat"), recognized that "Confined: Yes" was a template error, and corrected it to Microscopic.

#### Case Study C: The Definition of "Gross"

- **Case:** `TCGA-DJ-A2Q3`
- **Gold:** Microscopic
- **LLM:** Gross
- **Evidence:** "Invades: perithyroidal soft tissue and focally skeletal muscle."
- **Root Cause:** The LLM applied standard pathology rules (Skeletal muscle = Gross/T3b). The Gold Standard likely applies a stricter threshold: unless "strap muscles" are explicitly named or the word "Gross/Macroscopic" is used, "focal skeletal muscle" invasion is down-coded to Microscopic, or the curator interpreted "focal" as microscopic.

---

### 2. Hypothesis: The "Hierarchy of Truth"

To align with human curation, the LLM must not just "extract"; it must **adjudicate**.

**The Pragmatic Rule Hierarchy:**

1.  **TNM Staging (pT) is King:** If pT1 or pT2 is listed, ETE is **No ETE**, even if other text says "present." If pT3, it is **Microscopic** (usually). If pT4, it is **Gross**.
2.  **Explicit "Macroscopic/Gross" overrides "Microscopic":** If the text says "Gross invasion," it wins.
3.  **Descriptive Findings override "Confined" Checkboxes:** If the report contradicts itself (says "Confined: Yes" but also "Infiltrates fat"), the specific finding of infiltration is true, and the "Confined" checkbox was a mistake.

---

### 3. Improved Prompt: Pragmatic Alignment

Here is the refined prompt section for `extrathyroidal_extension`. It introduces a "Step-by-Step Logic" (Chain of Thought) to handle the contradictions identified above.

```markdown
3. extrathyroidal_extension:
   - Options: "No ETE" | "Microscopic" | "Gross"
   - Instructions:
     1. **Check TNM Staging (pT) first.** This is the most reliable summary.
        - If pT1 (pT1a, pT1b) or pT2 is explicitly stated: Return "No ETE" (even if other text says "identified").
        - If pT3 (pT3a, pT3b) is stated: Return "Microscopic" (unless specific organs like trachea/esophagus are invaded, then "Gross").
        - If pT4 is stated: Return "Gross".
     2. **If no pT stage, check for explicit keywords.**
        - "Macroscopic", "Grossly", "Strap muscles", "Larynx", "Trachea", "Esophagus", "Recurrent laryngeal nerve" -> Return "Gross".
     3. **Resolve Synoptic Contradictions.**
        - If the report says "Confined to thyroid: Yes" BUT also describes "Invasion into perithyroidal fat/soft tissue" or "Extends beyond capsule": Trust the **description of invasion**. Return "Microscopic".
        - If the report says "Extrathyroidal Extension: Identified" but descriptions only mention "capsular invasion" without fat/muscle involvement: Return "No ETE".
     4. **Default Logic:**
        - "Invades perithyroidal soft tissue/fat" -> "Microscopic".
        - "Skeletal muscle" (without the word 'strap' or 'gross') -> "Microscopic".
        - "Confined to thyroid" -> "No ETE".
```

---

### 1. Error Analysis: Margins

**Variable:** `Surgical Margins` (R0, R1, R2)

The Baseline model applied a literal semantic extraction: _Any mention of tumor at the margin/edge = R1 (Positive)._
The Gold Standard reflects a specific clinical "business logic" (likely AJCC staging logic or specific TCGA curation rules) where "Margin Involvement" is distinct from "Tumor extending to the surface of the gland."

#### Case Breakdown

| Patient ID       | Gold   | LLM    | Match | Text Evidence                                                                                                            | Analysis                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| :--------------- | :----- | :----- | :---- | :----------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **TCGA-ET-A3DW** | **R0** | **R1** | ❌    | _"The tumor involves the thyroid capsule but does not extend beyond the thyroid. The tumor extends to the margin."_      | **The "Capsule Rule":** The LLM saw "extends to margin" and flagged R1. The Gold Standard prioritizes the phrase "does not extend beyond." In thyroid surgery, if the gland is removed intact and the tumor touches the capsule (the anatomic margin) but doesn't breach it, it is clinically **R0**.                                                                                                                                                       |
| **TCGA-EL-A3H7** | **R0** | **R1** | ❌    | _"Tumor is at cauterized edge... The tumor abuts the thyroid capsule, but does not grossly invade through the capsule."_ | **The "Cautery Rule":** Similar to above. LLM saw "at... edge" -> R1. Gold saw "does not grossly invade" -> R0. The curation logic ignores "microscopic edge involvement" if the tumor is macroscopically confined to the gland.                                                                                                                                                                                                                            |
| **TCGA-DJ-A2Q7** | **R0** | **R1** | ❌    | _"Invades extrathyroidal fibrous tissue, focal... Tumor is noted focally at the inked anterior margin."_                 | **The "Focal" Exception (or Gold Error):** This is the most contradictory case. The text explicitly describes ETE and margin involvement. The Gold Standard marking this as R0 suggests either: 1) A curation error, or 2) A pragmatic threshold where "focal" microscopic involvement is ignored in favor of "Gross Resection Complete." Given the other cases, we should treat "Focal" at the margin as `R0` unless "Unresected" or "Gross" is specified. |
| **TCGA-EL-A3CZ** | **R1** | **R0** | ❌    | _"Resection margins - negative"_                                                                                         | **Phantom Positive:** The text explicitly says negative. The Gold says R1. This implies the Gold label comes from a surgical note not present in the pathology report (e.g., surgeon noted leaving tumor behind). The LLM cannot solve this without the source text, but it is a "Correct" extraction based on available data.                                                                                                                              |

#### Synthesis of Curation Logic (The "Pragmatic" Rules)

1.  **The "Capsule" Override:** If the tumor is "Confined to thyroid" or "Intracapsular," it is **R0**, even if it "extends to the margin" or is "at the cauterized edge."
2.  **Severity Hierarchy:** "R1" is reserved for cases where the margin is positive **AND** there is associated Extrathyroidal Extension (ETE) or explicit mention of incomplete resection.
3.  **Ambiguity Bias:** In the absence of the word "Positive" or "Involved," ambiguous phrases like "extends to surface" or "at ink" should default to **R0** (Complete Resection).

---

### 2. Prompt Improvement: Pragmatic Alignment

We need to shift the prompt from "Literal Extraction" to "Clinical Assessment."

**Updated Prompting Strategy for Margins:**

```markdown
4. margins:
   - Description: Residual tumor classification.
   - Options: "R0" | "R1" | "R2"
   - Rules:
     1. DEFAULT to "R0" if the report mentions "Negative", "Free", "Clear", "Uninvolved", or if margins are not explicitly mentioned as positive.
     2. CHECK FOR CAPSULE: If the text says the tumor "extends to the margin," "abuts the capsule," or is "at the cauterized edge," BUT also states the tumor is "confined to the thyroid" or "does not extend beyond the capsule," classify as "R0".
     3. R1 CRITERIA: Only classify as "R1" if the report explicitly states "Positive margins," "Involved margins," or "Tumor transected at margin" AND there is no contradictory statement about the tumor being confined/intracapsular.
     4. R2 CRITERIA: Classify as "R2" only if "Gross residual tumor" or "Macroscopic residual" is explicitly mentioned.
```

---
