
import re

def normalize_text(val):
    if val is None:
        return None
    return str(val).lower().strip()

def normalize_histologic_variant(val):
    s = normalize_text(val)
    if not s or s in ["null", "none", "not available", "nan"]:
        return None
    
    # Map common variations
    if "papillary" in s and "structural" not in s and "variant" not in s: 
        # Sometimes model says "Papillary Thyroid Carcinoma" for variant
        return "Classical" 
    if "classic" in s or "usual" in s or "conventional" in s:
        return "Classical"
    if "follicular" in s or "fvptc" in s:
        return "Follicular"
    if "tall" in s:
        return "Tall Cell"
    if "columnar" in s:
        return "Columnar Cell"
        
    return s.title()

def normalize_ete(val):
    s = normalize_text(val)
    if not s or s in ["null", "none", "(null)"]:
        return "No ETE" # Default assumption if missing? Or return None. Detailed prompt handles this.
        
    if "no" in s or "none" in s or "encapsulated" in s or "confined" in s:
        return "No ETE"
    if "gross" in s or "macroscopic" in s or "strap" in s or "trachea" in s:
        return "Gross"
    if "micro" in s or "minimal" in s or "focal" in s:
        return "Microscopic"
        
    # Fallback if just "extension" usually Micro per rules, but LLM should have handled it.
    if "present" in s:
        return "Microscopic" 
        
    return "No ETE" # Conservative default

def normalize_margins(val):
    s = normalize_text(val)
    if not s: return None
    
    if "r0" in s or "negative" in s or "clear" in s or "uninvolved" in s:
        return "R0"
    if "r2" in s or "gross" in s:
        return "R2"
    if "r1" in s or "micro" in s or "focal" in s:
        return "R1"
        
    return "R0" # Most common

def normalize_site(val):
    """Normalize tumor site to: Right lobe, Left lobe, Isthmus, Bilateral"""
    s = normalize_text(val)
    if not s: return None
    
    if "bilateral" in s or ("right" in s and "left" in s):
        return "Bilateral"
    if "isthmus" in s:
        return "Isthmus" # Per user rule: if Isthmus mentioned, prefer it unless Bilateral explicitly
    if "right" in s:
        return "Right lobe"
    if "left" in s:
        return "Left lobe"
        
    return None

def normalize_numeric_float(val):
    if val is None: return None
    try:
        # Extract first float
        match = re.search(r"[-+]?\d*\.\d+|\d+", str(val))
        if match:
            return float(match.group())
    except:
        pass
    return None

def normalize_numeric_int(val):
    if val is None: return None
    try:
        match = re.search(r"\d+", str(val))
        if match:
            return int(match.group())
    except:
        pass
    return None
