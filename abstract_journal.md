# Abstract Draft Journal: Thyroid Pathology Data Extraction

**Purpose**: This document serves as a rolling record of the research, methodology, and results for the thyroid pathology data extraction project. It is structured to facilitate the drafting of a manuscript focused on the **Generalizability of LLM-Based Pathology Abstraction**, specifically comparing standardized TCGA benchmarks against varied model scales (Large, Medium, Small).

---

## Research Strategy: The Generalizability Gap

### The "Why"

- **Manual Bottleneck**: Manual abstraction is the primary bottleneck in building comprehensive cancer databases (like the Moffitt thyroid database).
- **The TCGA Trap**: Most existing literature (2024-2025) reports 90%+ accuracy on TCGA-THCA data because it is "clean" and structured.
- **The Gap**: Performance often degrades on real-world, unstructured institutional reports characterized by free-text narratives and heterogeneity (as identified by ThyroPath/Springer).
- **Objective**: Establish a high-fidelity TCGA baseline across model scales to eventually test transferability to institutional data.

### Model Benchmarking Plan (Pilot Phase)

We will evaluate models across three scales to assess the cost-performance tradeoff:

| Scale      | Models                            |
| :--------- | :-------------------------------- |
| **Large**  | `mistral-large2`, `llama3.1-405b` |
| **Medium** | `llama3.1-70b`, `mixtral-8x7b`    |
| **Small**  | `llama3.1-8b`, `mistral-7b`       |

---

## 2026 Moffitt Scientific Symposium Draft (Working Concept)

### Title

Evaluating Generalizability and Scale-Dependent Performance of Large Language Models in Thyroid Cancer Pathology Abstraction

### Background

Large Language Models (LLMs) have demonstrated high accuracy (90%+) in extracting structured data from standardized cancer registries like TCGA. However, the generalizability of these results to varied reporting formats remains under-explored. This study establishes a multi-scale benchmark for LLM-based extraction of seven critical thyroid pathology elements to determine the optimal balance between model size, accuracy, and deployment feasibility.

### Methods (Step 1 Completed)

A gold-standard dataset of 507 TCGA-THCA cases was established by automated XML parsing (92.7% completeness rate).
**Next Steps**:

1. **Prompt Engineering**: Develop a zero-shot system-prompt to extract data from original PDF reports into structured JSON.
2. **Multi-Model Inference**: Run 6 models (scales 7B to 405B) using identical prompts.
3. **Validation**: Parse JSON outputs and validate against the XML-derived gold standard.
4. **Metric Collection**: Calculate F1, Precision, and Recall for each model scale.

### Results

Summary of 507 cases:
  - Incomplete cases: 37 (7.3%)
  - Files missing from disk: 0

Missing values per column:
  - pathologic_stage              : 2 (0.4%)
  - pathologic_M                  : 1 (0.2%)
  - lymph_nodes_examined_count    : 114 (22.5%)
  - lymph_nodes_positive_count    : 116 (22.9%)
  - extrathyroidal_extension      : 18 (3.6%)
  - lymph_nodes_examined_status   : 10 (2.0%)
  - focality                      : 10 (2.0%)

Value distributions:
  - pathologic_T:
    - T3                       : 171
    - T2                       : 167
    - T1b                      : 80
    - T1                       : 44
    - T1a                      : 20
    - T4a                      : 14
    - T4                       : 9
    - TX                       : 2
  - pathologic_N:
    - N0                       : 231
    - N1a                      : 93
    - N1b                      : 75
    - N1                       : 58
    - NX                       : 50
  - pathologic_M:
    - M0                       : 283
    - MX                       : 214
    - M1                       : 9
  - data_quality_flag:
    - OK                       : 470
    - INCOMPLETE               : 37

### Conclusions

[Pending] - Establishing whether Small/Medium models (8B-70B) can match Large-scale (405B) performance for structured extraction, which has significant implications for local, HIPAA-compliant deployment in clinical settings.

---

## Project Log & Technical Notes

### Phase 1: Gold Standard Construction (DONE)

- **Tooling**: Built a Python pipeline to link TCGA PDF/XML pairs.
- **Critical Finding**: XML logic must account for `primary_lymph_node_presentation_assessment`. If "NO", the patient is N0 but lacks count data; this is a "Complete" report, not a missing data point.

### Phase 2: Inference & Metrics (READY)

- **Architecture**: Zero-shot prompting with JSON schema enforcement.
- **Models**: Focus on Llama 3.1 and Mistral families.
- **Target Elements**: Histologic Type, Pathologic T/N/M, Extrathyroidal Extension, Focality, Lymph Node Counts.
