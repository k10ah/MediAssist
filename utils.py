"""
MediAssist AI — Clinical Report Summarizer
utils.py  |  OCR · NLP Parsing · Rule Engine
"""

import re
import os
import io
from typing import List, Dict, Any

# ──────────────────────────────────────────────
#  OPTIONAL IMPORTS (graceful fallback)
# ──────────────────────────────────────────────
try:
    import pdfplumber
    PDF_OK = True
except ImportError:
    PDF_OK = False

try:
    from PIL import Image
    import pytesseract
    OCR_OK = True
except ImportError:
    OCR_OK = False

# ══════════════════════════════════════════════
#  NORMAL RANGES  (units: standard lab units)
# ══════════════════════════════════════════════
NORMAL_RANGES: Dict[str, Dict] = {
    # CBC
    "Hemoglobin":       {"low": 12.0,  "high": 17.5,  "unit": "g/dL"},
    "RBC":              {"low": 4.0,   "high": 6.0,   "unit": "M/uL"},
    "WBC":              {"low": 4000,  "high": 11000, "unit": "cells/uL"},
    "Platelets":        {"low": 150000,"high": 450000,"unit": "/uL"},
    "Hematocrit":       {"low": 36.0,  "high": 50.0,  "unit": "%"},
    "MCV":              {"low": 80,    "high": 100,   "unit": "fL"},
    "MCH":              {"low": 27,    "high": 33,    "unit": "pg"},
    "MCHC":             {"low": 31.5,  "high": 36,    "unit": "g/dL"},
    # Metabolic
    "Glucose":          {"low": 70,    "high": 140,   "unit": "mg/dL"},
    "HbA1c":            {"low": 4.0,   "high": 5.7,   "unit": "%"},
    "Cholesterol":      {"low": 0,     "high": 200,   "unit": "mg/dL"},
    "HDL":              {"low": 40,    "high": 999,   "unit": "mg/dL"},
    "LDL":              {"low": 0,     "high": 100,   "unit": "mg/dL"},
    "Triglycerides":    {"low": 0,     "high": 150,   "unit": "mg/dL"},
    # Kidney
    "Creatinine":       {"low": 0.6,   "high": 1.2,   "unit": "mg/dL"},
    "Urea":             {"low": 7,     "high": 20,    "unit": "mg/dL"},
    "BUN":              {"low": 7,     "high": 20,    "unit": "mg/dL"},
    "Uric Acid":        {"low": 2.5,   "high": 7.0,   "unit": "mg/dL"},
    # Liver
    "SGOT":             {"low": 0,     "high": 40,    "unit": "U/L"},
    "SGPT":             {"low": 0,     "high": 40,    "unit": "U/L"},
    "AST":              {"low": 0,     "high": 40,    "unit": "U/L"},
    "ALT":              {"low": 0,     "high": 40,    "unit": "U/L"},
    "Bilirubin":        {"low": 0,     "high": 1.2,   "unit": "mg/dL"},
    "Albumin":          {"low": 3.4,   "high": 5.4,   "unit": "g/dL"},
    # Thyroid
    "TSH":              {"low": 0.4,   "high": 4.0,   "unit": "mIU/L"},
    "T3":               {"low": 80,    "high": 200,   "unit": "ng/dL"},
    "T4":               {"low": 4.5,   "high": 12.5,  "unit": "ug/dL"},
    # Electrolytes
    "Sodium":           {"low": 136,   "high": 145,   "unit": "mEq/L"},
    "Potassium":        {"low": 3.5,   "high": 5.0,   "unit": "mEq/L"},
    "Calcium":          {"low": 8.5,   "high": 10.5,  "unit": "mg/dL"},
    # Iron studies
    "Iron":             {"low": 60,    "high": 170,   "unit": "ug/dL"},
    "Ferritin":         {"low": 12,    "high": 300,   "unit": "ng/mL"},
}

# ══════════════════════════════════════════════
#  REGEX PATTERNS  — match "Test Name : value unit"
# ══════════════════════════════════════════════
# Keys = canonical name, values = list of regex aliases
PATTERNS: Dict[str, List[str]] = {
    "Hemoglobin":    [r"h[ae]moglobin", r"\bHb\b", r"\bHGB\b"],
    "RBC":           [r"\bRBC\b", r"red blood cell"],
    "WBC":           [r"\bWBC\b", r"white blood cell", r"leucocyte"],
    "Platelets":     [r"platelet", r"\bPLT\b"],
    "Hematocrit":    [r"hematocrit", r"\bHCT\b", r"\bPCV\b"],
    "MCV":           [r"\bMCV\b"],
    "MCH":           [r"\bMCH\b(?!C)"],
    "MCHC":          [r"\bMCHC\b"],
    "Glucose":       [r"\bglucose\b", r"\bsugar\b", r"\bblood sugar\b"],
    "HbA1c":         [r"hba1c", r"glycated", r"a1c"],
    "Cholesterol":   [r"\bcholesterol\b(?!\s*hdl)(?!\s*ldl)"],
    "HDL":           [r"\bHDL\b"],
    "LDL":           [r"\bLDL\b"],
    "Triglycerides": [r"triglyceride"],
    "Creatinine":    [r"creatinine"],
    "Urea":          [r"\burea\b"],
    "BUN":           [r"\bBUN\b", r"blood urea nitrogen"],
    "Uric Acid":     [r"uric acid"],
    "SGOT":          [r"\bSGOT\b"],
    "SGPT":          [r"\bSGPT\b"],
    "AST":           [r"\bAST\b"],
    "ALT":           [r"\bALT\b"],
    "Bilirubin":     [r"bilirubin(?!\s*direct)(?!\s*indirect)"],
    "Albumin":       [r"\balbumin\b"],
    "TSH":           [r"\bTSH\b", r"thyroid stimulating"],
    "T3":            [r"\bT3\b"],
    "T4":            [r"\bT4\b"],
    "Sodium":        [r"\bsodium\b", r"\bNa\b"],
    "Potassium":     [r"\bpotassium\b", r"\bK\b"],
    "Calcium":       [r"\bcalcium\b", r"\bCa\b"],
    "Iron":          [r"\biron\b(?!\s*binding)"],
    "Ferritin":      [r"\bferritin\b"],
}

