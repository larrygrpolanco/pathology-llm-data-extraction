**TITLE:**  
 Evaluating Open-Source Large Language Models for Automated Abstraction of Thyroid Cancer Pathology Data\[DP1\] 

**AUTHORS:**  
 Larry Grullon-Polanco\*, Colleen Veloski\+

**BACKGROUND:**  
 Moffitt Cancer Center maintains over 16,000 thyroid cancer pathology reports spanning decades. Many key variables exist in structured datasets, but some research-critical details remain only in free‑text narratives. This gap is pronounced in complex cases (e.g., multifocal or bilateral disease), where granular findings are often simplified. As a result, research questions that depend on complete pathologic detail still require labor‑intensive manual abstraction. This study evaluates open‑source large language models (LLMs) for automated pathology abstraction and categorizes discrepancies to distinguish abstraction error types.\[DP2\] 

**METHODS:**  
 200 TCGA-THCA pathology reports were processed using seven open‑source LLMs, ranging from a small model that can be locally run on a standard laptop (Llama 3.1 8B) to a massive model (Kimi K2) requiring substantial GPU resources. Five key variables (see Ttable 1\) were abstracted \[DP3\] and benchmarked against TCGA Clinical data. Errors were categorized by type (e.g., clinical ambiguity, specificity loss, OCR\[DP4\]  failures) to isolate true abstraction failures from interpretive judgment and source data limitations.

**RESULTS:**  
 Performance was similar across model sizes and error patterns were consistent (Table 1), suggesting a plateau in capabilities. Even the laptop-runnable model proved competitive. The LLMs accurately abstracted reported findings\[DP5\] , but this sometimes conflicted with how patients were coded in registries. For example, models correctly captured bilateral disease documented in reports, while TCGA clinical dataset typically recorded only the dominant site.

**CONCLUSION:**  
 Local open-source LLMs are a viable, efficient solution for automated abstraction. Mid-sized models (32B–70B) balance accuracy and compute; larger models yield diminishing returns. Error analysis reveals that these models do not fail at reading pathology reports. They fail at emulating human clinical judgment. While they accurately capture explicitly stated findings, they lack the implicit rules for prioritizing findings when reports contain conflicting information. The implementation challenge is thus not computational but conceptual: codifying the tacit clinical reasoning that expert abstractors apply intuitively and ensuring LLMs consistently follow those rules.\[DP6\] 

 

**Table 1\.** Agreement Between LLM Abstraction and TCGA Reference Data (F1 Score)

| Model | Histology | ETE | Margins | Site | Size | Average |
| :---- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Llama 3.1 8B** | 0.95 | 0.91 | 0.94 | 0.9 | 0.93 | 0.926 |
| **GPT OSS 20B** | 0.93 | 0.97 | 1 | 0.86 | 0.93 | 0.938 |
| **Qwen3 32B** | 0.95 | 0.98 | 0.99 | 0.89 | 0.93 | 0.948 |
| **Llama 3.3 70B** | 0.96 | 0.96 | 0.97 | 0.91 | 0.93 | 0.946 |
| **GPT OSS 120B** | 0.94 | 0.96 | 0.99 | 0.86 | 0.93 | 0.936 |
| **Mistral-Large 3 (675B)** | 0.96 | 0.98 | 0.97 | 0.87 | 0.92 | 0.94\[DP7\]  |
| **Kimi-K2 (1T)** | 0.96 | 0.98 | 0.99 | 0.91 | 0.94 | **0.956** |

 

Zero shot\! More about the methods. More clear about selection criteria not just 200 TCGA-THCA N=200 with proper lables extracted by the X in X time and I will use this as the gold standard. Talk about exploring

Value of the work is design a prompt that codifies… write  down a prompt that simulates extraction. Make this more smooth even when I try to micic abstractor thinking when designing prompt I notice that I does not follow all the rules

Variables categories vs numbers. If there is an imbalance this is an issues. Not all metrics are a good fit for the type of variables I am abstracting. Use other metrics that handle imbalance. Go to metric for high stratification in categories is Macro F1. Add comment and discuss macro.

Important to specify that I am designing a prompt. The value of the work is the prompt. The scientific work is the prompt engineering and optimization. This needs need to be clear the value of this type of work. The last sentence in the conclusion needs to be specified. Make clear I worked on that direction

When people read

---

 \[DP1\]Great work. Very nicely written and presented abstract.  
 \[DP2\]You may want to clarify – categorize discrepancies compared to what? Structured datasets (TCGA-THCA) or manual extraction?  
 \[DP3\]Little unclear here. Were the variables abstracted from the free-text narratives of the original pathology reports?  And then benchmarked against TCGA clinical dataset.  
 \[DP4\]You may want to expand it.  
 \[DP5\]I am a little confused here. How do we know about the accuracy? Were the LLM abstractions validated against manual extraction? If yes, how many of the 200 path reports were manually validated and by how many reviewers? Was there inter-reviewer variability?  
   
I understand there is a word limit. But these are questions that are likely to be asked during poster presentation or if you plan to write this up as a complete manuscript.  
 \[DP6\]Great conclusion.  
 \[DP7\]Why is this only two digits? Is it supposed to be 0.940?  
