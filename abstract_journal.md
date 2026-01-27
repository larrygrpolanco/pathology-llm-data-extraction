# Abstract: 2026 Moffitt Scientific Symposium

**Title**: Evaluating the Generalizability of Large Language Models for Automated Pathology Data Abstraction in Thyroid Cancer

**Authors**: Larry Polanco*, [Moffitt Faculty Name]+
*Presenting Author; +Faculty Mentor

---

### BACKGROUND

Manual abstraction of discrete data points from pathology reports is a resource-intensive bottleneck in oncology research and registry maintenance. While Large Language Models (LLMs) have shown high accuracy in standardized benchmarks, their generalizability to varied institutional reporting formats and the performance tradeoffs across model scales (7B to 70B+ parameters) remain inadequately characterized. This study aims to evaluate the accuracy of multi-scale LLMs in extracting critical thyroid cancer prognostic elements from a large-scale public dataset.

### METHODS

We developed an automated pipeline to extract 9 key pathology data points (e.g., histologic variant, tumor size, extrathyroidal extension, and margin status) from 507 thyroid cancer pathology reports in The Cancer Genome Atlas (TCGA-THCA) database. A gold-standard dataset was established by parsing the associated clinical XML records. Original PDF reports were converted to Markdown using a layout-aware parser to preserve semantic structure. Six LLM architectures, ranging from 8B to 120B+ parameters, were evaluated using identical zero-shot system prompts. Performance was assessed using weighted F1-score, precision, and recall.

### RESULTS

[THE FOLLOWING DATA IS TO BE POPULATED AFTER FULL RUN]
The study cohort included 507 cases with a 92.7% data completeness rate in the ground truth. Preliminary evaluation on a representative subset showed that larger parameter models achieved high fidelity in extracting quantitative values like tumor size (Accuracy: [X]%) and categorical values like histologic variant (Accuracy: [Y]%). However, systematic error patterns were identified in complex anatomic descriptions such as tumor site laterality and multifocal extrathyroidal extension.

| Model Scale      | Weighted F1-Score | Precision | Recall |
| :--------------- | :---------------: | :-------: | :----: |
| Large (70B+)     |      [X.XX]       |  [X.XX]   | [X.XX] |
| Medium (30B-70B) |      [X.XX]       |  [X.XX]   | [X.XX] |
| Small ( <10B)    |      [X.XX]       |  [X.XX]   | [X.XX] |

### CONCLUSIONS

These findings demonstrate that LLMs can accurately automate the abstraction of complex pathology data points, though performance is highly dependent on model scale and reporting complexity. This methodology provides a scalable framework for building institutional cancer databases at Moffitt, potentially reducing manual abstraction effort by over [Z]%. Future work will evaluate the transferability of these models to non-standardized institutional reports.

---

## Body Character Count Check (Excluding Spaces)

_Current estimate: ~1,500 characters. (Limit: 2,000 characters)_

---

## 📝 Project Context & "The Why"

This study is not just an evaluation of AI; it is a validation of **generalizability**.

1. **Replicability**: By using TCGA, we establish a baseline that any researcher can replicate.
2. **Clinical Utility**: We focus on the "messy" parts of a report—laterality, ETE, and margins—which are traditionally hard for rule-based systems.
3. **Hospital Readiness**: By testing smaller models (8B, 32B), we explore whether Moffitt can run these models **locally/on-premise**, ensuring HIPAA compliance and data security without relying on cloud APIs.
4. **Scale**: Automating 500 reports in minutes rather than weeks allows researchers to focus on clinical insights rather than data entry.