# ══════════════════════════════════════════════
#  PDF TEXT EXTRACTION
# ══════════════════════════════════════════════
def extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    if not PDF_OK:
        return "[ERROR] pdfplumber not installed. Run: pip install pdfplumber"

    text_parts = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                # Also try table extraction
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            text_parts.append("  ".join([str(c) for c in row if c]))
    except Exception as e:
        return f"[PDF extraction error] {str(e)}"

    return "\n".join(text_parts)


# ══════════════════════════════════════════════
#  IMAGE OCR EXTRACTION
# ══════════════════════════════════════════════
def extract_image_text(file_bytes: bytes) -> str:
    """Extract text from image bytes using pytesseract OCR."""
    if not OCR_OK:
        return "[ERROR] pytesseract or Pillow not installed."

    try:
        image = Image.open(io.BytesIO(file_bytes))
        # Preprocess: convert to RGB, enhance contrast
        image = image.convert("RGB")

        # Try different OCR configs for best results on lab reports
        configs = [
            "--oem 3 --psm 6",   # Assume uniform block of text
            "--oem 3 --psm 4",   # Assume single column of varying-size text
        ]
        best_text = ""
        for cfg in configs:
            try:
                text = pytesseract.image_to_string(image, config=cfg)
                if len(text.strip()) > len(best_text.strip()):
                    best_text = text
            except Exception:
                continue

        return best_text if best_text.strip() else "[No text detected in image]"

    except Exception as e:
        return f"[OCR error] {str(e)}"


# ══════════════════════════════════════════════
#  NLP / REGEX BIOMARKER PARSER
# ══════════════════════════════════════════════
def parse_lab_values(text: str) -> Dict[str, float]:
    """
    Parse biomarker values from extracted text using regex.
    Returns: {test_name: numeric_value}
    """
    results: Dict[str, float] = {}

    # Normalise text
    clean = text.replace("\n", " ").replace("\t", " ")
    clean = re.sub(r"\s{2,}", " ", clean)

    for test_name, aliases in PATTERNS.items():
        for alias in aliases:
            # Pattern: test_name followed by optional separators and a number
            pattern = (
                r"(?i)" + alias +
                r"[\s:=\|\.]{0,5}"   # separator
                r"([\d,]+\.?\d*)"    # number (allow commas like 13,200)
            )
            match = re.search(pattern, clean)
            if match:
                raw_val = match.group(1).replace(",", "")
                try:
                    results[test_name] = float(raw_val)
                    break  # found for this test, move to next
                except ValueError:
                    continue

    return results


# ══════════════════════════════════════════════
#  RULE ENGINE — FLAG ABNORMAL VALUES
# ══════════════════════════════════════════════
def flag_abnormal(lab_values: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Compare parsed values against normal ranges.
    Returns list of dicts for DataFrame display.
    """
    flagged = []

    for test, value in lab_values.items():
        ranges = NORMAL_RANGES.get(test)
        if not ranges:
            status = "Unknown"
        elif value < ranges["low"]:
            status = "Low"
        elif value > ranges["high"]:
            status = "High"
        else:
            status = "Normal"

        unit = ranges["unit"] if ranges else ""

        flagged.append({
            "Test":         test,
            "Value":        value,
            "Unit":         unit,
            "Reference Low":  ranges["low"]  if ranges else "—",
            "Reference High": ranges["high"] if ranges else "—",
            "Status":       status,
        })

    # Sort: abnormal first
    order = {"High": 0, "Low": 1, "Normal": 2, "Unknown": 3}
    flagged.sort(key=lambda x: order.get(x["Status"], 4))

    return flagged


# ══════════════════════════════════════════════
#  LOAD SAMPLE REPORTS FROM FOLDER
# ══════════════════════════════════════════════
def load_sample_reports() -> List[str]:
    """Return list of PDF/image filenames from sample_reports/ folder."""
    folder = "sample_reports"
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
        return []

    supported = [".pdf", ".png", ".jpg", ".jpeg"]
    files = [
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in supported
    ]
    return sorted(files)


# ══════════════════════════════════════════════
#  HELPER — Get abnormal summary string for prompt
# ══════════════════════════════════════════════
def get_abnormal_summary(flagged: List[Dict]) -> str:
    """Return human-readable string of abnormal values for LLM prompt."""
    abnormals = [r for r in flagged if r["Status"] in ("High", "Low")]
    if not abnormals:
        return "All tested biomarkers appear within normal range."

    lines = []
    for r in abnormals:
        lines.append(
            f"- {r['Test']}: {r['Value']} {r['Unit']} ({r['Status']}, "
            f"normal: {r['Reference Low']}–{r['Reference High']} {r['Unit']})"
        )
    return "\n".join(lines)