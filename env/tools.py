from typing import Dict, Any, List

# ─────────────────────────────────────────────────────────────────────────────
#  DIAGNOSTIC TOOLS DEFINITION
#  These costs perfectly match the test_costs defined in scenarios/scenario2.py
# ─────────────────────────────────────────────────────────────────────────────

diagnostic_tools: Dict[str, Dict[str, Any]] = {
    # ─── COST 1 (Instant / Basic Clinical Skills) ─────────────────────────────
    "thermometer_check": {"cost": 1, "category": "vitals", "display_name": "Thermometer Check", "reveals": "Precise body temperature reading"},
    "skin_examination": {"cost": 1, "category": "clinical_exam", "display_name": "Skin & Mucosal Examination", "reveals": "Rash type, pallor, jaundice, cyanosis, oedema, petechiae"},
    "chest_auscultation": {"cost": 1, "category": "clinical_exam", "display_name": "Chest Auscultation", "reveals": "Lung sounds - crackles, wheeze, reduced breath sounds"},
    "abdominal_exam": {"cost": 1, "category": "clinical_exam", "display_name": "Abdominal Examination", "reveals": "Tenderness, organomegaly, distension, guarding"},
    "bp_measurement": {"cost": 1, "category": "vitals", "display_name": "Blood Pressure Measurement", "reveals": "Systolic and diastolic blood pressure"},
    "tourniquet_test": {"cost": 1, "category": "clinical_exam", "display_name": "Tourniquet Test", "reveals": "Capillary fragility - dengue haemorrhagic indicator"},

    # ─── COST 2 (Basic Bedside Devices) ───────────────────────────────────────
    "pulse_oximeter": {"cost": 2, "category": "vitals", "display_name": "Pulse Oximeter", "reveals": "SpO2 oxygen saturation and pulse rate"},
    "urine_dipstick": {"cost": 2, "category": "rapid_test", "display_name": "Urine Dipstick", "reveals": "Protein, glucose, blood, bilirubin, leukocytes"},

    # ─── COST 3 (Standard Rapid Kits) ─────────────────────────────────────────
    "rapid_malaria_test": {"cost": 3, "category": "rapid_test", "display_name": "Rapid Malaria Antigen Test (RDT)", "reveals": "Positive or negative for malaria antigens (P.vivax/P.falciparum)"},

    # ─── COST 4 (Point of Care Blood Drops) ───────────────────────────────────
    "blood_glucose_strip": {"cost": 4, "category": "rapid_test", "display_name": "Blood Glucose Strip", "reveals": "Random blood sugar level"},
    "hemoglobin_strip": {"cost": 4, "category": "rapid_test", "display_name": "Hemoglobin Color Scale", "reveals": "Haemoglobin level - anaemia check"},

    # ─── COST 5 (Complex Serology & Blood Draws) ──────────────────────────────
    "blood_panel": {"cost": 5, "category": "lab_test", "display_name": "Basic Blood Panel (CBC)", "reveals": "CBC - WBC, RBC, platelets, differential, ESR"},
    "rapid_dengue_test": {"cost": 5, "category": "rapid_test", "display_name": "Dengue NS1 & IgM/IgG Rapid Test", "reveals": "NS1 antigen, IgM and IgG antibodies for dengue"},
    "widal_test": {"cost": 5, "category": "lab_test", "display_name": "Widal Tube Agglutination Test", "reveals": "Typhoid antibody titres (TO and TH)"},

    # ─── COST 6 (Time-Intensive Microscopy) ───────────────────────────────────
    "sputum_smear": {"cost": 6, "category": "lab_test", "display_name": "Sputum Smear Microscopy (AFB)", "reveals": "AFB stain for tuberculosis - slow but conclusive"}
}

# ─────────────────────────────────────────────────────────────────────────────
#  Exported Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def get_tool_cost(tool_name: str) -> int:
    """Returns the time/budget cost of a given tool. Returns 0 if invalid."""
    return diagnostic_tools.get(tool_name, {}).get("cost", 0)

def is_valid_tool(tool_name: str) -> bool:
    """Checks if the tool exists in the master toolkit."""
    return tool_name in diagnostic_tools

def get_all_tool_names() -> List[str]:
    """Returns a list of all valid action keys for validation."""
    return list(diagnostic_tools.keys())