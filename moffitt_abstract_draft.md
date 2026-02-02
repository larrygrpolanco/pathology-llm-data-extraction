### 1. Abstract Draft

**Title:** **Aligning Large Language Models with Human Curation Logic: Quantifying the Impact of Implicit Abstraction Rules in Retrospective Cancer Research**
or
**Aligning Large Language Models with Human Abstraction Heuristics: Decoding Implicit Rules in Retrospective Oncology Data**

**Authors:** [Your Name]*, [Co-Authors], [Mentor]+
**Affiliations:** 1. [Your Dept], 2. [Other Dept]

**BACKGROUND**
In retrospective oncology research, converting unstructured pathology text into structured databases is a critical but labor-intensive task. While Large Language Models (LLMs) offer a scalable solution for automation, initial validations often reveal discrepancies between LLM outputs and manually curated "Gold Standards." We propose that these mismatches often stem not from model hallucinations, but from the implicit choices human abstractors make regarding ambiguous data, edge cases, and variable definitions. When an LLM extracts data literally, it lacks the context of the specific "business logic" or curation protocols used by the original human team. This study aims to demonstrate that aligning LLM prompts with these inferred curation heuristics—effectively providing the model with a "Standard Operating Procedure" (SOP)—significantly improves agreement with legacy datasets.

**METHODS**
We analyzed a development set of 103 thyroid carcinoma pathology reports from the TCGA-THCA dataset, comparing them against the corresponding GDC Clinical Data Resource (the human-curated Gold Standard). Using an open-weights model (GPT-OSS-120B) to simulate a secure local environment, we conducted a comparative analysis of two prompting strategies:
1.  **Baseline Semantic Extraction:** The model was instructed to extract clinical findings exactly as stated in the text (e.g., recording specific histologic subtypes or minor microscopic findings).
2.  **Pragmatic Alignment Extraction:** The model was provided with a specific set of abstraction rules derived from an initial error analysis of the Gold Standard. These rules instructed the model to mimic observed human curation habits, such as mapping descriptive histologic variants to broader categories (e.g., classifying "oncocytic variant" as "Classical") and prioritizing disease extent (e.g., "Bilateral") over index tumor location.
We evaluated performance across five variables: Histologic Variant, Tumor Site, Extrathyroidal Extension, Margins, and Tumor Size.

**RESULTS**
The Baseline Semantic model achieved an overall accuracy of ~86%, with frequent divergences in categorical variables. Error analysis revealed that the model was often "factually" correct based on the text, but "operationally" incorrect based on the dataset's specific schema.
Implementing the Pragmatic Alignment prompt significantly reduced these discrepancies. For **Tumor Site**, agreement improved by instructing the model to prioritize "Bilateral" status over the location of the dominant nodule, reconciling a key definition mismatch. For **Histologic Variant**, accuracy increased by enforcing a stricter hierarchy that filtered out non-standard subtypes often described in free text but not captured in the registry. Preliminary results suggest that defining explicit handling rules for edge cases (e.g., microscopic extrathyroidal extension in large tumors) further aligns LLM output with human curation.

**CONCLUSIONS**
This study highlights that "accuracy" in data abstraction is relative to the specific rules of the project. Human-curated datasets contain inherent decision-making patterns that purely semantic LLM extraction will miss. To successfully integrate LLMs into research workflows, we must move beyond simple extraction prompts and develop "Aligned Prompts" that encode the project's specific inclusion, exclusion, and simplification criteria. These findings emphasize the necessity of the "Human in the Loop" to define the logic that the model executes.

---
