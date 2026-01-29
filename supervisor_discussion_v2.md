# LLM Pathology Extraction: Supervisor Discussion Document
**Pilot Study Results & Proposed Direction**  
*Updated: January 2026*

---

## Executive Summary

**Problem**: Pathology variables like vascular invasion, extrathyroidal extension, and nodal involvement exist in our reports but aren't structured data. Every retrospective study requires manual abstraction.

**Pilot Results (n=63)**: Tested 7 LLMs on 9 thyroid pathology fields. Performance varies dramatically by field complexity—all models achieve 100% on histologic type, but lymph node quantification separates tiers (63% for small models vs 89% for large).

**Proposed Direction**: Select one model tier based on computational infrastructure availability, then systematically improve performance through iterative prompt refinement using confusion matrix analysis.

**Key Decision Needed**: What accuracy threshold do you consider acceptable for research use? This will determine model selection and refinement strategy.

---

## The Research Problem We're Solving

### Current Bottleneck
Manual pathology abstraction limits our ability to:
- **Rapidly build cohorts**: "Find all cases with vascular invasion + positive margins"
- **Screen trial eligibility**: "How many patients meet pathologic criteria?"
- **Conduct outcomes research**: Link pathology features to survival at scale
- **Enable QA/auditing**: Flag discrepancies between staging and pathology

### What This Could Enable
- Automated extraction of research variables from archived reports
- Real-time abstraction for prospective studies
- Quality assurance flagging for human review
- Teaching datasets organized by pathologic features

---

## Pilot Results: Field Complexity Hierarchy

### Performance by Field (n=63 thyroid cancer reports)

```
TIER 1: Universal Success (100% accuracy, all models)
└─ Histologic Type

TIER 2: Strong Performance (>85% accuracy, all model sizes)
├─ Focality: 87-94%
├─ Tumor Site: 81-89%
├─ Tumor Size: 84-86%
└─ Histologic Variant: 83-87%

TIER 3: Model-Dependent (requires medium+ models for >80%)
├─ Margins: 76-86%
├─ Lymph Nodes Resected: 83-95%
└─ Extrathyroidal Extension: 67-86%

TIER 4: Discriminator Field (requires large models for >85%)
└─ Lymph Nodes Positive Count: 63-89%
    (Critical for AJCC N-staging)
```

### Key Finding
**Lymph node positive count is the differentiator**—requires parsing narrative text like "3 of 15 lymph nodes positive for metastatic disease" into structured counts. Small models struggle (63%, F1: 0.60), large models succeed (89%, F1: 0.88).

---

## Model Selection: Computational Requirements

Rather than discuss per-report costs, here's what different model tiers require:

### Small Models (8B parameters)
- **Infrastructure**: Standard workstation with GPU (~$3,000-5,000 setup)
- **Deployment**: Can run locally on-premise for HIPAA compliance
- **Performance**: Research-grade (>85%) on 6/9 fields
- **Limitations**: Fails on extrathyroidal extension (67%), lymph node counts (63%)
- **Example**: llama-3.1-8b-instant

### Medium Models (32-70B parameters)
- **Infrastructure**: Multi-GPU workstation (~$15,000-20,000) OR secure cloud API
- **Deployment**: **Moffitt has secure cloud access for these models**
- **Performance**: >80% accuracy on 8/9 fields
- **Limitations**: Lymph node count still challenging (81-86%)
- **Example**: qwen3-32b, llama-3.3-70b

### Large Models (120B+ parameters)
- **Infrastructure**: Enterprise GPU cluster OR secure cloud API
- **Deployment**: **Moffitt has secure cloud access**
- **Performance**: 77-100% across all fields
- **Advantage**: Best performance on lymph node quantification (89%)
- **Example**: gpt-oss-120b, mistral-large-3

---

## Proposed Next Steps: Single-Model Optimization

### Phase 1: Model Selection (Your Input Needed)
**Question**: What accuracy threshold is acceptable for research use?

**Option A: Medium Model (32-70B)**
- Rationale: Moffitt has secure cloud access; 80%+ on most fields
- Target fields for improvement: lymph node count (currently 81-86%)
- **Ask**: "Is 85% good enough for most research, with human verification on complex cases?"

**Option B: Large Model (120B)**
- Rationale: Best performance on critical staging variables (89% on nodes)
- Target: Push all fields to >90% through prompt optimization
- **Ask**: "Do we need maximum accuracy, or is 'good enough' acceptable?"

### Phase 2: Iterative Prompt Refinement
Once model selected, systematically improve performance:

1. **Error Analysis via Confusion Matrices**
   - Identify error patterns (missed vs misclassified vs hallucinated)
   - Example: Are lymph node errors due to:
     - Missing the count entirely? → Add explicit extraction instruction
     - Confusing "total resected" with "positive"? → Add disambiguation examples
     - Parsing complex phrasing? → Provide few-shot examples

2. **Prompt Engineering Iterations**
   - Test specific improvements targeting error patterns
   - Validate on held-out test set
   - Track F1-score improvements per iteration

