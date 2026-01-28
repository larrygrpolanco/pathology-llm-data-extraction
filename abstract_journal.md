# Abstract Development Journal
## Evaluating LLMs for Thyroid Cancer Pathology Abstraction

### 1. Model Selection Framework: The Three-Tier Ethics

To address both **high-performance requirements** at NCI-designated centers and **global health access**, we categorize models into deployment tiers rather than simply "best vs. worst." This framework acknowledges that a 50% cost reduction enabling deployment in low-resource settings is ethically preferable to marginal gains for wealthy institutions.


#### **Tier 1: Accessible (Small, ≤10B)**
**Representative**: `llama-3.1-8b`

- **Role**: On-premise deployment for HIPAA-sensitive environments, global health applications, resource-limited pathology departments
- **Performance**: XX accuracy (XX%) on 5/8 fields: histologic_type, histologic_variant, tumor_size, margins, focality
- **Limitations**: Extrathyroidal extension (XX%), lymph node positive count (XX%)
- **Clinical Interpretation**: Excellent for basic registry abstraction and diagnostic confirmation; requires human verification for surgical extent (ETE) and nodal staging

#### **Tier 2: Clinical Standard (Medium, 30B-70B)**
**Representative**: `qwen3-32b`

- **Role**: The "sweet spot" for hospital deployment—balancing accuracy with operational cost
- **Performance**: XX accuracy (XX%) on 6/8 fields, specifically **correcting the 8B model's failure on extrathyroidal extension (XX%) and tumor site (XX%)**
- **Limitations**: Lymph node positive count (XX%) remains challenging
- **Clinical Interpretation**: Suitable for surgical abstraction and AJCC staging (T-category); ETE accuracy critical for risk stratification

#### **Tier 3: Maximum Accuracy (Large, &gt;70B)**
**Representative**: `mistral-large` (OpenRouter) or `llama-3.1-405b`

- **Role**: High-stakes research, multi-center trials, and complex case review where maximum fidelity justifies API costs
- **Performance**: `mistral-large` achieves **83.3% accuracy on lymph_nodes_positive_count** (vs. 50% for smaller tiers) and perfect histologic_variant classification (where 405B hits 83.3%)
- **Clinical Interpretation**: Essential for accurate N-staging in research contexts; the only tier reliably extracting nodal burden from narrative text



---

### 2. Key Clinical Insights from Data

...

---

### 3. Draft Abstract (Moffitt 2026 Submission)
*Character count: ~1,850 (excluding spaces, table, title, authors)*

**Title**: Tiered Deployment of Large Language Models for Thyroid Cancer Pathology Abstraction: Balancing Accuracy, Cost, and Global Accessibility

**Background**: Manual abstraction of pathology data creates bottlenecks in cancer registries. While frontier AI models offer high accuracy, the performance of efficient, deployable models—critical for resource-limited settings—remains unclear. We evaluated multi-scale LLMs to establish tiered deployment recommendations for varied clinical environments.

**Methods**: We extracted 8 prognostic data points from 407 TCGA-THCA thyroid pathology reports. Models spanning 8B to large parameters were evaluated with zero-shot prompting: a small open-source model (8B), an optimized medium model (32B), and a frontier large model. Performance was assessed via accuracy and F1-score against XML-derived gold standards.

**Results**: T


**Conclusions**: LLM selection should match clinical use case and resource availability. Small models suffice for diagnostic abstraction in low-resource settings, medium models (32B) provide optimal accuracy-cost balance for institutional registries, and large models remain necessary for research requiring precise nodal staging. This tiered framework enables equitable AI deployment across diverse cancer center environments.

---

### 4. Presentation Narrative Notes

**The "Why This Matters" Hook**: 
"In Mozambique, a pathologist reviews 50 thyroid cases daily with no abstractor support. At Moffitt, we have three full-time staff for 500 annual thyroid cases. This study asks: do both sites deserve AI assistance, or just the wealthy one? The 8B model says we can serve both."

...