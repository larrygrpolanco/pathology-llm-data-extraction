# Poster Preparation: Rule-Based, Not Random

*Expanded notes for your poster presentation. Everything the abstract can't fit.*

---

## The Story in One Sentence

The LLMs aren't failing because they can't read — they're failing because the rules they were given don't match the rules the Gold Standard was built on, and that's actually a solvable problem.

---

## Why This Matters (Your Pitch)

You don't need to be a developer to explain this one. The core argument is practical:

We have 16,000+ thyroid pathology reports sitting in free text. Right now, turning those into usable research data means someone reads each one by hand and types the findings into a structured database. That is not sustainable. This study shows that mid-sized, locally deployable LLMs can do that extraction at over 90% accuracy — and that most of the remaining errors aren't random mistakes. They are predictable, systematic, and fixable with better prompt design. That means this is a real pipeline, not just a proof of concept.

The privacy and cost angle is simple: running these models locally keeps patient data on our servers and costs near zero after setup, unlike sending tens of thousands of reports to a commercial API.

---

## The Models (How to Explain the Grouping)

Seven models were tested. For the poster, group them into three tiers based on effective parameter count. This keeps the visual clean and the message clear.

| Tier | Models | Why This Grouping |
|:---|:---|:---|
| **Small** | Llama-3.1-8B, GPT-OSS-20B | Consumer-grade hardware, lowest compute |
| **Mid** | Qwen3-32B, Llama-3.3-70B, Kimi-K2 | Kimi-K2 is a mixture-of-experts model (~32B active parameters despite a larger total architecture). Grouped here by effective compute. |
| **Large** | Mistral-Large (~123B), GPT-OSS-120B | Largest parameter counts, most compute-intensive |

The key finding: **Mid-tier models matched or beat Large-tier models on four of five variables.** That is the headline.

---

## The Results (What the Numbers Actually Say)

### What worked well

Surgical Margins was the standout: the Small-tier GPT-OSS-20B hit F1 = 0.99, the single highest score in the study. Histologic Variant and Extrathyroidal Extension both exceeded 0.95 across Mid and Large models. These are fields where the pathology report contains an explicit, unambiguous statement and the Gold Standard agrees on how to read it. LLMs are very good at this.

### What didn't work as well — and why

Tumor Site was the consistent weak spot: F1 ranged from 0.86 to 0.91 across all models, with no clear size advantage. This is where the error analysis becomes the real story (see below). The models were reading correctly. The problem was the definition of "correct."

Tumor Size errors were smaller but followed a similar pattern: conflicting measurements in different sections of the same report, and the model and Gold Standard disagreed on which section was authoritative.

### The bottom line on model size

Bigger models did not outperform smaller ones in any meaningful way. The overall average F1 across all five variables ranged from 0.926 (Llama-8B) to 0.955 (Kimi-K2). That is a narrow band. For a department looking to deploy this, the practical implication is clear: you do not need the most expensive model.

---

## The Error Analysis: Consolidated into Three Categories

This is where your applied linguistics background shines. The raw error analysis covered a lot of ground across five variables, but when you step back, almost everything collapses into three overarching patterns. Each one has a clear cause and a clear fix.

### 1. Definition Alignment

**What it is:** The LLM followed its instructions correctly, but the Gold Standard was built using a different set of rules that weren't in the prompt.

**Why it happens:** Registry curation standards like TCGA/GDC use conventions that are often implicit — things like "ignore microcarcinomas when determining tumor site" or "use the dominant nodule, not every focus." These aren't written down in the pathology report. They are institutional knowledge that human abstractors carry but that no one thought to put in a prompt.

**Examples from your data:**
- *Tumor Site:* The prompt told the model to flag "Bilateral" if carcinoma appeared in both lobes. The model did exactly that. But the Gold Standard routinely ignored tiny contralateral microcarcinomas (< 1 cm) and recorded only the dominant tumor's location. The model was technically correct by its own rules. The Gold Standard used a different rule.
- *Tumor Size:* The report listed tumor measurements in two places — the Final Diagnosis and the Synoptic Report — and they didn't match. The model and Gold Standard picked different sections as authoritative.
- *Histologic Variant:* A report said "mixed classical and follicular variant." The model flagged Follicular (the more specific term). The Gold Standard applied a "default to Classical if mixed" convention.

**The fix:** Rewrite the prompt to include these conventions explicitly. This is prompt engineering, not model engineering.

### 2. Context Boundary

**What it is:** The Gold Standard was built using information from multiple clinical documents. The LLM only had access to the pathology report.

