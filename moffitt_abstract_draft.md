# Evaluating Open-Source Large Language Models for Automated Abstraction of Thyroid Cancer Pathology Data

**AUTHORS:** Larry Grullon-Polanco*, Colleen Veloski+

## BACKGROUND

Moffitt Cancer Center maintains over 16,000 thyroid cancer pathology reports spanning decades. Many key variables exist in structured datasets, but some research-critical details remain only in free-text narratives. This gap is pronounced in complex cases (e.g., multifocal or bilateral disease), where granular findings are often simplified. As a result, research questions that depend on complete pathologic detail still require labor-intensive manual abstraction. This study evaluates open-source large language models (LLMs) for automated pathology abstraction and categorizes discrepancies to distinguish abstraction error types.

## METHODS

200 TCGA-THCA pathology reports were processed using seven open-source LLMs, ranging from a small model that can be locally run on a standard laptop (Llama 3.1 8B) to a massive model (Kimi K2) requiring substantial GPU resources. Five key variables (see Table 1) were abstracted and benchmarked against TCGA Clinical data. Errors were categorized by type (e.g., clinical ambiguity, specificity loss, OCR failures) to isolate true abstraction failures from interpretive judgment and source data limitations.

## RESULTS

Performance was similar across model sizes and error patterns were consistent, suggesting a plateau in capabilities. Even the laptop-runnable model proved competitive. The LLMs accurately abstracted reported findings, but this sometimes conflicted with how patients were coded in registries. For example, models correctly captured bilateral disease documented in reports, while TCGA clinical dataset typically recorded only the dominant site.

## CONCLUSION

Local open-source LLMs are a viable, efficient solution for automated abstraction. Mid-sized models (32B–70B) balance accuracy and compute; larger models yield diminishing returns. Error analysis reveals that these models do not fail at reading pathology reports. They fail at emulating human clinical judgment. While they accurately capture explicitly stated findings, they lack the implicit rules for prioritizing findings when reports contain conflicting information. The implementation challenge is thus not computational but conceptual: codifying the tacit clinical reasoning that expert abstractors apply intuitively and ensuring LLMs consistently follow those rules.

---

### Table 1. Agreement Between LLM Abstraction and TCGA Reference Data (F1 Score)

| Model | Histology | ETE | Margins | Site | Size | Average |
|-------|-----------|-----|---------|------|------|---------|
| Llama 3.1 8B | 0.95 | 0.91 | 0.94 | 0.9 | 0.93 | 0.926 |
| GPT OSS 20B | 0.93 | 0.97 | 1 | 0.86 | 0.93 | 0.938 |
| Qwen3 32B | 0.95 | 0.98 | 0.99 | 0.89 | 0.93 | 0.948 |
| Llama 3.3 70B | 0.96 | 0.96 | 0.97 | 0.91 | 0.93 | 0.946 |
| GPT OSS 120B | 0.94 | 0.96 | 0.99 | 0.86 | 0.93 | 0.936 |
| Mistral-Large 3 (675B) | 0.96 | 0.98 | 0.97 | 0.87 | 0.92 | 0.94 |
| Kimi-K2 (1T) | 0.96 | 0.98 | 0.99 | 0.91 | 0.94 | 0.956 |