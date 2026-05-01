Moffitt Symposium Poster 

 

Evaluating Open-Source Large Language Models for Automated Abstraction of Thyroid Cancer Pathology Data  

 

Introduction 

Cancer registries capture structured variables, but research-critical details — histologic subtype, extension patterns, multifocal disease — often exist only in free-text pathology reports, and getting them out at scale requires either manual abstraction or automation. Open-weight LLMs are locally deployable options that reduce privacy and cost concerns, and recent studies show they can achieve high agreement on pathology extraction tasks.1-3 However, high agreement alone does not establish a system as research-grade: disagreements may reflect model error, source ambiguity, incomplete abstraction rules, or limitations in the reference standard itself. Systematic error review is needed to distinguish correctable model failures from task-inherent limitations.4

To evaluate whether open-weight LLMs can abstract key thyroid cancer pathology variables from free-text pathology reports with high agreement to reference data, and to determine whether model-reference disagreements reflect model failures, ambiguous source text, abstraction-rule limitations, or reference-standard issues.

 

Methods 

Seven open-weight LLMs were evaluated on a thyroid cancer pathology abstraction task using TCGA-THCA pathology reports and corresponding structured reference labels. Reports were divided into a prompt-development set (n=82) and a held-out test set (n=200). The task focused on five pathology variables relevant to thyroid cancer research and cancer registry-style abstraction.

Variables extracted: Tumor site, Tumor size, Histologic variant, Extrathyroidal extension, Margins.

Pathology reports were converted into model-readable text while preserving report structure where possible. Each model received a registry-style abstraction prompt (zero-shot — no labeled examples were provided) that specified the target variables, allowable output categories, evidence requirements, section-priority rules, and tie-breaking logic. Outputs were returned in structured JSON and deterministically normalized before comparison with reference labels.

Model performance was evaluated using weighted F1 score (which accounts for class-frequency imbalance across output categories) across the held-out test set. Because agreement metrics can obscure the reasons for disagreement, mismatched cases underwent manual evidence review.4 Disagreements were categorized into four error sources: rule compliance failure, source ambiguity, scope limitation, or reference-standard issue.

 

Results 

Open-weight LLMs achieved high zero-shot agreement with reference labels across the five thyroid cancer pathology variables. Average weighted F1 scores ranged from 0.93 to 0.96 across evaluated models. Performance differences across model sizes were modest, demonstrating that larger models were not uniformly superior for this constrained extraction task.

Variable-level performance was highest for structured or explicitly reported concepts such as margin status, extrathyroidal extension, and histologic variant. Tumor site was more challenging, reflecting ambiguity in report wording, multifocal disease, and the need for precise abstraction rules.

Key finding: model scale was not the main determinant of performance. Instead, performance depended heavily on whether the prompt encoded registry-style rules, section priorities, and normalization logic.

 

 

Table 1\. Agreement Between LLM Abstraction and TCGA Reference Data (weighted F1 Score) 

 

| Model  | Histology  | ETE  | Margins  | Site  | Size  | Average  |
| :---- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Llama 3.1 8B**  | 0.95  | 0.91  | 0.94  | 0.9  | 0.93  | 0.926  |
| **GPT OSS 20B**  | 0.93  | 0.97  | 1  | 0.86  | 0.93  | 0.938  |
| **Qwen3 32B**  | 0.95  | 0.98  | 0.99  | 0.89  | 0.93  | 0.948  |
| **Llama 3.3 70B**  | 0.96  | 0.96  | 0.97  | 0.91  | 0.93  | 0.946  |
| **GPT OSS 120B**  | 0.94  | 0.96  | 0.99  | 0.86  | 0.93  | 0.936  |
| **Mistral-Large 3 (675B)**  | 0.96  | 0.98  | 0.97  | 0.87  | 0.92  | 0.940   |
| **Kimi-K2 (1T)**  | 0.96  | 0.98  | 0.99  | 0.91  | 0.94  | **0.956**  |

 

 

Error Analysis 

Manual review showed that not all model-reference disagreements represented model error. Disagreements clustered into four categories:

Rule compliance failure:

The needed information was present and the prompt contained the correct rule, but the model failed to apply it consistently.

Source ambiguity:

The pathology report contained conflicting, incomplete, or difficult-to-interpret information.

Scope limitation:

The reference label required information not fully available in the pathology report, such as operative or clinical context outside the extracted source document.

Reference-standard issue:

Manual evidence review showed that the model output was better supported by the pathology report than the structured reference label.

These findings reinforce recent work arguing that single agreement metrics conflate task-inherent ambiguity with model error, and may underestimate performance when the reference standard is itself incomplete.4

 

Discussion 

Open-weight LLMs demonstrated high agreement on thyroid cancer pathology abstraction, and performance was driven more by prompt quality than model size. The abstraction prompt functions as a reproducible protocol: it must encode variable definitions, permissible categories, section-priority rules, and tie-breaking criteria. Structured schemas and clearly specified data dictionaries improve model usability and downstream interoperability.3

Error review showed that some mismatches reflected reference-standard limitations rather than model error — cases where the model's output was better supported by the report text than the structured registry label. For research deployment, LLM abstraction systems should include evidence-linked outputs, deterministic normalization, and targeted human review of uncertain or discordant cases.

 

Conclusion 

Open-weight LLMs achieved high zero-shot agreement with reference labels across five thyroid cancer pathology variables, with average weighted F1 of 0.93–0.96. Larger models did not consistently outperform smaller ones, demonstrating that model choice alone is not the primary performance driver.

The central challenge is not computational but conceptual: codifying the tacit clinical reasoning that expert abstractors apply, encoding it into a structured prompt, and ensuring the model follows those rules consistently. These findings support a human-in-the-loop workflow in which LLMs perform first-pass abstraction and disagreement review focuses on cases most likely to affect downstream research conclusions.

 

Future Directions 

The immediate next step is applying this pipeline to Moffitt's institutional thyroid pathology corpus, which would test generalizability beyond TCGA formatting. Prompts should be maintained as version-controlled protocols, and private benchmark sets held back for evaluation as model versions change.

 

References 

Lee D, Vaid A, Menon KM, Freeman R, Matteson DS, Marin ML, et al. Using large language models to automate data extraction from surgical pathology reports: retrospective cohort study. JMIR Form Res. 2025;9:e64544. doi:10.2196/64544. 

Grothey B, Odenkirchen J, Brkic A, Schömig-Markiefka B, Quaas A, Büttner R, et al. Comprehensive testing of large language models for extraction of structured data in pathology. Commun Med (Lond). 2025;5:96. doi:10.1038/s43856-025-00808-8. 

Balasubramanian JB, Adams D, Roxanis I, Berrington de Gonzalez A, Coulson P, Almeida JS, et al. Leveraging large language models for structured information extraction from pathology reports. J Pathol Inform. 2025;19:100521. doi:10.1016/j.jpi.2025.100521. 

Xu Z, Khatri V, Dai Y, Liu X, Li S, Zhang X, et al. Enhancing LLM-based data annotation with error decomposition. arXiv. 2026\. doi:10.48550/arXiv.2601.11920. 

 

 
