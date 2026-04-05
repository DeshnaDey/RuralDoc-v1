"""
tools.py — Diagnostic tool catalogue for MedicalDiagnosisEnv.

Each tool entry describes a single diagnostic procedure available at a rural
Indian Primary Health Centre (PHC).

Structure of each entry:
    {
        "name":        str   — canonical test_name used in actions
        "display":     str   — human-readable label
        "cost":        float — cost in scenario budget units
        "time_days":   int   — days the result takes (1 = same day)
        "category":    str   — "bedside" | "lab" | "rdt" | "imaging"
        "description": str   — what the test involves
        "diseases":    list[str] — primary diseases this test helps diagnose
    }

Public helpers:
    get_tool(name)               -> dict | None
    tools_for_disease(disease)   -> list[dict]
    affordable_tools(budget)     -> list[dict]
    tools_by_category(category)  -> list[dict]
"""

from __future__ import annotations

TOOLS: dict[str, dict] = {
    # ── Bedside / physical ────────────────────────────────────────────────────
    "thermometer_check": {
        "name":        "thermometer_check",
        "display":     "Thermometer Check",
        "cost":        1.0,
        "time_days":   1,
        "category":    "bedside",
        "description": "Oral/axillary temperature measurement to confirm fever.",
        "diseases":    ["malaria", "typhoid", "dengue", "tuberculosis", "sepsis"],
    },
    "skin_examination": {
        "name":        "skin_examination",
        "display":     "Skin Examination",
        "cost":        1.0,
        "time_days":   1,
        "category":    "bedside",
        "description": "Visual inspection for rashes, jaundice, pallor, or lesions.",
        "diseases":    ["dengue", "typhoid", "hepatitis_b", "leprosy"],
    },
    "chest_auscultation": {
        "name":        "chest_auscultation",
        "display":     "Chest Auscultation",
        "cost":        1.0,
        "time_days":   1,
        "category":    "bedside",
        "description": "Stethoscope examination of breath sounds for crackles or wheezing.",
        "diseases":    ["tuberculosis", "pneumonia", "asthma"],
    },
    "pulse_oximeter": {
        "name":        "pulse_oximeter",
        "display":     "Pulse Oximeter (SpO₂)",
        "cost":        1.0,
        "time_days":   1,
        "category":    "bedside",
        "description": "Fingertip SpO₂ and heart rate measurement.",
        "diseases":    ["tuberculosis", "pneumonia", "malaria", "sepsis"],
    },
    "ecg": {
        "name":        "ecg",
        "display":     "ECG (12-lead)",
        "cost":        3.0,
        "time_days":   1,
        "category":    "bedside",
        "description": "Electrocardiogram to assess cardiac rhythm and ischaemia.",
        "diseases":    ["sepsis", "poisoning", "electrolyte_disorder"],
    },

    # ── Rapid diagnostic tests (RDT) ──────────────────────────────────────────
    "rapid_malaria_test": {
        "name":        "rapid_malaria_test",
        "display":     "Rapid Malaria RDT",
        "cost":        2.0,
        "time_days":   1,
        "category":    "rdt",
        "description": "HRP2/pLDH antigen strip test for P. falciparum and P. vivax.",
        "diseases":    ["malaria"],
    },
    "dengue_ns1_test": {
        "name":        "dengue_ns1_test",
        "display":     "Dengue NS1 Antigen RDT",
        "cost":        3.0,
        "time_days":   1,
        "category":    "rdt",
        "description": "NS1 antigen rapid test; positive in first 5 days of dengue.",
        "diseases":    ["dengue"],
    },
    "hepatitis_b_rdt": {
        "name":        "hepatitis_b_rdt",
        "display":     "Hepatitis B Surface Antigen RDT",
        "cost":        3.0,
        "time_days":   1,
        "category":    "rdt",
        "description": "HBsAg strip test for Hepatitis B infection.",
        "diseases":    ["hepatitis_b"],
    },
    "blood_glucose": {
        "name":        "blood_glucose",
        "display":     "Blood Glucose (glucometer)",
        "cost":        1.0,
        "time_days":   1,
        "category":    "rdt",
        "description": "Fingerprick capillary glucose to screen for diabetes/hypoglycaemia.",
        "diseases":    ["diabetes", "hypoglycaemia", "sepsis"],
    },

    # ── Lab tests ─────────────────────────────────────────────────────────────
    "blood_panel": {
        "name":        "blood_panel",
        "display":     "Full Blood Panel (CBC + ESR)",
        "cost":        5.0,
        "time_days":   1,
        "category":    "lab",
        "description": (
            "Complete blood count with differential and erythrocyte "
            "sedimentation rate.  Flags anaemia, leukocytosis, thrombocytopaenia."
        ),
        "diseases":    [
            "malaria", "typhoid", "tuberculosis", "dengue",
            "leukemia", "sepsis", "anaemia",
        ],
    },
    "sputum_smear": {
        "name":        "sputum_smear",
        "display":     "Sputum Smear Microscopy (AFB)",
        "cost":        6.0,
        "time_days":   2,
        "category":    "lab",
        "description": (
            "Ziehl-Neelsen staining of morning sputum to detect "
            "acid-fast bacilli (TB diagnosis)."
        ),
        "diseases":    ["tuberculosis"],
    },
    "widal_test": {
        "name":        "widal_test",
        "display":     "Widal Agglutination Test",
        "cost":        4.0,
        "time_days":   1,
        "category":    "lab",
        "description": (
            "Serological test for Salmonella typhi O and H antibodies; "
            "titre ≥ 1:160 is suggestive of typhoid."
        ),
        "diseases":    ["typhoid"],
    },
    "urine_dipstick": {
        "name":        "urine_dipstick",
        "display":     "Urine Dipstick",
        "cost":        2.0,
        "time_days":   1,
        "category":    "lab",
        "description": "10-parameter dipstick for protein, glucose, nitrites, leucocytes, blood.",
        "diseases":    ["uti", "renal_disease", "diabetes", "hepatitis_b"],
    },
    "stool_microscopy": {
        "name":        "stool_microscopy",
        "display":     "Stool Microscopy (ova & parasites)",
        "cost":        4.0,
        "time_days":   2,
        "category":    "lab",
        "description": "Wet-mount and formal-ether concentration for helminth ova and protozoa.",
        "diseases":    ["amoebiasis", "giardiasis", "typhoid", "dysentery"],
    },
    "blood_culture": {
        "name":        "blood_culture",
        "display":     "Blood Culture & Sensitivity",
        "cost":        8.0,
        "time_days":   3,
        "category":    "lab",
        "description": (
            "Gold-standard for bacteraemia; typically 48–72 h incubation. "
            "Confirms Salmonella in typhoid and Gram-negative sepsis."
        ),
        "diseases":    ["typhoid", "sepsis", "brucellosis"],
    },
}


