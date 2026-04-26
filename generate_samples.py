"""
MediAssist AI — generate_samples.py
Generates synthetic lab report PDFs for local testing.
Run once:  python generate_samples.py

Uses only the standard library + fpdf2 (pip install fpdf2)
No real patient data used — all values are synthetic.
"""

import os
import random

try:
    from fpdf import FPDF
    FPDF_OK = True
except ImportError:
    FPDF_OK = False
    print("fpdf2 not installed. Run: pip install fpdf2")

# ──────────────────────────────────────────────
#  SYNTHETIC PATIENT TEMPLATES
# ──────────────────────────────────────────────
PATIENTS = [
    {
        "name": "Arun Sharma",
        "age": 34, "gender": "Male",
        "report_type": "Complete Blood Count (CBC)",
        "tests": [
            ("Hemoglobin",  "10.2",  "g/dL",     "12.0–16.0"),   # Low
            ("RBC",         "3.8",   "M/uL",     "4.0–6.0"),     # Low
            ("WBC",         "13200", "cells/uL", "4000–11000"),  # High
            ("Platelets",   "210000","cells/uL", "150000–450000"),
            ("Hematocrit",  "34.5",  "%",        "36.0–50.0"),   # Low
            ("MCV",         "72",    "fL",       "80–100"),      # Low
            ("MCH",         "24",    "pg",       "27–33"),       # Low
            ("MCHC",        "31",    "g/dL",     "31.5–36"),
        ]
    },
    {
        "name": "Priya Nair",
        "age": 52, "gender": "Female",
        "report_type": "Lipid Profile & Blood Sugar",
        "tests": [
            ("Glucose",         "176",  "mg/dL", "70–110"),      # High
            ("HbA1c",           "7.2",  "%",     "4.0–5.7"),     # High
            ("Cholesterol",     "245",  "mg/dL", "0–200"),       # High
            ("HDL",             "38",   "mg/dL", "40–999"),      # Low
            ("LDL",             "162",  "mg/dL", "0–100"),       # High
            ("Triglycerides",   "195",  "mg/dL", "0–150"),       # High
        ]
    },
    {
        "name": "Ramesh Kumar",
        "age": 45, "gender": "Male",
        "report_type": "Liver Function Test (LFT)",
        "tests": [
            ("SGOT",        "72",   "U/L",    "0–40"),    # High
            ("SGPT",        "88",   "U/L",    "0–40"),    # High
            ("Albumin",     "3.8",  "g/dL",   "3.4–5.4"),
            ("Bilirubin",   "1.8",  "mg/dL",  "0–1.2"),   # High
        ]
    },
    {
        "name": "Sunita Reddy",
        "age": 29, "gender": "Female",
        "report_type": "Thyroid Function Test (TFT)",
        "tests": [
            ("TSH",  "7.8", "mIU/L",  "0.4–4.0"),   # High
            ("T3",   "72",  "ng/dL",  "80–200"),     # Low
            ("T4",   "5.2", "ug/dL",  "4.5–12.5"),
        ]
    },
    {
        "name": "Vikram Iyer",
        "age": 61, "gender": "Male",
        "report_type": "Kidney Function Test (KFT)",
        "tests": [
            ("Creatinine",  "1.9",  "mg/dL", "0.6–1.2"),  # High
            ("Urea",        "42",   "mg/dL", "7–20"),      # High
            ("BUN",         "21",   "mg/dL", "7–20"),      # High
            ("Uric Acid",   "7.8",  "mg/dL", "2.5–7.0"),  # High
            ("Sodium",      "138",  "mEq/L", "136–145"),
            ("Potassium",   "4.2",  "mEq/L", "3.5–5.0"),
        ]
    },
]

LAB_NAME = "Bajaj Diagnostics & Health Labs"
DOCTOR   = "Dr. A. Mehta, MBBS, MD Pathology"

# ──────────────────────────────────────────────
#  PDF GENERATOR
# ──────────────────────────────────────────────
def generate_report_pdf(patient: dict, output_path: str):
    """Generate a synthetic lab report PDF for one patient."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Header ---
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 80, 160)
    pdf.cell(0, 10, LAB_NAME, align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "NABL Accredited | ISO 9001:2015 Certified", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Divider
    pdf.set_draw_color(30, 80, 160)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # --- Report Type ---
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 8, patient["report_type"], align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # --- Patient Info ---
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    info_items = [
        ("Patient Name", patient["name"]),
        ("Age / Gender",  f"{patient['age']} yrs / {patient['gender']}"),
        ("Referring Doctor", DOCTOR),
        ("Sample Type",  "Venous Blood"),
        ("Sample Collected", "07:30 AM"),
        ("Report Date",  "2024-03-15"),
    ]
    for label, value in info_items:
        pdf.cell(55, 7, f"{label}:", border=0)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)

    pdf.ln(4)

    # Divider
    pdf.set_line_width(0.4)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # --- Table Header ---
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(220, 230, 245)
    pdf.set_text_color(20, 20, 80)
    col_w = [65, 30, 30, 55]
    headers = ["Test Name", "Result", "Unit", "Reference Range"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, border=1, fill=True)
    pdf.ln()

    # --- Table Rows ---
    pdf.set_font("Helvetica", "", 10)
    for test, value, unit, ref in patient["tests"]:
        # Determine if flagged
        try:
            low_str, high_str = ref.split("–")
            is_low  = float(value.replace(",","")) < float(low_str)
            is_high = float(value.replace(",","")) > float(high_str)
        except Exception:
            is_low = is_high = False

        if is_high:
            pdf.set_text_color(180, 0, 0)
            display_val = f"{value} H"
        elif is_low:
            pdf.set_text_color(180, 120, 0)
            display_val = f"{value} L"
        else:
            pdf.set_text_color(0, 120, 0)
            display_val = value

        pdf.set_fill_color(255, 255, 255)
        pdf.cell(col_w[0], 7, test,        border=1)
        pdf.cell(col_w[1], 7, display_val, border=1)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(col_w[2], 7, unit,        border=1)
        pdf.cell(col_w[3], 7, ref,         border=1)
        pdf.ln()

    pdf.ln(6)

    # --- Footer ---
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5, (
        "DISCLAIMER: This report is for informational purposes only and does not constitute "
        "medical advice. Please consult your physician for interpretation and treatment decisions."
    ))
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 80, 160)
    pdf.cell(0, 5, f"Verified by: {DOCTOR}", new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)
    print(f"  ✅ Created: {output_path}")


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────
if __name__ == "__main__":
    if not FPDF_OK:
        print("\n❌ Cannot generate reports. Run:  pip install fpdf2\n")
        exit(1)

    os.makedirs("sample_reports", exist_ok=True)
    print("\n🏥 Generating synthetic MediAssist sample reports...\n")

    for p in PATIENTS:
        safe_name = p["name"].replace(" ", "_").lower()
        fname = f"sample_reports/{safe_name}_{p['report_type'].split('(')[0].strip().replace(' ','_').lower()}.pdf"
        generate_report_pdf(p, fname)

    print(f"\n✅ Done! {len(PATIENTS)} sample reports saved in sample_reports/\n")
    print("📌 Now run:  streamlit run app.py")
    print("   Then select a sample from the sidebar.\n")