3. **Field-Specific Optimization**
   - Focus refinement on critical fields first (nodes, ETE)
   - May develop field-specific prompts if needed

### Phase 3: Validation on Full Dataset
- Run optimized model on all 407 reports
- Calculate final performance metrics with confidence intervals
- Compare to inter-annotator agreement (if available)

---

## Questions for Discussion

### Strategic
1. **Accuracy threshold**: What performance level would make you trust automated extraction for:
   - Retrospective cohort building?
   - Trial feasibility screening?
   - Outcomes research?
   - (Human verification always available for ambiguous cases)

2. **Priority fields**: Which variables are most critical for your research portfolio?
   - Lymph node involvement (for staging)?
   - Vascular invasion (for risk stratification)?
   - Margins (for surgical adequacy)?
   - Others I should test?

3. **Infrastructure**: Do we use Moffitt's secure cloud LLM access, or is there preference for local deployment?

### Methodological
4. **Benchmark**: Should we measure inter-annotator agreement between human abstractors to contextualize LLM performance?

5. **Expansion**: After thyroid validation, which tumor types would be highest impact?
   - Sarcomas (complex histologies)?
   - GI tumors (extensive staging)?
   - Other?

### Practical
6. **Timeline**: What's your preferred timeline for:
   - Full 407-report experiment?
   - Symposium abstract submission?
   - Potential publication?

7. **Collaborators**: Should I loop in specific pathologists or informaticists for clinical input on acceptable accuracy thresholds?

---

## Why This Approach

**Focus on one model** rather than comparing many:
- Avoids "model comparison" paper (less interesting)
- Emphasizes **methodology** (prompt engineering, error analysis)
- More generalizable to other institutions
- Shows problem-solving approach (not just benchmarking)

**Iterative improvement** demonstrates rigor:
- Confusion matrix analysis = systematic debugging
- Shows we understand error modes, not just reporting numbers
- Positions this as applied research, not just tool evaluation

**Acceptable accuracy threshold** is the key question:
- 90% accuracy on 1000 reports = 100 errors to manually review
- If that's acceptable, medium models likely sufficient
- If we need >95%, may require large models + extensive refinement

---

## Next Steps After This Meeting

Based on your input, I'll:
1. **Select target model** (medium vs large based on accuracy needs)
2. **Run full 407-report baseline** (establish current performance)
3. **Conduct error analysis** (build confusion matrices, categorize failures)
4. **Draft 1-2 prompt refinements** (targeting top error patterns)
5. **Validate improvements** (measure F1 gains)
6. **Prepare symposium abstract** (with real results + conclusions)

**Timeline estimate**: 2-3 weeks for full cycle

---

## Appendix: Detailed Performance Data

### Model Performance Summary (n=63)

**Small Model: llama-3.1-8b-instant**
- Histologic Type: 100% (F1: 1.00) ✓
- Focality: 94% (F1: 0.94) ✓
- Tumor Site: 89% (F1: 0.89) ✓
- Margins: 86% (F1: 0.90) ✓
- Tumor Size: 84% (F1: 0.83) ✓
- Histologic Variant: 83% (F1: 0.86) ✓
- Lymph Nodes Resected: 83% (F1: 0.77) ⚠
- **Extrathyroidal Extension: 67% (F1: 0.71)** ⚠
- **Lymph Nodes Positive: 63% (F1: 0.60)** ⚠

**Medium Model: qwen3-32b** (Best cost-performance balance)
- Histologic Type: 100% (F1: 1.00) ✓
- Lymph Nodes Resected: 95% (F1: 0.95) ✓
- Focality: 92% (F1: 0.92) ✓
- Extrathyroidal Extension: 86% (F1: 0.87) ✓
- Tumor Size: 86% (F1: 0.85) ✓
- Tumor Site: 85% (F1: 0.86) ✓
- Histologic Variant: 85% (F1: 0.87) ✓
- **Lymph Nodes Positive: 81% (F1: 0.82)** ⚠
- Margins: 76% (F1: 0.83) ⚠

**Large Model: mistral-large-3**
- Histologic Type: 100% (F1: 1.00) ✓
- Lymph Nodes Resected: 95% (F1: 0.95) ✓
- Focality: 90% (F1: 0.91) ✓
- **Lymph Nodes Positive: 89% (F1: 0.88)** ✓ [BEST]
- Histologic Variant: 87% (F1: 0.89) ✓
- Margins: 85% (F1: 0.90) ✓
- Tumor Size: 85% (F1: 0.84) ✓
- Tumor Site: 84% (F1: 0.85) ✓
- Extrathyroidal Extension: 77% (F1: 0.81) ⚠

---

**What I Need From You**:
1. Acceptable accuracy threshold for research use
2. Model tier preference (medium vs large)
3. Priority fields for optimization focus
4. Timeline expectations
5. Other tumor types to consider

**Let's discuss and lock in a clear direction.**
