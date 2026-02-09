"""
Field-specific prompts for confidence calibration experiment.
Each field has its own focused prompt with confidence scoring instructions.
"""

# =============================================================================
# CONFIDENCE CALIBRATION INSTRUCTIONS (Easy to edit)
# =============================================================================
# These instructions are appended to each field prompt to guide confidence scoring.
# Edit this section to adjust how the model assesses its confidence.

CONFIDENCE_INSTRUCTIONS = """
CONFIDENCE CALIBRATION:
Return your confidence level as "High", "Medium", or "Low" determining wether this needs to be reviewed by a human or not:
- High: The information is clearly stated and unambiguous; no human review needed
- Medium: The information is present but requires difficult interpretation or has some ambiguity; may require human  
- Low: The information is unclear, conflicting, or missing; requires human review

Provide concise reasoning (1-2 sentences) explaining your confidence choice.
"""

# =============================================================================
# FIELD-SPECIFIC CONFIGURATIONS
# =============================================================================

FIELD_CONFIGS = {
    "histologic_variant": {
        "prompt": """Extract the histologic variant from this thyroid pathology report.

EXTRACTION RULES:
1. Options: "Classical" | "Follicular" | "Tall Cell"
2. Extract variant ONLY from the final diagnosis line, NOT from microscopic descriptions
3. "Follicular/Tall Cell features" or "architecture" → ignore (these describe cellular patterns, not the variant)
4. If multiple variants mentioned, use the one in the PRIMARY/DOMINANT tumor only
5. DEFAULT: If diagnosis says "Papillary Thyroid Carcinoma" without specifying variant → "Classical"

Return a JSON object with exactly these keys:
{{
  "value": "the extracted value",
  "confidence": "High" | "Medium" | "Low",
  "reasoning": "brief explanation"
}}
"""
        + CONFIDENCE_INSTRUCTIONS,
        "type": "categorical",
        "options": ["Classical", "Follicular", "Tall Cell"],
    },
    "tumor_site": {
        "prompt": """Extract the tumor site following The Bilateral Rule.

EXTRACTION RULES (The Bilateral Rule):
1. Options: "Right lobe" | "Left lobe" | "Isthmus" | "Bilateral"
2. Identify the location of the DOMINANT nodule (e.g., Right Lobe)
3. Check for clinically significant carcinoma (>1cm) in the contralateral lobe
4. If carcinoma is present in BOTH lobes → Output "Bilateral"
5. Otherwise, output the site of the dominant nodule
6. Only use "Isthmus" if the dominant center is the isthmus

Return a JSON object with exactly these keys:
{{
  "value": "the extracted value",
  "confidence": "High" | "Medium" | "Low",
  "reasoning": "brief explanation"
}}
"""
        + CONFIDENCE_INSTRUCTIONS,
        "type": "categorical",
        "options": ["Right lobe", "Left lobe", "Isthmus", "Bilateral"],
    },
    "extrathyroidal_extension": {
        "prompt": """Extract the extrathyroidal extension status.

EXTRACTION RULES:
1. Options: "No ETE" | "Microscopic" | "Gross"
2. Check Synoptic table first and trust the descriptive text over the TNM stage code (as staging criteria vary by year)
3. "Not identified", "Absent", "Intrathyroidal", "Confined/limited to thyroid" → "No ETE"
4. "Present", "Identified", "Microscopic extension", "Invades fat/soft tissue" → "Microscopic"
5. "Gross extension", "Macroscopic", "Invades strap muscles/trachea" → "Gross"

Return a JSON object with exactly these keys:
{{
  "value": "the extracted value",
  "confidence": "High" | "Medium" | "Low",
  "reasoning": "brief explanation"
}}
"""
        + CONFIDENCE_INSTRUCTIONS,
        "type": "categorical",
        "options": ["No ETE", "Microscopic", "Gross"],
    },
    "margins": {
        "prompt": """Extract the margin status.

EXTRACTION RULES:
1. Options: "R0" | "R1" | "R2"
2. "Uninvolved", "Negative", "Clear", or if no involvement is mentioned → "R0" (even if close)
3. "Involved", "Positive", or "Focal involvement" → "R1"
4. "Gross residual" → "R2"

Return a JSON object with exactly these keys:
{{
  "value": "the extracted value",
  "confidence": "High" | "Medium" | "Low",
  "reasoning": "brief explanation"
}}
"""
        + CONFIDENCE_INSTRUCTIONS,
        "type": "categorical",
        "options": ["R0", "R1", "R2"],
    },
    "tumor_size": {
        "prompt": """Extract the tumor size in centimeters.

EXTRACTION RULES (Header Priority):
1. Type: Float (cm)
2. Use Synoptic Data / Final Diagnosis for the DOMINANT (largest) tumor
3. EXCEPTION: If Diagnosis uses the term "Microcarcinoma" AND Gross Description measures the same nodule as ≥1.0 cm, use the Gross measurement
4. Convert mm to cm (divide by 10)

Return a JSON object with exactly these keys:
{{
  "value": <float>,
  "confidence": "High" | "Medium" | "Low",
  "reasoning": "brief explanation"
}}
"""
        + CONFIDENCE_INSTRUCTIONS,
        "type": "numeric",
    },
}

# Field order for consistent processing
FIELD_ORDER = [
    "histologic_variant",
    "tumor_site",
    "extrathyroidal_extension",
    "margins",
    "tumor_size",
]


def get_field_prompt(field_name: str) -> str:
    """Get the prompt for a specific field."""
    if field_name not in FIELD_CONFIGS:
        raise ValueError(f"Unknown field: {field_name}")
    return FIELD_CONFIGS[field_name]["prompt"]


def get_all_fields() -> list:
    """Get list of all field names in order."""
    return FIELD_ORDER


def get_field_type(field_name: str) -> str:
    """Get the type of a field (categorical or numeric)."""
    if field_name not in FIELD_CONFIGS:
        raise ValueError(f"Unknown field: {field_name}")
    return FIELD_CONFIGS[field_name]["type"]


def get_field_options(field_name: str) -> list:
    """Get valid options for a categorical field."""
    if field_name not in FIELD_CONFIGS:
        raise ValueError(f"Unknown field: {field_name}")
    return FIELD_CONFIGS[field_name].get("options", [])
