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

_Current Progress_: Gold standard established for 507 cases. Parsing identified 94 cases where lymph node counts were absent due to lack of resection (correctly identified via `primary_lymph_node_presentation_assessment`), resulting in a 19% increase in usable reference data.
_[Pending Results]_: Comparative metrics across Mistral and Llama architectures.

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
- **Target Elements**: Histologic Type, Stage, Pathologic T/N/M, Extrathyroidal Extension, Focality, Lymph Node Counts.