# ── Public helpers ────────────────────────────────────────────────────────────

def get_tool(name: str) -> dict | None:
    """Return the tool entry for *name*, or None if not found."""
    return TOOLS.get(name)


def tools_for_disease(disease: str) -> list[dict]:
    """Return all tools whose 'diseases' list includes *disease* (case-insensitive)."""
    disease_lower = disease.lower()
    return [t for t in TOOLS.values() if disease_lower in [d.lower() for d in t["diseases"]]]


def affordable_tools(budget: float) -> list[dict]:
    """Return all tools whose cost is ≤ *budget*."""
    return [t for t in TOOLS.values() if t["cost"] <= budget]


def tools_by_category(category: str) -> list[dict]:
    """Return all tools in the given category (bedside | lab | rdt | imaging)."""
    return [t for t in TOOLS.values() if t["category"] == category]


# ── Smoke test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Total tools: {len(TOOLS)}")
    print()

    # All tools tabulated
    print(f"{'Name':<26} {'Category':<10} {'Cost':>5}  {'Time':>4}  Diseases")
    print("-" * 80)
    for t in TOOLS.values():
        diseases = ", ".join(t["diseases"][:3])
        if len(t["diseases"]) > 3:
            diseases += f" (+{len(t['diseases'])-3})"
        print(f"{t['name']:<26} {t['category']:<10} {t['cost']:>5.1f}  {t['time_days']:>3}d  {diseases}")

    print()
    print("Affordable on budget=5.0:", [t["name"] for t in affordable_tools(5.0)])
    print()
    print("Tools for tuberculosis:", [t["name"] for t in tools_for_disease("tuberculosis")])
    print()
    print("Bedside tools:", [t["name"] for t in tools_by_category("bedside")])


# ── Additional scenario tools (added to ensure full coverage) ─────────────────

TOOLS["bp_measurement"] = {
    "name":        "bp_measurement",
    "display":     "Blood Pressure Measurement",
    "cost":        1.0,
    "time_days":   1,
    "category":    "bedside",
    "description": "Sphygmomanometer BP reading (systolic/diastolic).",
    "diseases":    ["hypertension", "sepsis", "dengue", "pre_eclampsia"],
}

TOOLS["blood_glucose_strip"] = {
    "name":        "blood_glucose_strip",
    "display":     "Blood Glucose Strip Test",
    "cost":        4.0,
    "time_days":   1,
    "category":    "rdt",
    "description": "Semiquantitative glucose strip for diabetes screening.",
    "diseases":    ["diabetes", "hypoglycaemia"],
}

TOOLS["hemoglobin_strip"] = {
    "name":        "hemoglobin_strip",
    "display":     "Hemoglobin Strip (HemoCue)",
    "cost":        4.0,
    "time_days":   1,
    "category":    "rdt",
    "description": "Point-of-care haemoglobin measurement for anaemia screening.",
    "diseases":    ["anaemia", "malaria", "hookworm"],
}

TOOLS["tourniquet_test"] = {
    "name":        "tourniquet_test",
    "display":     "Tourniquet Test (Rumple-Leede)",
    "cost":        1.0,
    "time_days":   1,
    "category":    "bedside",
    "description": "BP cuff test for capillary fragility; positive in dengue thrombocytopaenia.",
    "diseases":    ["dengue"],
}

TOOLS["rapid_dengue_test"] = {
    "name":        "rapid_dengue_test",
    "display":     "Rapid Dengue RDT (NS1 + IgM/IgG combo)",
    "cost":        5.0,
    "time_days":   1,
    "category":    "rdt",
    "description": "Combination NS1 antigen and IgM/IgG antibody strip for dengue.",
    "diseases":    ["dengue"],
}

TOOLS["abdominal_exam"] = {
    "name":        "abdominal_exam",
    "display":     "Abdominal Examination",
    "cost":        1.0,
    "time_days":   1,
    "category":    "bedside",
    "description": "Palpation for hepatosplenomegaly, tenderness, guarding.",
    "diseases":    ["typhoid", "hepatitis_b", "malaria", "amoebiasis"],
}
