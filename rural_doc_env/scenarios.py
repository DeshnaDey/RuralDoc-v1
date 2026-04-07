import copy

# ─────────────────────────────────────────────────────────────────────────────
#  SCENARIOS V2 — ALL 20 DISEASES
#  New fields: budget, test_costs, penalty_events, referral_destination
#  Every test_result entry has: result, info_gain, suggests, rules_out, memory_note
#  Rules enforced:
#    • Every test in master list appears in EVERY time period — no exceptions
#    • Phase-2 info_gain > Phase-1 (except conclusive_test = 1.0 in both phases)
#    • conclusive_test always info_gain = 1.0
#    • sum(test_costs.values()) < budget (tight but not impossible)
#    • memory_notes escalate in Phase 2 ("URGENT", "worsening", "escalating")
# ─────────────────────────────────────────────────────────────────────────────

scenarios_v2 = [

    # ═══════════════════════════════════════════════════════════════════════════
    # HARD | case_01 | Pulmonary Tuberculosis
    # Master: thermometer_check(1), skin_examination(1), chest_auscultation(1),
    #         pulse_oximeter(2), rapid_malaria_test(3), blood_panel(5), sputum_smear(6)
    # Total: 19 | Budget: 24
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_01",
        "difficulty_tier": "hard",
        "patient_demographics": {"age": 34, "gender": "male", "location": "Urban slum, Delhi"},
        "hidden_diagnosis": "tuberculosis",
        "budget": 24,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "chest_auscultation": 1,
            "pulse_oximeter": 2, "rapid_malaria_test": 3, "blood_panel": 5, "sputum_smear": 6
        },
        "relevant_tests": ["thermometer_check", "chest_auscultation", "sputum_smear"],
        "conclusive_test": "sputum_smear",
        "requires_referral": True,
        "referral_destination": "District Hospital (DOTS Centre)",
        "critical_window_days": 14,
        "penalty_events": {
            "hemoptysis_without_referral": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-7": {
                "symptoms": ["chronic cough for 3 weeks", "night sweats", "weight loss", "low-grade evening fever"],
                "vitals": {"temp": "37.9 C", "bp": "110/75", "hr": 88, "spo2": "96%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.9 C (Low-grade evening fever)",
                        "info_gain": 0.1,
                        "suggests": ["tuberculosis", "chronic_infection", "kala_azar"],
                        "rules_out": [],
                        "memory_note": "Low-grade evening fever 37.9C; consistent with TB chronicity but seen in many conditions — non-specific alone."
                    },
                    "chest_auscultation": {
                        "result": "Crepitations in the apical region of right lung",
                        "info_gain": 0.4,
                        "suggests": ["tuberculosis", "pneumonia"],
                        "rules_out": ["asthma", "copd"],
                        "memory_note": "Apical crepitations localised to right apex; strongly suspicious for pulmonary TB — sputum smear urgently indicated."
                    },
                    "sputum_smear": {
                        "result": "Positive for Acid-Fast Bacilli (AFB)",
                        "info_gain": 1.0,
                        "suggests": ["tuberculosis"],
                        "rules_out": ["pneumonia", "copd_exacerbation", "lung_cancer"],
                        "memory_note": "AFB-positive sputum smear; pulmonary tuberculosis confirmed — initiate DOTS referral immediately."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 96%, PR 88 bpm",
                        "info_gain": 0.1,
                        "suggests": [],
                        "rules_out": ["severe_respiratory_failure"],
                        "memory_note": "SpO2 96%; mild hypoxia present, no acute respiratory failure at this stage."
                    },
                    "blood_panel": {
                        "result": "Hb 10.8 g/dL, ESR 78 mm/hr, WBC 7,200/mcL",
                        "info_gain": 0.2,
                        "suggests": ["tuberculosis", "chronic_infection"],
                        "rules_out": [],
                        "memory_note": "Mild anaemia with markedly raised ESR (78 mm/hr); supports chronic granulomatous infection consistent with TB."
                    },
                    "rapid_malaria_test": {
                        "result": "Negative",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["malaria"],
                        "memory_note": "Malaria excluded by RDT; fever with night sweats not attributable to malarial infection."
                    },
                    "skin_examination": {
                        "result": "Mild wasting noted; no rash; no pallor",
                        "info_gain": 0.1,
                        "suggests": ["tuberculosis"],
                        "rules_out": ["dengue", "kala_azar"],
                        "memory_note": "Mild cachexia consistent with chronic TB illness; no cutaneous finding suggesting alternative diagnosis."
                    }
                }
            },
            "8-14": {
                "symptoms": ["chronic cough for 4 weeks", "blood-tinged sputum (hemoptysis)", "severe night sweats", "visible weight loss"],
                "vitals": {"temp": "38.2 C", "bp": "105/70", "hr": 95, "spo2": "94%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "38.2 C (Escalating fever)",
                        "info_gain": 0.2,
                        "suggests": ["tuberculosis", "tb_progression"],
                        "rules_out": [],
                        "memory_note": "Escalating evening fever to 38.2C; worsening TB systemic involvement alongside onset of hemoptysis."
                    },
                    "chest_auscultation": {
                        "result": "Worsening crepitations and reduced breath sounds right apex",
                        "info_gain": 0.5,
                        "suggests": ["tuberculosis", "tb_cavitation"],
                        "rules_out": ["asthma"],
                        "memory_note": "URGENT: Progressive apical consolidation with reduced breath sounds — cavitation advancing, parenchymal destruction worsening."
                    },
                    "sputum_smear": {
                        "result": "Positive for Acid-Fast Bacilli (AFB) — heavy bacillary load",
                        "info_gain": 1.0,
                        "suggests": ["tuberculosis"],
                        "rules_out": ["pneumonia", "copd_exacerbation"],
                        "memory_note": "URGENT: Persistently AFB-positive with escalating bacillary load and hemoptysis — active TB, immediate DOTS referral required."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 94%, PR 95 bpm",
                        "info_gain": 0.2,
                        "suggests": ["tuberculosis_progression"],
                        "rules_out": [],
                        "memory_note": "Worsening SpO2 to 94%; escalating respiratory compromise — referral to District Hospital now urgent."
                    },
                    "blood_panel": {
                        "result": "Hb 9.6 g/dL, ESR 102 mm/hr, WBC 8,100/mcL",
                        "info_gain": 0.3,
                        "suggests": ["tuberculosis", "tb_progression"],
                        "rules_out": [],
                        "memory_note": "Worsening anaemia and markedly elevated ESR (102 mm/hr); confirms active escalating TB with rising systemic inflammatory burden."
                    },
                    "rapid_malaria_test": {
                        "result": "Negative",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["malaria"],
                        "memory_note": "Malaria definitively excluded; clinical picture entirely explained by confirmed escalating pulmonary TB."
                    },
                    "skin_examination": {
                        "result": "Progressive wasting and pallor now visible; no rash",
                        "info_gain": 0.15,
                        "suggests": ["tuberculosis"],
                        "rules_out": [],
                        "memory_note": "Worsening pallor and visible cachexia; escalating TB-related wasting and anaemia now clinically apparent."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # EASY | case_02 | Type 2 Diabetes
    # Master: thermometer_check(1), bp_measurement(1), skin_examination(1),
    #         urine_dipstick(2), blood_glucose_strip(4)
    # Total: 9 | Budget: 12
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_02",
        "difficulty_tier": "easy",
        "patient_demographics": {"age": 52, "gender": "female", "location": "Semi-urban Maharashtra"},
        "hidden_diagnosis": "type_2_diabetes",
        "budget": 12,
        "test_costs": {
            "thermometer_check": 1, "bp_measurement": 1, "skin_examination": 1,
            "urine_dipstick": 2, "blood_glucose_strip": 4
        },
        "relevant_tests": ["blood_glucose_strip", "urine_dipstick"],
        "conclusive_test": "blood_glucose_strip",
        "requires_referral": False,
        "referral_destination": None,
        "critical_window_days": 30,
        "penalty_events": {
            "uncontrolled_hyperglycemia_missed": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-15": {
                "symptoms": ["frequent urination at night", "excessive thirst", "blurring of vision"],
                "vitals": {"temp": "36.8 C", "bp": "130/85", "hr": 78, "spo2": "99%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "36.8 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["malaria", "dengue", "infection"],
                        "memory_note": "Afebrile; acute febrile illness excluded as cause of polyuria and thirst."
                    },
                    "bp_measurement": {
                        "result": "130/85 mmHg (Stage 1 Hypertension)",
                        "info_gain": 0.2,
                        "suggests": ["hypertension", "type_2_diabetes"],
                        "rules_out": [],
                        "memory_note": "Borderline elevated BP; diabetic hypertension co-morbidity possible — blood glucose confirmation required."
                    },
                    "skin_examination": {
                        "result": "Darkening at nape and axilla — possible acanthosis nigricans",
                        "info_gain": 0.2,
                        "suggests": ["type_2_diabetes", "insulin_resistance"],
                        "rules_out": [],
                        "memory_note": "Suspicious skin darkening at neck folds; acanthosis nigricans raises insulin resistance concern."
                    },
                    "urine_dipstick": {
                        "result": "Glucose +++, Ketones Negative",
                        "info_gain": 0.5,
                        "suggests": ["type_2_diabetes"],
                        "rules_out": ["diabetic_ketoacidosis"],
                        "memory_note": "Glycosuria detected; strongly suggests hyperglycaemia — blood glucose confirmation required."
                    },
                    "blood_glucose_strip": {
                        "result": "Random Blood Sugar 285 mg/dL",
                        "info_gain": 1.0,
                        "suggests": ["type_2_diabetes"],
                        "rules_out": ["hypoglycemia", "normal_glucose"],
                        "memory_note": "RBS 285 mg/dL meets WHO diagnostic threshold; Type 2 diabetes confirmed — initiate metformin and lifestyle counselling."
                    }
                }
            },
            "16-30": {
                "symptoms": ["frequent urination at night", "excessive thirst", "blurring of vision", "new tingling in feet (neuropathy)"],
                "vitals": {"temp": "36.8 C", "bp": "135/85", "hr": 80, "spo2": "99%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "36.8 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["malaria", "infection"],
                        "memory_note": "Persistently afebrile; fever-based differential remains excluded."
                    },
                    "bp_measurement": {
                        "result": "135/85 mmHg (Worsening)",
                        "info_gain": 0.3,
                        "suggests": ["hypertension", "diabetic_nephropathy"],
                        "rules_out": [],
                        "memory_note": "Worsening BP trend; escalating hypertension may indicate early diabetic nephropathy — monitor renal function."
                    },
                    "skin_examination": {
                        "result": "Acanthosis nigricans confirmed at nape and both axillae",
                        "info_gain": 0.3,
                        "suggests": ["type_2_diabetes", "insulin_resistance"],
                        "rules_out": [],
                        "memory_note": "Worsening acanthosis nigricans now confirmed at multiple sites; escalating insulin resistance consistent with uncontrolled diabetes."
                    },
                    "urine_dipstick": {
                        "result": "Glucose +++, Ketones Negative, Protein Trace",
                        "info_gain": 0.6,
                        "suggests": ["type_2_diabetes", "diabetic_nephropathy"],
                        "rules_out": [],
                        "memory_note": "Escalating microproteinuria now present alongside persistent glycosuria; early diabetic nephropathy emerging."
                    },
                    "blood_glucose_strip": {
                        "result": "Random Blood Sugar 310 mg/dL",
                        "info_gain": 1.0,
                        "suggests": ["type_2_diabetes"],
                        "rules_out": [],
                        "memory_note": "URGENT: Worsening RBS to 310 mg/dL; uncontrolled diabetes with escalating neuropathy and nephropathy risk."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # EASY | case_03 | Hypertension
    # Master: thermometer_check(1), skin_examination(1), bp_measurement(1),
    #         urine_dipstick(2), pulse_oximeter(2)
    # Total: 7 | Budget: 10
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_03",
        "difficulty_tier": "easy",
        "patient_demographics": {"age": 45, "gender": "male", "location": "Rural Punjab"},
        "hidden_diagnosis": "hypertension",
        "budget": 10,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "bp_measurement": 1,
            "urine_dipstick": 2, "pulse_oximeter": 2
        },
        "relevant_tests": ["bp_measurement", "urine_dipstick"],
        "conclusive_test": "bp_measurement",
        "requires_referral": False,
        "referral_destination": None,
        "critical_window_days": 30,
        "penalty_events": {
            "hypertensive_crisis_missed": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-30": {
                "symptoms": ["dizziness", "occipital headache in mornings", "palpitations"],
                "vitals": {"temp": "37.0 C", "bp": "175/105", "hr": 92, "spo2": "98%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.0 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["malaria", "infection"],
                        "memory_note": "Afebrile 37.0C; infectious cause of headache excluded."
                    },
                    "skin_examination": {
                        "result": "Mild facial flushing; no rash; no pallor",
                        "info_gain": 0.05,
                        "suggests": ["hypertension"],
                        "rules_out": ["anaemia"],
                        "memory_note": "Mild facial flushing noted; significant anaemia excluded. Non-specific finding alone."
                    },
                    "bp_measurement": {
                        "result": "175/105 mmHg (Stage 2 Hypertension)",
                        "info_gain": 1.0,
                        "suggests": ["hypertension"],
                        "rules_out": ["normal_bp"],
                        "memory_note": "BP 175/105 mmHg — Stage 2 Hypertension confirmed. Initiate antihypertensive therapy and lifestyle modification."
                    },
                    "urine_dipstick": {
                        "result": "Protein Trace, Glucose Negative",
                        "info_gain": 0.2,
                        "suggests": ["hypertensive_nephropathy"],
                        "rules_out": ["diabetes", "uti"],
                        "memory_note": "Trace proteinuria; possible early hypertensive renal involvement. Diabetes and UTI excluded."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 98%, PR 92 bpm",
                        "info_gain": 0.05,
                        "suggests": [],
                        "rules_out": ["heart_failure", "respiratory_cause"],
                        "memory_note": "SpO2 98%; significant cardiac decompensation and respiratory cause of symptoms excluded."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # HARD | case_04 | Ischaemic Heart Disease (Acute MI)
    # Master: thermometer_check(1), skin_examination(1), chest_auscultation(1),
    #         bp_measurement(1), pulse_oximeter(2)
    # Total: 6 | Budget: 9
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_04",
        "difficulty_tier": "hard",
        "patient_demographics": {"age": 60, "gender": "male", "location": "Village in Kerala"},
        "hidden_diagnosis": "ischaemic_heart_disease",
        "budget": 9,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "chest_auscultation": 1,
            "bp_measurement": 1, "pulse_oximeter": 2
        },
        "relevant_tests": ["bp_measurement", "pulse_oximeter", "skin_examination"],
        "conclusive_test": "skin_examination",
        "requires_referral": True,
        "referral_destination": "District Hospital (Cardiac Emergency)",
        "critical_window_days": 1,
        "penalty_events": {
            "delayed_referral_post_symptom_onset": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1": {
                "symptoms": ["heavy chest pain radiating to left arm", "sweating", "shortness of breath", "nausea", "feeling of impending doom"],
                "vitals": {"temp": "36.5 C", "bp": "150/90", "hr": 110, "spo2": "94%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "36.5 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["infection", "malaria"],
                        "memory_note": "Afebrile; infective cause of chest pain excluded."
                    },
                    "skin_examination": {
                        "result": "Profuse diaphoresis (cold sweats), pale extremities",
                        "info_gain": 1.0,
                        "suggests": ["ischaemic_heart_disease", "myocardial_infarction"],
                        "rules_out": ["musculoskeletal_pain", "anxiety"],
                        "memory_note": "Profuse cold sweats with peripheral pallor and arm radiation — classic autonomic response of acute MI. URGENT referral to cardiac emergency."
                    },
                    "chest_auscultation": {
                        "result": "Normal heart sounds; no murmur; mild basal crepitations",
                        "info_gain": 0.3,
                        "suggests": ["ischaemic_heart_disease", "early_heart_failure"],
                        "rules_out": ["pneumonia", "pleuritis"],
                        "memory_note": "Mild basal crepitations suggest early pulmonary oedema; no pericardial rub. Consistent with acute ischaemic event."
                    },
                    "bp_measurement": {
                        "result": "150/90 mmHg",
                        "info_gain": 0.2,
                        "suggests": ["hypertension", "ischaemic_heart_disease"],
                        "rules_out": [],
                        "memory_note": "Hypertensive BP in context of chest pain; known risk factor and acute stress response in MI."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 94%, PR 110 bpm (Tachycardia)",
                        "info_gain": 0.3,
                        "suggests": ["ischaemic_heart_disease", "heart_failure"],
                        "rules_out": [],
                        "memory_note": "SpO2 94% with tachycardia; significant haemodynamic compromise consistent with acute MI — immediate referral mandatory."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # EASY | case_05 | Nutritional Anaemia
    # Master: thermometer_check(1), bp_measurement(1), urine_dipstick(2),
    #         skin_examination(1), hemoglobin_strip(4)
    # Total: 9 | Budget: 12
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_05",
        "difficulty_tier": "easy",
        "patient_demographics": {"age": 16, "gender": "female", "location": "Tribal district, Jharkhand"},
        "hidden_diagnosis": "nutritional_anemia",
        "budget": 12,
        "test_costs": {
            "thermometer_check": 1, "bp_measurement": 1, "urine_dipstick": 2,
            "skin_examination": 1, "hemoglobin_strip": 4
        },
        "relevant_tests": ["skin_examination", "hemoglobin_strip"],
        "conclusive_test": "hemoglobin_strip",
        "requires_referral": False,
        "referral_destination": None,
        "critical_window_days": 30,
        "penalty_events": {
            "severe_anaemia_untreated": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-30": {
                "symptoms": ["severe fatigue", "breathlessness on walking", "craving to eat dirt (pica)", "dizziness"],
                "vitals": {"temp": "37.0 C", "bp": "100/60", "hr": 105, "spo2": "98%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.0 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["malaria", "infection"],
                        "memory_note": "Afebrile; infectious cause of fatigue excluded."
                    },
                    "bp_measurement": {
                        "result": "100/60 mmHg (Low)",
                        "info_gain": 0.2,
                        "suggests": ["nutritional_anemia", "dehydration"],
                        "rules_out": [],
                        "memory_note": "Low BP 100/60; hypotension consistent with severe anaemia and reduced cardiac preload."
                    },
                    "urine_dipstick": {
                        "result": "Normal; Glucose Negative, Protein Negative",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["diabetes", "uti", "renal_disease"],
                        "memory_note": "Urinalysis normal; renal, diabetic and urinary causes of fatigue excluded."
                    },
                    "skin_examination": {
                        "result": "Pronounced pallor in conjunctiva and palms, koilonychia (spoon nails)",
                        "info_gain": 0.5,
                        "suggests": ["iron_deficiency_anemia", "nutritional_anemia"],
                        "rules_out": ["malaria"],
                        "memory_note": "Koilonychia and conjunctival pallor strongly suggest iron deficiency anaemia; haemoglobin confirmation required."
                    },
                    "hemoglobin_strip": {
                        "result": "7.2 g/dL (Severe Anaemia)",
                        "info_gain": 1.0,
                        "suggests": ["nutritional_anemia", "iron_deficiency"],
                        "rules_out": ["normal_hemoglobin"],
                        "memory_note": "Hb 7.2 g/dL — severe anaemia confirmed. With koilonychia and pica, iron deficiency nutritional anaemia established. Initiate iron supplementation."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # MEDIUM | case_06 | Diarrheal Disease with Dehydration
    # Master: thermometer_check(1), skin_examination(1), pulse_oximeter(2),
    #         bp_measurement(1)
    # Total: 5 | Budget: 8
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_06",
        "difficulty_tier": "medium",
        "patient_demographics": {"age": 4, "gender": "male", "location": "Rural Bihar"},
        "hidden_diagnosis": "diarrheal_disease_with_dehydration",
        "budget": 8,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1,
            "pulse_oximeter": 2, "bp_measurement": 1
        },
        "relevant_tests": ["skin_examination", "bp_measurement"],
        "conclusive_test": "skin_examination",
        "requires_referral": False,
        "referral_destination": None,
        "critical_window_days": 1,
        "penalty_events": {
            "hypovolemic_shock_without_ors": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1": {
                "symptoms": ["watery loose stools 8 times today", "vomiting", "lethargy", "decreased urination"],
                "vitals": {"temp": "37.5 C", "bp": "85/55", "hr": 130, "spo2": "97%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.5 C (Low-grade fever)",
                        "info_gain": 0.1,
                        "suggests": ["gastroenteritis", "enteric_infection"],
                        "rules_out": [],
                        "memory_note": "Low-grade fever 37.5C; mild systemic response to enteric infection noted."
                    },
                    "skin_examination": {
                        "result": "Decreased skin turgor (pinch recoil slow), sunken eyes, dry mucosa",
                        "info_gain": 1.0,
                        "suggests": ["dehydration", "diarrheal_disease"],
                        "rules_out": ["malnutrition_only"],
                        "memory_note": "Classic triad of dehydration — decreased turgor, sunken eyes, dry mucosa confirmed. Moderate-to-severe dehydration. Initiate ORS immediately."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 97%, PR 130 bpm (Tachycardia)",
                        "info_gain": 0.2,
                        "suggests": ["dehydration", "shock"],
                        "rules_out": ["pneumonia"],
                        "memory_note": "Tachycardia 130 bpm; haemodynamic compromise from dehydration. Respiratory compromise excluded."
                    },
                    "bp_measurement": {
                        "result": "85/55 mmHg (Borderline hypotension for age)",
                        "info_gain": 0.4,
                        "suggests": ["dehydration", "hypovolemic_shock"],
                        "rules_out": [],
                        "memory_note": "Borderline hypotension 85/55 mmHg; hypovolaemic shock threshold approaching — urgent rehydration required."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # EASY | case_07 | Malaria (P. vivax)
    # Master: thermometer_check(1), skin_examination(1), pulse_oximeter(2),
    #         blood_panel(5), rapid_malaria_test(3)
    # Total: 12 | Budget: 14
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_07",
        "difficulty_tier": "easy",
        "patient_demographics": {"age": 28, "gender": "male", "location": "Forest fringe, Chhattisgarh"},
        "hidden_diagnosis": "malaria",
        "budget": 14,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "pulse_oximeter": 2,
            "blood_panel": 5, "rapid_malaria_test": 3
        },
        "relevant_tests": ["thermometer_check", "rapid_malaria_test", "blood_panel"],
        "conclusive_test": "rapid_malaria_test",
        "requires_referral": False,
        "referral_destination": None,
        "critical_window_days": 2,
        "penalty_events": {
            "missed_diagnosis_after_day_2": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1": {
                "symptoms": ["high grade fever", "shivering/chills", "sweating", "body ache"],
                "vitals": {"temp": "39.6 C", "bp": "110/70", "hr": 108, "spo2": "98%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "39.6 C",
                        "info_gain": 0.3,
                        "suggests": ["malaria", "dengue", "typhoid"],
                        "rules_out": [],
                        "memory_note": "High fever 39.6C; febrile illness with malarial periodicity pattern suspected — non-specific alone."
                    },
                    "rapid_malaria_test": {
                        "result": "Positive for Plasmodium vivax",
                        "info_gain": 1.0,
                        "suggests": ["malaria"],
                        "rules_out": ["typhoid", "dengue", "kala_azar"],
                        "memory_note": "RDT confirms P. vivax malaria. Diagnosis established — initiate chloroquine and primaquine regimen."
                    },
                    "blood_panel": {
                        "result": "Hb 10.5 g/dL, Platelets 140,000/mcL, WBC 5,200/mcL",
                        "info_gain": 0.2,
                        "suggests": ["malaria", "dengue"],
                        "rules_out": [],
                        "memory_note": "Mild anaemia and borderline thrombocytopenia; consistent with early malaria but non-specific without RDT."
                    },
                    "skin_examination": {
                        "result": "No rash, no petechiae, no significant pallor",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["dengue", "nutritional_anemia"],
                        "memory_note": "Skin examination unremarkable; dengue haemorrhagic rash and significant anaemia pallor excluded."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 98%, PR 108 bpm",
                        "info_gain": 0.05,
                        "suggests": [],
                        "rules_out": ["pneumonia", "copd_exacerbation"],
                        "memory_note": "Oxygen saturation 98%; significant respiratory compromise excluded at this stage."
                    }
                }
            },
            "2": {
                "symptoms": ["persistent high fever", "severe rigors", "vomiting", "extreme weakness", "altered sensorium"],
                "vitals": {"temp": "40.1 C", "bp": "100/65", "hr": 120, "spo2": "97%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "40.1 C",
                        "info_gain": 0.4,
                        "suggests": ["malaria", "severe_malaria"],
                        "rules_out": [],
                        "memory_note": "Escalating fever to 40.1C with worsening rigors; severe malaria progression with cerebral involvement risk."
                    },
                    "rapid_malaria_test": {
                        "result": "Positive for Plasmodium vivax",
                        "info_gain": 1.0,
                        "suggests": ["malaria"],
                        "rules_out": ["typhoid", "dengue"],
                        "memory_note": "URGENT: RDT persistently positive with altered sensorium — P. vivax confirmed, escalating to severe malaria."
                    },
                    "blood_panel": {
                        "result": "Hb 9.8 g/dL, Platelets 110,000/mcL, WBC 4,800/mcL",
                        "info_gain": 0.3,
                        "suggests": ["malaria", "severe_malaria"],
                        "rules_out": [],
                        "memory_note": "Worsening anaemia (9.8 g/dL) and falling platelets; disease progression confirms escalating severe malaria."
                    },
                    "skin_examination": {
                        "result": "Mild pallor noted in conjunctiva; no rash",
                        "info_gain": 0.1,
                        "suggests": ["malaria"],
                        "rules_out": ["dengue"],
                        "memory_note": "Emerging pallor consistent with worsening haemolysis; dengue rash absent, reinforcing malaria diagnosis."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 97%, PR 120 bpm",
                        "info_gain": 0.1,
                        "suggests": ["severe_malaria"],
                        "rules_out": [],
                        "memory_note": "Escalating tachycardia (120 bpm); SpO2 marginally declining — monitor closely for respiratory deterioration."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # MEDIUM | case_08 | Dengue Fever
    # Master: thermometer_check(1), skin_examination(1), tourniquet_test(1),
    #         pulse_oximeter(2), blood_panel(5), rapid_dengue_test(5)
    # Total: 15 | Budget: 20
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_08",
        "difficulty_tier": "medium",
        "patient_demographics": {"age": 22, "gender": "female", "location": "Urban Tamil Nadu"},
        "hidden_diagnosis": "dengue",
        "budget": 20,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "tourniquet_test": 1,
            "pulse_oximeter": 2, "blood_panel": 5, "rapid_dengue_test": 5
        },
        "relevant_tests": ["tourniquet_test", "rapid_dengue_test", "blood_panel"],
        "conclusive_test": "rapid_dengue_test",
        "requires_referral": False,
        "referral_destination": None,
        "critical_window_days": 3,
        "penalty_events": {
            "dengue_shock_without_referral": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1": {
                "symptoms": ["sudden fever", "severe bone pain (breakbone fever)", "retro-orbital pain", "nausea"],
                "vitals": {"temp": "39.2 C", "bp": "105/65", "hr": 100, "spo2": "98%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "39.2 C (Abrupt-onset fever)",
                        "info_gain": 0.2,
                        "suggests": ["dengue", "malaria", "typhoid"],
                        "rules_out": [],
                        "memory_note": "High fever 39.2C abrupt onset; febrile illness with dengue-compatible pattern."
                    },
                    "skin_examination": {
                        "result": "No petechiae visible; no rash yet",
                        "info_gain": 0.05,
                        "suggests": [],
                        "rules_out": [],
                        "memory_note": "No cutaneous haemorrhagic signs at this stage; dengue rash typically appears by day 3."
                    },
                    "tourniquet_test": {
                        "result": "Positive (>10 petechiae)",
                        "info_gain": 0.4,
                        "suggests": ["dengue", "dengue_haemorrhagic_fever"],
                        "rules_out": [],
                        "memory_note": "Positive tourniquet test with >10 petechiae; capillary fragility confirmed — dengue haemorrhagic risk flagged."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 98%, PR 100 bpm",
                        "info_gain": 0.05,
                        "suggests": [],
                        "rules_out": ["respiratory_failure"],
                        "memory_note": "SpO2 98%; no respiratory compromise at this stage."
                    },
                    "blood_panel": {
                        "result": "Platelets 95,000/mcL, WBC 3,200/mcL",
                        "info_gain": 0.3,
                        "suggests": ["dengue", "viral_fever"],
                        "rules_out": ["bacterial_sepsis"],
                        "memory_note": "Thrombocytopenia and leukopenia; characteristic of dengue viral illness — bacterial sepsis excluded."
                    },
                    "rapid_dengue_test": {
                        "result": "NS1 Antigen Positive",
                        "info_gain": 1.0,
                        "suggests": ["dengue"],
                        "rules_out": ["malaria", "typhoid", "chikungunya"],
                        "memory_note": "NS1 antigen positive on day 1; dengue confirmed in febrile phase. Monitor for warning signs closely."
                    }
                }
            },
            "2": {
                "symptoms": ["fever breaking (critical phase)", "abdominal pain", "persistent vomiting", "lethargy"],
                "vitals": {"temp": "37.5 C", "bp": "95/60", "hr": 110, "spo2": "98%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.5 C (Fever defervescing — critical phase entry)",
                        "info_gain": 0.3,
                        "suggests": ["dengue_critical_phase"],
                        "rules_out": [],
                        "memory_note": "Escalating concern: fever breaking signals entry into dengue critical phase — plasma leakage risk increases now."
                    },
                    "skin_examination": {
                        "result": "Mild flushing; no spontaneous petechiae yet",
                        "info_gain": 0.1,
                        "suggests": ["dengue"],
                        "rules_out": [],
                        "memory_note": "Worsening flushing; clinical evolution consistent with dengue progression. Spontaneous bleeding not yet manifest."
                    },
                    "tourniquet_test": {
                        "result": "Positive (>20 petechiae)",
                        "info_gain": 0.5,
                        "suggests": ["dengue_haemorrhagic_fever", "plasma_leakage"],
                        "rules_out": [],
                        "memory_note": "Worsening capillary fragility: >20 petechiae now. Escalating haemorrhagic dengue — monitor BP and platelets urgently."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 98%, PR 110 bpm",
                        "info_gain": 0.15,
                        "suggests": ["dengue_critical_phase"],
                        "rules_out": [],
                        "memory_note": "Rising tachycardia 110 bpm during fever defervescence; warning sign for haemodynamic compromise."
                    },
                    "blood_panel": {
                        "result": "Platelets 60,000/mcL, WBC 2,800/mcL, rising haematocrit",
                        "info_gain": 0.5,
                        "suggests": ["dengue_haemorrhagic_fever", "plasma_leakage"],
                        "rules_out": [],
                        "memory_note": "Worsening thrombocytopenia (60K) with rising haematocrit — classical dengue plasma leakage pattern escalating."
                    },
                    "rapid_dengue_test": {
                        "result": "NS1 Antigen Positive, IgM Positive",
                        "info_gain": 1.0,
                        "suggests": ["dengue"],
                        "rules_out": [],
                        "memory_note": "URGENT: Both NS1 and IgM positive — confirmed dengue with escalating haemorrhagic features. Critical phase monitoring mandatory."
                    }
                }
            },
            "3": {
                "symptoms": ["bleeding from gums", "severe abdominal pain", "restlessness", "cold clammy skin"],
                "vitals": {"temp": "36.8 C", "bp": "85/55", "hr": 130, "spo2": "96%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "36.8 C (Afebrile — shock phase)",
                        "info_gain": 0.3,
                        "suggests": ["dengue_shock_syndrome"],
                        "rules_out": [],
                        "memory_note": "Afebrile but haemodynamically deteriorating — dengue shock syndrome now imminent."
                    },
                    "skin_examination": {
                        "result": "Spontaneous petechiae visible without test; cool clammy skin",
                        "info_gain": 0.8,
                        "suggests": ["dengue_haemorrhagic_fever", "dengue_shock_syndrome"],
                        "rules_out": [],
                        "memory_note": "URGENT: Spontaneous petechiae and cold clammy extremities — clinical dengue shock syndrome. Immediate referral required."
                    },
                    "tourniquet_test": {
                        "result": "Spontaneous petechiae visible — formal test unnecessary",
                        "info_gain": 0.5,
                        "suggests": ["dengue_shock_syndrome"],
                        "rules_out": [],
                        "memory_note": "URGENT: Test unnecessary — spontaneous haemorrhage confirms severe dengue. Patient needs urgent transfusion facility."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 96%, PR 130 bpm",
                        "info_gain": 0.4,
                        "suggests": ["dengue_shock_syndrome", "hypovolemia"],
                        "rules_out": [],
                        "memory_note": "URGENT: Escalating tachycardia 130 bpm with falling SpO2 — haemodynamic collapse progressing."
                    },
                    "blood_panel": {
                        "result": "Platelets 25,000/mcL (Critical); WBC 2,400/mcL",
                        "info_gain": 0.8,
                        "suggests": ["dengue_shock_syndrome", "dengue_haemorrhagic_fever"],
                        "rules_out": [],
                        "memory_note": "URGENT: Platelets collapsed to 25,000/mcL — life-threatening thrombocytopenia. Platelet transfusion required urgently."
                    },
                    "rapid_dengue_test": {
                        "result": "IgM Positive",
                        "info_gain": 1.0,
                        "suggests": ["dengue"],
                        "rules_out": [],
                        "memory_note": "URGENT: IgM-confirmed dengue in shock phase — escalating to dengue shock syndrome. Immediate hospital referral mandatory."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # HARD | case_09 | COPD Exacerbation
    # Master: thermometer_check(1), skin_examination(1), bp_measurement(1),
    #         chest_auscultation(1), pulse_oximeter(2), sputum_smear(6)
    # Total: 12 | Budget: 15
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_09",
        "difficulty_tier": "hard",
        "patient_demographics": {"age": 68, "gender": "male", "location": "Village in Rajasthan"},
        "hidden_diagnosis": "copd_exacerbation",
        "budget": 15,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "bp_measurement": 1,
            "chest_auscultation": 1, "pulse_oximeter": 2, "sputum_smear": 6
        },
        "relevant_tests": ["pulse_oximeter", "chest_auscultation", "sputum_smear"],
        "conclusive_test": "pulse_oximeter",
        "requires_referral": True,
        "referral_destination": "District Hospital (Respiratory Ward)",
        "critical_window_days": 1,
        "penalty_events": {
            "hypoxia_without_referral": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1": {
                "symptoms": ["worsening breathlessness", "productive cough with green sputum", "inability to speak full sentences"],
                "vitals": {"temp": "37.6 C", "bp": "145/85", "hr": 112, "spo2": "88%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.6 C (Low-grade fever)",
                        "info_gain": 0.1,
                        "suggests": ["infection", "copd_infective_exacerbation"],
                        "rules_out": [],
                        "memory_note": "Low-grade fever 37.6C; infective trigger for COPD exacerbation likely."
                    },
                    "skin_examination": {
                        "result": "Central cyanosis of lips and fingernails; barrel-shaped chest",
                        "info_gain": 0.4,
                        "suggests": ["copd", "respiratory_failure"],
                        "rules_out": [],
                        "memory_note": "Central cyanosis and barrel chest; chronic obstructive pulmonary pathology with acute decompensation evident."
                    },
                    "bp_measurement": {
                        "result": "145/85 mmHg",
                        "info_gain": 0.1,
                        "suggests": ["hypertension"],
                        "rules_out": [],
                        "memory_note": "Elevated BP; chronic hypertension co-morbidity, not driving acute management."
                    },
                    "chest_auscultation": {
                        "result": "Diffuse expiratory wheeze, prolonged expiration, bilateral coarse crepitations",
                        "info_gain": 0.5,
                        "suggests": ["copd_exacerbation", "copd"],
                        "rules_out": ["pneumothorax"],
                        "memory_note": "Expiratory wheeze with prolonged expiration — obstructive pattern consistent with COPD exacerbation. Pneumothorax excluded."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 88% on room air",
                        "info_gain": 1.0,
                        "suggests": ["copd_exacerbation", "respiratory_failure"],
                        "rules_out": ["mild_bronchitis"],
                        "memory_note": "SpO2 88% on room air — life-threatening hypoxia confirmed. COPD exacerbation with type 1 respiratory failure. URGENT referral required."
                    },
                    "sputum_smear": {
                        "result": "Negative for AFB",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["tuberculosis"],
                        "memory_note": "AFB-negative sputum; tuberculosis excluded as cause of respiratory deterioration."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # MEDIUM | case_10 | Typhoid Fever
    # Master: thermometer_check(1), abdominal_exam(1), urine_dipstick(2),
    #         rapid_malaria_test(3), blood_panel(5), widal_test(5)
    # Total: 17 | Budget: 20
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_10",
        "difficulty_tier": "medium",
        "patient_demographics": {"age": 30, "gender": "female", "location": "Slum cluster, Mumbai"},
        "hidden_diagnosis": "typhoid_fever",
        "budget": 20,
        "test_costs": {
            "thermometer_check": 1, "abdominal_exam": 1, "urine_dipstick": 2,
            "rapid_malaria_test": 3, "blood_panel": 5, "widal_test": 5
        },
        "relevant_tests": ["thermometer_check", "abdominal_exam", "widal_test"],
        "conclusive_test": "widal_test",
        "requires_referral": False,
        "referral_destination": None,
        "critical_window_days": 4,
        "penalty_events": {
            "intestinal_perforation_without_referral": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-2": {
                "symptoms": ["fever for 8 days gradually increasing", "dull headache", "abdominal discomfort", "constipation"],
                "vitals": {"temp": "39.0 C", "bp": "115/75", "hr": 80, "spo2": "99%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "39.0 C (Relative bradycardia noted)",
                        "info_gain": 0.2,
                        "suggests": ["typhoid", "malaria", "dengue"],
                        "rules_out": [],
                        "memory_note": "Sustained 39.0C fever with pulse-temperature dissociation; relative bradycardia raises clinical suspicion for typhoid."
                    },
                    "abdominal_exam": {
                        "result": "Mild splenomegaly, diffuse tenderness",
                        "info_gain": 0.3,
                        "suggests": ["typhoid", "hepatitis_a", "kala_azar"],
                        "rules_out": [],
                        "memory_note": "Mild splenomegaly on palpation; narrows differential toward typhoid or viral hepatitis."
                    },
                    "widal_test": {
                        "result": "Positive (TO 1:320, TH 1:160)",
                        "info_gain": 1.0,
                        "suggests": ["typhoid"],
                        "rules_out": ["malaria", "dengue", "hepatitis_a"],
                        "memory_note": "Widal TO 1:320 meets diagnostic threshold; typhoid fever confirmed — begin ciprofloxacin or azithromycin."
                    },
                    "blood_panel": {
                        "result": "WBC 3,400/mcL (leukopenia), Hb 11.2 g/dL, Platelets 180,000/mcL",
                        "info_gain": 0.3,
                        "suggests": ["typhoid", "dengue"],
                        "rules_out": ["bacterial_pyogenic_infection"],
                        "memory_note": "Leukopenia characteristic of Salmonella typhi; helps exclude pyogenic bacterial sepsis from differential."
                    },
                    "urine_dipstick": {
                        "result": "Trace protein, Glucose Negative, Bilirubin Negative",
                        "info_gain": 0.05,
                        "suggests": [],
                        "rules_out": ["diabetes", "uti", "hepatitis"],
                        "memory_note": "Urine unremarkable; UTI, diabetes, and significant hepatic jaundice excluded."
                    },
                    "rapid_malaria_test": {
                        "result": "Negative",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["malaria"],
                        "memory_note": "Malaria excluded by RDT; febrile illness is non-malarial."
                    }
                }
            },
            "3-4": {
                "symptoms": ["high step-ladder fever", "delirium/confusion", "pea-soup diarrhea", "rose spots on trunk"],
                "vitals": {"temp": "39.8 C", "bp": "105/65", "hr": 85, "spo2": "98%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "39.8 C (Step-ladder pattern)",
                        "info_gain": 0.35,
                        "suggests": ["typhoid", "typhoid_complication"],
                        "rules_out": [],
                        "memory_note": "Escalating step-ladder fever to 39.8C; delirium and rose spots on trunk — worsening typhoid progression."
                    },
                    "abdominal_exam": {
                        "result": "Significant distension, tender hepatosplenomegaly",
                        "info_gain": 0.5,
                        "suggests": ["typhoid", "intestinal_perforation"],
                        "rules_out": [],
                        "memory_note": "URGENT: Marked hepatosplenomegaly with abdominal distension; intestinal perforation risk — consider urgent referral."
                    },
                    "widal_test": {
                        "result": "Positive (TO 1:640, TH 1:320)",
                        "info_gain": 1.0,
                        "suggests": ["typhoid"],
                        "rules_out": ["malaria", "dengue"],
                        "memory_note": "URGENT: Widal titre doubled to TO 1:640; escalating active typhoid with impending complications confirmed."
                    },
                    "blood_panel": {
                        "result": "WBC 2,800/mcL (worsening leukopenia), Hb 10.5 g/dL",
                        "info_gain": 0.4,
                        "suggests": ["typhoid", "typhoid_complication"],
                        "rules_out": [],
                        "memory_note": "Worsening leukopenia and anaemia; escalating systemic typhoid involvement with rising complication risk."
                    },
                    "urine_dipstick": {
                        "result": "Trace protein, Glucose Negative",
                        "info_gain": 0.05,
                        "suggests": [],
                        "rules_out": [],
                        "memory_note": "Persistent trace proteinuria; minor renal irritation, non-diagnostic and not driving management."
                    },
                    "rapid_malaria_test": {
                        "result": "Negative",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["malaria"],
                        "memory_note": "Malaria definitively excluded; fever entirely explained by worsening confirmed typhoid."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # HARD | case_11 | Stroke
    # Master: thermometer_check(1), skin_examination(1), chest_auscultation(1),
    #         bp_measurement(1), pulse_oximeter(2)
    # Total: 6 | Budget: 9
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_11",
        "difficulty_tier": "hard",
        "patient_demographics": {"age": 65, "gender": "female", "location": "Rural Haryana"},
        "hidden_diagnosis": "stroke",
        "budget": 9,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "chest_auscultation": 1,
            "bp_measurement": 1, "pulse_oximeter": 2
        },
        "relevant_tests": ["bp_measurement", "skin_examination"],
        "conclusive_test": "skin_examination",
        "requires_referral": True,
        "referral_destination": "District Hospital (Stroke Unit)",
        "critical_window_days": 1,
        "penalty_events": {
            "delayed_referral_beyond_thrombolysis_window": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1": {
                "symptoms": ["sudden weakness in right arm and leg", "slurred speech", "facial droop on right side", "confusion"],
                "vitals": {"temp": "36.9 C", "bp": "185/110", "hr": 88, "spo2": "97%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "36.9 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["febrile_seizure", "meningitis"],
                        "memory_note": "Afebrile 36.9C; infective neurological cause such as meningitis or febrile seizure excluded."
                    },
                    "skin_examination": {
                        "result": "Right-sided facial paralysis, 0/5 motor strength right extremities",
                        "info_gain": 1.0,
                        "suggests": ["stroke", "ischaemic_stroke"],
                        "rules_out": ["bell_palsy", "hypoglycemia_seizure"],
                        "memory_note": "URGENT: Complete right hemiplegia with upper motor neuron facial droop — stroke pattern confirmed. Within thrombolysis window — immediate referral required."
                    },
                    "chest_auscultation": {
                        "result": "Normal heart sounds; no added sounds",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["pneumonia", "pulmonary_oedema"],
                        "memory_note": "Chest clear; pulmonary complication and aspiration pneumonia not yet present."
                    },
                    "bp_measurement": {
                        "result": "185/110 mmHg (Hypertensive Emergency)",
                        "info_gain": 0.4,
                        "suggests": ["stroke", "hypertensive_emergency"],
                        "rules_out": [],
                        "memory_note": "Hypertensive emergency 185/110; high BP consistent with haemorrhagic or ischaemic stroke aetiology."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 97%, PR 88 bpm",
                        "info_gain": 0.1,
                        "suggests": [],
                        "rules_out": ["respiratory_failure"],
                        "memory_note": "SpO2 97%; no respiratory compromise from aspiration at this stage."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # MEDIUM | case_12 | Hepatitis A or E
    # Master: thermometer_check(1), skin_examination(1), abdominal_exam(1),
    #         urine_dipstick(2), blood_panel(5)
    # Total: 10 | Budget: 14
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_12",
        "difficulty_tier": "medium",
        "patient_demographics": {"age": 25, "gender": "male", "location": "Post-flood village, Assam"},
        "hidden_diagnosis": "hepatitis_a_or_e",
        "budget": 14,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "abdominal_exam": 1,
            "urine_dipstick": 2, "blood_panel": 5
        },
        "relevant_tests": ["skin_examination", "abdominal_exam", "urine_dipstick"],
        "conclusive_test": "skin_examination",
        "requires_referral": True,
        "referral_destination": "District Hospital (Gastroenterology)",
        "critical_window_days": 7,
        "penalty_events": {
            "acute_liver_failure_without_referral": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-3": {
                "symptoms": ["yellowish discoloration of eyes", "dark urine", "loss of appetite", "nausea", "mild right upper abdomen pain"],
                "vitals": {"temp": "37.5 C", "bp": "110/70", "hr": 82, "spo2": "99%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.5 C (Low-grade fever)",
                        "info_gain": 0.1,
                        "suggests": ["hepatitis", "viral_infection"],
                        "rules_out": [],
                        "memory_note": "Low-grade fever 37.5C; viral hepatitis prodromal fever pattern."
                    },
                    "skin_examination": {
                        "result": "Pronounced icterus (yellow sclera) and mild generalised jaundice",
                        "info_gain": 1.0,
                        "suggests": ["hepatitis_a", "hepatitis_e", "hepatitis_b"],
                        "rules_out": ["malaria", "dengue"],
                        "memory_note": "Icteric sclerae and jaundice confirmed — viral hepatitis established. Post-flood context suggests Hepatitis A or E. Referral indicated."
                    },
                    "abdominal_exam": {
                        "result": "Tender hepatomegaly",
                        "info_gain": 0.4,
                        "suggests": ["hepatitis", "hepatitis_a_or_e"],
                        "rules_out": ["cirrhosis"],
                        "memory_note": "Tender hepatomegaly consistent with acute viral hepatitis; non-cirrhotic pattern."
                    },
                    "urine_dipstick": {
                        "result": "Bilirubin +++, Urobilinogen Normal",
                        "info_gain": 0.3,
                        "suggests": ["hepatitis", "hepatocellular_jaundice"],
                        "rules_out": ["obstructive_jaundice", "pre_hepatic_jaundice"],
                        "memory_note": "Bilirubinuria with normal urobilinogen; pre-hepatic jaundice excluded, hepatocellular pattern consistent with hepatitis."
                    },
                    "blood_panel": {
                        "result": "WBC 5,200/mcL (normal), Hb 12.1 g/dL, raised transaminases (clinical estimate)",
                        "info_gain": 0.3,
                        "suggests": ["viral_hepatitis"],
                        "rules_out": ["bacterial_sepsis"],
                        "memory_note": "Normal leukocyte count; bacterial sepsis excluded. Clinical picture supports acute viral hepatitis."
                    }
                }
            },
            "4-7": {
                "symptoms": ["deepening jaundice", "severe fatigue", "clay-colored stools", "intense itching (pruritus)"],
                "vitals": {"temp": "37.2 C", "bp": "105/65", "hr": 78, "spo2": "99%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.2 C (Subsiding fever)",
                        "info_gain": 0.15,
                        "suggests": ["hepatitis"],
                        "rules_out": [],
                        "memory_note": "Subsiding fever; typical viral hepatitis pattern — worsening jaundice despite improving pyrexia."
                    },
                    "skin_examination": {
                        "result": "Deep icterus, scratch marks from pruritus",
                        "info_gain": 1.0,
                        "suggests": ["hepatitis_a_or_e", "cholestatic_component"],
                        "rules_out": [],
                        "memory_note": "URGENT: Deepening jaundice with pruritic scratch marks — escalating cholestatic component. Refer for LFT monitoring and IV support."
                    },
                    "abdominal_exam": {
                        "result": "Marked tender hepatomegaly",
                        "info_gain": 0.5,
                        "suggests": ["hepatitis_worsening", "hepatitis_a_or_e"],
                        "rules_out": [],
                        "memory_note": "Worsening hepatomegaly and tenderness; escalating hepatic inflammation — acute liver failure risk rising."
                    },
                    "urine_dipstick": {
                        "result": "Bilirubin +++, Urobilinogen Absent",
                        "info_gain": 0.5,
                        "suggests": ["obstructive_hepatitis", "cholestasis"],
                        "rules_out": [],
                        "memory_note": "URGENT: Absent urobilinogen with persistent bilirubinuria — cholestatic jaundice emerging, worsening hepatocellular damage."
                    },
                    "blood_panel": {
                        "result": "Hb 10.5 g/dL (falling), WBC 4,800/mcL, worsening transaminases",
                        "info_gain": 0.4,
                        "suggests": ["hepatitis_worsening", "acute_liver_failure_risk"],
                        "rules_out": [],
                        "memory_note": "Worsening anaemia and escalating hepatic markers — progressive liver disease. URGENT referral for specialist management."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # MEDIUM | case_13 | Asthma
    # Master: thermometer_check(1), skin_examination(1), bp_measurement(1),
    #         chest_auscultation(1), pulse_oximeter(2)
    # Total: 6 | Budget: 9
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_13",
        "difficulty_tier": "medium",
        "patient_demographics": {"age": 14, "gender": "male", "location": "Industrial outskirts, Gujarat"},
        "hidden_diagnosis": "asthma",
        "budget": 9,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "bp_measurement": 1,
            "chest_auscultation": 1, "pulse_oximeter": 2
        },
        "relevant_tests": ["chest_auscultation", "pulse_oximeter"],
        "conclusive_test": "chest_auscultation",
        "requires_referral": False,
        "referral_destination": None,
        "critical_window_days": 2,
        "penalty_events": {
            "silent_chest_without_referral": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1": {
                "symptoms": ["episodic shortness of breath", "chest tightness", "dry cough worse at night"],
                "vitals": {"temp": "36.8 C", "bp": "115/75", "hr": 95, "spo2": "95%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "36.8 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["infective_bronchitis", "pneumonia"],
                        "memory_note": "Afebrile; infective bronchitis and pneumonia as primary cause less likely."
                    },
                    "skin_examination": {
                        "result": "Mild eczematous changes on forearm; no rash",
                        "info_gain": 0.2,
                        "suggests": ["asthma", "atopic_disease"],
                        "rules_out": [],
                        "memory_note": "Eczematous skin changes; atopic triad (asthma/eczema/rhinitis) noted — supports allergic asthma diagnosis."
                    },
                    "bp_measurement": {
                        "result": "115/75 mmHg (Normal)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": [],
                        "memory_note": "BP normal; cardiovascular cause of breathlessness unlikely."
                    },
                    "chest_auscultation": {
                        "result": "Bilateral widespread polyphonic wheeze on expiration",
                        "info_gain": 1.0,
                        "suggests": ["asthma"],
                        "rules_out": ["copd", "cardiac_failure"],
                        "memory_note": "Polyphonic expiratory wheeze bilaterally — bronchospasm confirmed; asthma diagnosis established. Initiate salbutamol inhaler."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 95%, PR 95 bpm",
                        "info_gain": 0.3,
                        "suggests": ["asthma", "moderate_asthma"],
                        "rules_out": ["severe_attack"],
                        "memory_note": "SpO2 95% with mild tachycardia; moderate asthma attack, not yet life-threatening."
                    }
                }
            },
            "2": {
                "symptoms": ["severe breathlessness", "inability to complete sentences", "use of accessory muscles to breathe", "silent chest"],
                "vitals": {"temp": "36.9 C", "bp": "125/85", "hr": 120, "spo2": "89%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "36.9 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": [],
                        "memory_note": "Persistently afebrile; no infective exacerbation trigger identified."
                    },
                    "skin_examination": {
                        "result": "Eczema unchanged; accessory muscle use visible",
                        "info_gain": 0.2,
                        "suggests": ["asthma"],
                        "rules_out": [],
                        "memory_note": "Atopic background unchanged; visible accessory muscle use confirms severe respiratory effort."
                    },
                    "bp_measurement": {
                        "result": "125/85 mmHg (Mildly elevated)",
                        "info_gain": 0.05,
                        "suggests": [],
                        "rules_out": [],
                        "memory_note": "Mildly elevated BP; likely anxiety and respiratory distress response, non-diagnostic."
                    },
                    "chest_auscultation": {
                        "result": "Decreased air entry globally; absent wheeze (silent chest — medical emergency)",
                        "info_gain": 1.0,
                        "suggests": ["severe_asthma", "life_threatening_asthma"],
                        "rules_out": [],
                        "memory_note": "URGENT: Silent chest — absent wheeze indicates near-complete airway obstruction. Life-threatening asthma attack. Immediate referral mandatory."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 89%, PR 120 bpm",
                        "info_gain": 0.5,
                        "suggests": ["severe_asthma", "respiratory_failure"],
                        "rules_out": [],
                        "memory_note": "URGENT: SpO2 fallen to 89% with escalating tachycardia — impending respiratory failure. Immediate oxygen and referral."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # HARD | case_14 | Lymphatic Filariasis
    # Master: thermometer_check(1), bp_measurement(1), urine_dipstick(2),
    #         skin_examination(1), blood_panel(5)
    # Total: 10 | Budget: 14
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_14",
        "difficulty_tier": "hard",
        "patient_demographics": {"age": 40, "gender": "male", "location": "Endemic district, UP"},
        "hidden_diagnosis": "lymphatic_filariasis",
        "budget": 14,
        "test_costs": {
            "thermometer_check": 1, "bp_measurement": 1, "urine_dipstick": 2,
            "skin_examination": 1, "blood_panel": 5
        },
        "relevant_tests": ["skin_examination", "blood_panel"],
        "conclusive_test": "skin_examination",
        "requires_referral": True,
        "referral_destination": "District Hospital (Filariae Control Programme)",
        "critical_window_days": 30,
        "penalty_events": {
            "missed_referral_for_dec_therapy": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-30": {
                "symptoms": ["massive painless swelling of left leg", "thickening of skin on leg", "heaviness while walking"],
                "vitals": {"temp": "37.1 C", "bp": "125/80", "hr": 76, "spo2": "99%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.1 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["cellulitis", "acute_infection"],
                        "memory_note": "Afebrile; acute infective cellulitis excluded as sole cause of limb swelling."
                    },
                    "bp_measurement": {
                        "result": "125/80 mmHg (Normal)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": [],
                        "memory_note": "BP normal; cardiovascular cause of oedema less likely."
                    },
                    "urine_dipstick": {
                        "result": "Normal; Protein Negative, Glucose Negative",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["nephrotic_syndrome", "renal_disease"],
                        "memory_note": "Urinalysis normal; renal causes of oedema such as nephrotic syndrome excluded."
                    },
                    "skin_examination": {
                        "result": "Non-pitting edema of left lower extremity, hyperkeratosis (elephantiasis)",
                        "info_gain": 1.0,
                        "suggests": ["lymphatic_filariasis", "elephantiasis"],
                        "rules_out": ["deep_vein_thrombosis", "cardiac_oedema"],
                        "memory_note": "Non-pitting elephantiasis with hyperkeratosis — pathognomonic of advanced lymphatic filariasis. Refer for DEC therapy."
                    },
                    "blood_panel": {
                        "result": "Eosinophilia 12%, Hb 11.5 g/dL, WBC 7,800/mcL",
                        "info_gain": 0.4,
                        "suggests": ["filariasis", "parasitic_infection"],
                        "rules_out": ["bacterial_infection"],
                        "memory_note": "Eosinophilia 12% supports helminthic/parasitic infection; consistent with lymphatic filariasis in endemic zone."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # MEDIUM | case_15 | Leprosy
    # Master: thermometer_check(1), urine_dipstick(2), skin_examination(1),
    #         blood_panel(5)
    # Total: 9 | Budget: 12
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_15",
        "difficulty_tier": "medium",
        "patient_demographics": {"age": 35, "gender": "male", "location": "Remote village, MP"},
        "hidden_diagnosis": "leprosy",
        "budget": 12,
        "test_costs": {
            "thermometer_check": 1, "urine_dipstick": 2,
            "skin_examination": 1, "blood_panel": 5
        },
        "relevant_tests": ["skin_examination"],
        "conclusive_test": "skin_examination",
        "requires_referral": True,
        "referral_destination": "District Hospital (Leprosy Control Unit)",
        "critical_window_days": 45,
        "penalty_events": {
            "missed_mdt_initiation": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-45": {
                "symptoms": ["light colored patches on back", "loss of sensation over the patches", "weakness in gripping objects", "painless ulcers on feet"],
                "vitals": {"temp": "37.0 C", "bp": "120/75", "hr": 80, "spo2": "99%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.0 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["acute_infection"],
                        "memory_note": "Afebrile; acute febrile illness excluded. Chronic insidious onset confirmed."
                    },
                    "urine_dipstick": {
                        "result": "Normal; Glucose Negative, Protein Negative",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["renal_disease", "diabetes"],
                        "memory_note": "Urinalysis normal; renal and diabetic neuropathy as alternative cause excluded."
                    },
                    "skin_examination": {
                        "result": "Multiple hypopigmented macules on trunk with complete anesthesia to touch and pinprick; thickened ulnar nerve palpated",
                        "info_gain": 1.0,
                        "suggests": ["leprosy", "borderline_leprosy"],
                        "rules_out": ["tinea_versicolor", "vitiligo"],
                        "memory_note": "Hypopigmented anaesthetic macules with thickened peripheral nerve — pathognomonic triad of leprosy. MDT regimen and referral required."
                    },
                    "blood_panel": {
                        "result": "Mild eosinophilia 8%, Hb 11.8 g/dL, WBC 6,500/mcL",
                        "info_gain": 0.1,
                        "suggests": ["parasitic_or_granulomatous_infection"],
                        "rules_out": [],
                        "memory_note": "Mild eosinophilia; non-specific for leprosy but consistent with chronic granulomatous infection."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # HARD | case_16 | Cervical Cancer
    # Master: thermometer_check(1), bp_measurement(1), urine_dipstick(2),
    #         abdominal_exam(1), hemoglobin_strip(4)
    # Total: 9 | Budget: 13
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_16",
        "difficulty_tier": "hard",
        "patient_demographics": {"age": 50, "gender": "female", "location": "Rural West Bengal"},
        "hidden_diagnosis": "cervical_cancer",
        "budget": 13,
        "test_costs": {
            "thermometer_check": 1, "bp_measurement": 1, "urine_dipstick": 2,
            "abdominal_exam": 1, "hemoglobin_strip": 4
        },
        "relevant_tests": ["abdominal_exam", "hemoglobin_strip"],
        "conclusive_test": "abdominal_exam",
        "requires_referral": True,
        "referral_destination": "District Hospital (Gynaecological Oncology)",
        "critical_window_days": 14,
        "penalty_events": {
            "missed_malignancy_referral": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-14": {
                "symptoms": ["irregular vaginal bleeding", "foul-smelling vaginal discharge", "pelvic pain", "severe fatigue", "weight loss"],
                "vitals": {"temp": "37.2 C", "bp": "105/65", "hr": 96, "spo2": "98%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.2 C (Low-grade fever)",
                        "info_gain": 0.05,
                        "suggests": ["infection", "cancer_associated_fever"],
                        "rules_out": [],
                        "memory_note": "Low-grade fever; may indicate associated pelvic infection or tumour necrosis."
                    },
                    "bp_measurement": {
                        "result": "105/65 mmHg (Low)",
                        "info_gain": 0.1,
                        "suggests": ["anaemia", "haemorrhage"],
                        "rules_out": [],
                        "memory_note": "Low BP consistent with significant blood loss from chronic vaginal bleeding."
                    },
                    "urine_dipstick": {
                        "result": "Blood Trace, Protein Trace",
                        "info_gain": 0.2,
                        "suggests": ["cervical_cancer", "bladder_involvement"],
                        "rules_out": [],
                        "memory_note": "Trace haematuria may indicate tumour invasion to bladder — cervical cancer local extension suspected."
                    },
                    "abdominal_exam": {
                        "result": "Hard, fixed, irregular suprapubic mass palpated",
                        "info_gain": 1.0,
                        "suggests": ["cervical_cancer", "pelvic_malignancy"],
                        "rules_out": ["fibroid", "ovarian_cyst_benign"],
                        "memory_note": "Hard, fixed, irregular suprapubic mass — highly suspicious for advanced pelvic malignancy. URGENT referral to gynaecological oncology."
                    },
                    "hemoglobin_strip": {
                        "result": "8.5 g/dL (Significant Anaemia)",
                        "info_gain": 0.3,
                        "suggests": ["anaemia_of_chronic_disease", "haemorrhagic_anaemia"],
                        "rules_out": [],
                        "memory_note": "Haemoglobin 8.5 g/dL; significant anaemia from chronic blood loss consistent with cervical malignancy."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # HARD | case_17 | Chronic Kidney Disease
    # Master: thermometer_check(1), skin_examination(1), bp_measurement(1),
    #         pulse_oximeter(2), urine_dipstick(2), blood_panel(5)
    # Total: 12 | Budget: 16
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_17",
        "difficulty_tier": "hard",
        "patient_demographics": {"age": 58, "gender": "male", "location": "Farming community, Andhra Pradesh"},
        "hidden_diagnosis": "chronic_kidney_disease",
        "budget": 16,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "bp_measurement": 1,
            "pulse_oximeter": 2, "urine_dipstick": 2, "blood_panel": 5
        },
        "relevant_tests": ["bp_measurement", "urine_dipstick", "skin_examination"],
        "conclusive_test": "urine_dipstick",
        "requires_referral": True,
        "referral_destination": "District Hospital (Nephrology)",
        "critical_window_days": 10,
        "penalty_events": {
            "uraemia_without_dialysis_referral": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-5": {
                "symptoms": ["swelling in legs and face", "fatigue", "nausea", "decreased urine output"],
                "vitals": {"temp": "36.8 C", "bp": "165/100", "hr": 85, "spo2": "97%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "36.8 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["infection"],
                        "memory_note": "Afebrile; infective cause of oedema excluded."
                    },
                    "skin_examination": {
                        "result": "Bilateral pitting edema up to knees, periorbital puffiness",
                        "info_gain": 0.4,
                        "suggests": ["chronic_kidney_disease", "nephrotic_syndrome", "cardiac_failure"],
                        "rules_out": [],
                        "memory_note": "Bilateral pitting oedema with periorbital puffiness; nephrotic/renal syndrome pattern — CKD workup indicated."
                    },
                    "bp_measurement": {
                        "result": "165/100 mmHg",
                        "info_gain": 0.3,
                        "suggests": ["chronic_kidney_disease", "renal_hypertension"],
                        "rules_out": [],
                        "memory_note": "Hypertension 165/100; renal hypertension pattern in context of oedema and proteinuria."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 97%, PR 85 bpm",
                        "info_gain": 0.05,
                        "suggests": [],
                        "rules_out": ["severe_cardiac_failure", "respiratory_failure"],
                        "memory_note": "SpO2 97%; no significant respiratory compromise at this stage."
                    },
                    "urine_dipstick": {
                        "result": "Protein +++, Blood Trace",
                        "info_gain": 1.0,
                        "suggests": ["chronic_kidney_disease", "nephrotic_syndrome"],
                        "rules_out": ["cardiac_oedema", "hepatic_oedema"],
                        "memory_note": "Massive proteinuria (Protein +++) — renal origin of oedema confirmed. CKD likely. Immediate referral to District Hospital required."
                    },
                    "blood_panel": {
                        "result": "Hb 9.5 g/dL, WBC 6,200/mcL, elevated creatinine (clinical estimate)",
                        "info_gain": 0.4,
                        "suggests": ["chronic_kidney_disease", "renal_anaemia"],
                        "rules_out": [],
                        "memory_note": "Normocytic anaemia consistent with CKD-associated erythropoietin deficiency; renal origin confirmed."
                    }
                }
            },
            "6-10": {
                "symptoms": ["severe shortness of breath (fluid overload)", "vomiting", "confusion (uremia)", "muscle twitches"],
                "vitals": {"temp": "36.5 C", "bp": "180/110", "hr": 95, "spo2": "92%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "36.5 C (Subnormal)",
                        "info_gain": 0.05,
                        "suggests": [],
                        "rules_out": [],
                        "memory_note": "Subnormal temperature; uraemia causing temperature dysregulation — worsening CKD progression."
                    },
                    "skin_examination": {
                        "result": "Massive anasarca (generalised edema), uremic frost visible",
                        "info_gain": 0.6,
                        "suggests": ["end_stage_renal_disease", "uraemia"],
                        "rules_out": [],
                        "memory_note": "URGENT: Uremic frost and anasarca — end-stage renal failure. Immediate dialysis-capable referral mandatory."
                    },
                    "bp_measurement": {
                        "result": "180/110 mmHg (Hypertensive Emergency)",
                        "info_gain": 0.4,
                        "suggests": ["hypertensive_emergency", "ckd_progression"],
                        "rules_out": [],
                        "memory_note": "URGENT: Escalating BP to 180/110 — hypertensive emergency from worsening CKD. Risk of hypertensive encephalopathy."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 92%, PR 95 bpm",
                        "info_gain": 0.3,
                        "suggests": ["fluid_overload", "pulmonary_oedema"],
                        "rules_out": [],
                        "memory_note": "Worsening SpO2 92%; pulmonary oedema from fluid overload escalating — respiratory compromise now present."
                    },
                    "urine_dipstick": {
                        "result": "Protein +++, Blood Trace (unchanged)",
                        "info_gain": 1.0,
                        "suggests": ["chronic_kidney_disease"],
                        "rules_out": [],
                        "memory_note": "URGENT: Persistent massive proteinuria — established CKD with end-organ failure escalating. Dialysis referral critical."
                    },
                    "blood_panel": {
                        "result": "Hb 7.8 g/dL, markedly elevated creatinine, raised potassium (clinical)",
                        "info_gain": 0.5,
                        "suggests": ["end_stage_renal_disease", "hyperkalaemia_risk"],
                        "rules_out": [],
                        "memory_note": "URGENT: Worsening anaemia with rising creatinine and potassium — life-threatening uraemia and hyperkalaemia risk."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # HARD | case_18 | Kala-Azar (Visceral Leishmaniasis)
    # Master: thermometer_check(1), skin_examination(1), urine_dipstick(2),
    #         rapid_malaria_test(3), abdominal_exam(1), blood_panel(5)
    # Total: 13 | Budget: 17
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_18",
        "difficulty_tier": "hard",
        "patient_demographics": {"age": 28, "gender": "male", "location": "Endemic zone, Bihar"},
        "hidden_diagnosis": "kala_azar",
        "budget": 17,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "urine_dipstick": 2,
            "rapid_malaria_test": 3, "abdominal_exam": 1, "blood_panel": 5
        },
        "relevant_tests": ["abdominal_exam", "blood_panel", "skin_examination"],
        "conclusive_test": "abdominal_exam",
        "requires_referral": True,
        "referral_destination": "District Hospital (Kala-Azar Elimination Programme)",
        "critical_window_days": 7,
        "penalty_events": {
            "missed_referral_for_amb_therapy": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-7": {
                "symptoms": ["fever for 2 months", "progressive extreme weight loss", "massive swelling in abdomen", "darkening of skin", "bleeding gums"],
                "vitals": {"temp": "38.5 C", "bp": "95/60", "hr": 105, "spo2": "98%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "38.5 C (Prolonged fever over 2 months)",
                        "info_gain": 0.2,
                        "suggests": ["kala_azar", "malaria", "typhoid"],
                        "rules_out": [],
                        "memory_note": "Prolonged fever 38.5C over 2 months; chronic febrile illness requiring systematic evaluation."
                    },
                    "skin_examination": {
                        "result": "Hyperpigmentation on hands, feet, abdomen, and face",
                        "info_gain": 0.5,
                        "suggests": ["kala_azar", "visceral_leishmaniasis"],
                        "rules_out": ["malaria"],
                        "memory_note": "Generalised hyperpigmentation (kala-azar = black fever); highly characteristic of visceral leishmaniasis in Bihar endemic zone."
                    },
                    "urine_dipstick": {
                        "result": "Protein Trace, Glucose Negative",
                        "info_gain": 0.05,
                        "suggests": [],
                        "rules_out": ["diabetes", "uti"],
                        "memory_note": "Trace proteinuria; minor renal irritation. No alternative diagnosis suggested."
                    },
                    "rapid_malaria_test": {
                        "result": "Negative",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["malaria"],
                        "memory_note": "Malaria excluded by RDT; prolonged fever with splenomegaly is non-malarial."
                    },
                    "abdominal_exam": {
                        "result": "Massive splenomegaly crossing umbilicus, firm and non-tender. Hepatomegaly present.",
                        "info_gain": 1.0,
                        "suggests": ["kala_azar", "visceral_leishmaniasis"],
                        "rules_out": ["malaria", "typhoid", "lymphoma"],
                        "memory_note": "Massive crossing-umbilicus splenomegaly — pathognomonic of kala-azar in Bihar endemic context. Immediate referral for rK39 test and AmBisome therapy."
                    },
                    "blood_panel": {
                        "result": "Severe Pancytopenia: Hb 5.5 g/dL, WBC 1,500/mcL, Platelets 45,000/mcL",
                        "info_gain": 0.5,
                        "suggests": ["kala_azar", "visceral_leishmaniasis"],
                        "rules_out": ["dengue_alone"],
                        "memory_note": "Severe pancytopenia with bone marrow suppression; strongly supports visceral leishmaniasis over other diagnoses."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # MEDIUM | case_19 | Severe Pneumonia Under 5
    # Master: thermometer_check(1), skin_examination(1), bp_measurement(1),
    #         chest_auscultation(1), pulse_oximeter(2)
    # Total: 6 | Budget: 9
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_19",
        "difficulty_tier": "medium",
        "patient_demographics": {"age": 2, "gender": "female", "location": "Tribal village, Odisha"},
        "hidden_diagnosis": "severe_pneumonia_under_5",
        "budget": 9,
        "test_costs": {
            "thermometer_check": 1, "skin_examination": 1, "bp_measurement": 1,
            "chest_auscultation": 1, "pulse_oximeter": 2
        },
        "relevant_tests": ["pulse_oximeter", "chest_auscultation", "thermometer_check"],
        "conclusive_test": "pulse_oximeter",
        "requires_referral": True,
        "referral_destination": "District Hospital (Paediatric Ward)",
        "critical_window_days": 1,
        "penalty_events": {
            "hypoxia_without_referral_child": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1": {
                "symptoms": ["high fever", "fast breathing", "lower chest wall indrawing", "inability to drink", "grunting"],
                "vitals": {"temp": "39.4 C", "bp": "90/60", "hr": 150, "spo2": "89%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "39.4 C (High fever)",
                        "info_gain": 0.2,
                        "suggests": ["pneumonia", "malaria", "sepsis"],
                        "rules_out": [],
                        "memory_note": "High fever 39.4C in a 2-year-old; serious bacterial infection and pneumonia in differential."
                    },
                    "skin_examination": {
                        "result": "Central cyanosis of lips; intercostal retractions visible",
                        "info_gain": 0.4,
                        "suggests": ["severe_pneumonia", "respiratory_failure"],
                        "rules_out": [],
                        "memory_note": "Central cyanosis and chest retractions — severe respiratory distress in a child. Pneumonia with hypoxia highly likely."
                    },
                    "bp_measurement": {
                        "result": "90/60 mmHg (Low for age)",
                        "info_gain": 0.2,
                        "suggests": ["sepsis", "severe_illness"],
                        "rules_out": [],
                        "memory_note": "Low BP for age; haemodynamic compromise consistent with severe pneumonia or sepsis."
                    },
                    "chest_auscultation": {
                        "result": "Bronchial breath sounds and crepitations over right mid and lower zones",
                        "info_gain": 0.5,
                        "suggests": ["pneumonia", "severe_pneumonia"],
                        "rules_out": ["asthma", "bronchiolitis"],
                        "memory_note": "Right-sided bronchial breathing with crepitations; lobar consolidation consistent with bacterial pneumonia confirmed."
                    },
                    "pulse_oximeter": {
                        "result": "SpO2 89%, PR 150 bpm",
                        "info_gain": 1.0,
                        "suggests": ["severe_pneumonia", "hypoxia"],
                        "rules_out": ["mild_rti"],
                        "memory_note": "SpO2 89% in a child — WHO severe pneumonia criteria met. URGENT referral for oxygen and IV antibiotics. Life-threatening."
                    }
                }
            }
        }
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # EASY | case_20 | Intestinal Worms
    # Master: thermometer_check(1), urine_dipstick(2), skin_examination(1),
    #         abdominal_exam(1), hemoglobin_strip(4)
    # Total: 9 | Budget: 12
    # ═══════════════════════════════════════════════════════════════════════════
    {
        "id": "case_20",
        "difficulty_tier": "easy",
        "patient_demographics": {"age": 7, "gender": "male", "location": "Rural UP"},
        "hidden_diagnosis": "intestinal_worms",
        "budget": 12,
        "test_costs": {
            "thermometer_check": 1, "urine_dipstick": 2, "skin_examination": 1,
            "abdominal_exam": 1, "hemoglobin_strip": 4
        },
        "relevant_tests": ["abdominal_exam", "hemoglobin_strip"],
        "conclusive_test": "hemoglobin_strip",
        "requires_referral": False,
        "referral_destination": None,
        "critical_window_days": 14,
        "penalty_events": {
            "untreated_worm_burden_anaemia": -1.0,
            "budget_exhausted": -0.5,
            "duplicate_test": -0.2
        },
        "daily_progression": {
            "1-14": {
                "symptoms": ["vague abdominal pain", "poor appetite", "passing 'long white worms' in stool", "fatigue", "teeth grinding at night"],
                "vitals": {"temp": "37.0 C", "bp": "100/65", "hr": 88, "spo2": "99%"},
                "test_results": {
                    "thermometer_check": {
                        "result": "37.0 C (Afebrile)",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["malaria", "infection"],
                        "memory_note": "Afebrile; febrile illness excluded. Helminthic infestation is typically non-pyrexial."
                    },
                    "urine_dipstick": {
                        "result": "Normal; Glucose Negative, Protein Negative",
                        "info_gain": 0.0,
                        "suggests": [],
                        "rules_out": ["uti", "diabetes", "renal_disease"],
                        "memory_note": "Urinalysis normal; UTI and renal causes excluded."
                    },
                    "skin_examination": {
                        "result": "Mild pallor in conjunctiva; no rash; no oedema",
                        "info_gain": 0.2,
                        "suggests": ["nutritional_anemia", "intestinal_worms"],
                        "rules_out": [],
                        "memory_note": "Mild conjunctival pallor; anaemia from worm-related malabsorption and blood loss likely."
                    },
                    "abdominal_exam": {
                        "result": "Soft, non-tender, slight distension",
                        "info_gain": 0.3,
                        "suggests": ["intestinal_worms", "malnutrition"],
                        "rules_out": ["appendicitis", "organomegaly"],
                        "memory_note": "Mild abdominal distension without tenderness; consistent with intestinal helminthiasis. No acute abdomen."
                    },
                    "hemoglobin_strip": {
                        "result": "9.5 g/dL (Moderate Anaemia)",
                        "info_gain": 1.0,
                        "suggests": ["intestinal_worms", "nutritional_deficiency"],
                        "rules_out": ["normal_hemoglobin"],
                        "memory_note": "Hb 9.5 g/dL — moderate anaemia in a school-age child with visible worms in stool. Helminthiasis confirmed. Administer albendazole and iron supplementation."
                    }
                }
            }
        }
    }

]


# ─────────────────────────────────────────────────────────────────────────────
#  Utility: expand grouped day ranges → flat int-keyed dict (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
def expand_daily_progression(daily_progression):
    expanded = {}
    for day_key, state_data in daily_progression.items():
        if "-" in str(day_key):
            start, end = map(int, str(day_key).split("-"))
            for d in range(start, end + 1):
                expanded[d] = copy.deepcopy(state_data)
        else:
            expanded[int(day_key)] = copy.deepcopy(state_data)
    return expanded


# ─────────────────────────────────────────────────────────────────────────────
#  Smoke test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    all_ids = [s["id"] for s in scenarios_v2]
    assert len(all_ids) == 20, f"Expected 20 scenarios, got {len(all_ids)}"
    assert len(set(all_ids)) == 20, "Duplicate IDs detected"

    for sc in scenarios_v2:
        prog = expand_daily_progression(sc["daily_progression"])
        total_cost = sum(sc["test_costs"].values())
        assert total_cost < sc["budget"], (
            f"{sc['id']}: total_cost {total_cost} >= budget {sc['budget']}"
        )
        # Verify conclusive_test is 1.0 in all phases
        for day_key, phase in sc["daily_progression"].items():
            ct = sc["conclusive_test"]
            ig = phase["test_results"][ct]["info_gain"]
            assert ig == 1.0, (
                f"{sc['id']} day {day_key}: conclusive_test '{ct}' info_gain={ig}, expected 1.0"
            )
        print(
            f"[OK] {sc['id']:8s} | {sc['difficulty_tier']:6s} | "
            f"{sc['hidden_diagnosis']:35s} | "
            f"cost={total_cost:2d}/{sc['budget']:2d} | "
            f"phases={len(sc['daily_progression'])} | "
            f"tests/phase={len(list(sc['daily_progression'].values())[0]['test_results'])}"
        )
    print(f"\nAll {len(scenarios_v2)} scenarios validated successfully.")