**Why it happens:** Some clinical variables — especially Surgical Margins and Extrathyroidal Extension — are determined by combining what the pathologist saw under the microscope with what the surgeon saw during the operation. The operative note lives in a different system. The LLM was only given one piece of the puzzle.

**Examples from your data:**
- *Margins:* The pathology report said "positive margins" (R1 — microscopic residual tumor). But the Gold Standard recorded R2 (macroscopic residual), which meant the surgeon had documented visible tumor left behind in the operative note. The model read the pathology report perfectly. It just didn't have the surgeon's note.
- *ETE:* In one case, the ETE field in the report was vague, but positive margins on an unencapsulated tumor strongly implied microscopic extension. The Gold Standard inferred this. The model did not, because the inference required clinical reasoning across fields, not just reading one section.

**The fix:** This one is partially a data pipeline issue. If the goal is to match GDC Gold Standards exactly, the input needs to include operative notes alongside pathology reports. If the goal is to extract what the pathology report actually says, then the Gold Standard comparison needs to account for this gap. Either way, it is knowable and addressable.

### 3. Salience Bias

**What it is:** When a report contains competing terms or entities, the LLM gravitates toward the rarer, more specific, or more prominent one — even when the correct answer is the mundane one.

**Why it happens:** LLMs are pattern-matching engines. Rare, specific terms like "Follicular" or "Tall Cell" carry more signal weight in training data than generic terms like "Classical." When both appear in the same sentence, the model pulls toward the distinctive one.

**Examples from your data:**
- *Histologic Variant:* A report noted "papillary carcinoma, classical" in the header, but mentioned a small secondary focus of "tall cell variant" later in the notes. The model flagged Tall Cell for the whole case. The Gold Standard coded only the dominant (largest) tumor.
- *Tumor Size:* The model occasionally extracted a measurement belonging to a benign nodule or a thyroid lobe rather than the malignant tumor, because the wrong number happened to be closer to or more salient than the correct one in the text.
- *ETE:* Template boilerplate in some reports included language like "tumor invades muscle" as an unedited form field. The model read it as a clinical finding. The actual finding was in the structured synoptic table further down.

**The fix:** Prompt design can help — being more explicit about which section of the report to prioritize, and telling the model to ignore template language. But this category also benefits from a human-in-the-loop review step, especially for variables where salience conflicts are common.

---

## What to Emphasize on Your Poster

The audience will be a mix of clinicians, researchers, and data people. Here is what each group will care about:

**Clinicians** want to know: Can this actually replace manual abstraction? The answer is yes, for the straightforward fields, with human review for the edge cases. And most of the edge cases are fixable.

**Researchers** want to know: How reliable is this data if I use it for a study? The answer is: very reliable for most variables, with known and documented limitations on Tumor Site and Margins that can be flagged or corrected.

**Data people** want to know: What does the pipeline look like and what does it cost? The answer: open-weight models, runs locally, no API fees, no data leaves the hospital. The main investment is prompt refinement.

---

## Anticipated Questions and How to Answer Them

**"Why not just use ChatGPT?"**
Privacy and cost. Sending 16,000 patient reports to an external API is a HIPAA risk and costs money per token at scale. Running a 32B model locally is essentially free after setup and keeps everything on our servers.

**"Isn't 90% accuracy too low for clinical use?"**
It depends on the use case. For research database population — which is what this is — 90%+ with documented, predictable error patterns is a massive improvement over manual abstraction. The errors are not random; they are systematic and reviewable. A human reviewer can focus on the known problem areas instead of reading every single report.

**"Why does the biggest model not do the best?"**
This is actually the most interesting finding. Bigger models have more general knowledge, but this task doesn't require general knowledge. It requires following specific extraction rules precisely. A well-prompted mid-sized model does that just as well. The bottleneck is the prompt, not the model.

**"What would you do next?"**
Two things. First, refine the prompts to explicitly include the registry conventions that caused the Definition Alignment errors — especially the Dominant Nodule Rule for Tumor Site. Second, test whether including operative notes alongside pathology reports closes the Context Boundary gap for Margins and ETE.

---

## A Note on the Gold Standard

This is worth mentioning on your poster or in conversation, because it affects how people interpret the results. The GDC Gold Standard was not built for this exact task. It was designed as a comprehensive clinical metadata record, not as an extraction benchmark for pathology reports alone. Some of the "errors" in this study are actually cases where the model's output is defensible — or even more faithful to the source text — but doesn't match what the Gold Standard recorded for other reasons. That doesn't make the Gold Standard wrong. It just means the comparison has inherent limits, and those limits are themselves informative.
