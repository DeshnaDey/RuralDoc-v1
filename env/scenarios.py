from __future__ import annotations

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

scenarios_v2 = \
[   {   'id': 'case_01',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 34, 'gender': 'male', 'location': 'Urban slum, Delhi'},
        'hidden_diagnosis': 'tuberculosis',
        'budget': 24,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'chest_auscultation': 1,
                          'pulse_oximeter': 2,
                          'rapid_malaria_test': 3,
                          'blood_panel': 5,
                          'sputum_smear': 6},
        'relevant_tests': ['thermometer_check', 'chest_auscultation', 'sputum_smear'],
        'conclusive_test': 'sputum_smear',
        'requires_referral': True,
        'referral_destination': 'District Hospital (DOTS Centre)',
        'critical_window_days': 14,
        'penalty_events': {'hemoptysis_without_referral': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1-7': {   'symptoms': [   'chronic cough for 3 weeks',
                                                            'night sweats',
                                                            'weight loss',
                                                            'low-grade evening fever'],
                                            'vitals': {'temp': '37.9 C', 'bp': '110/75', 'hr': 88, 'spo2': '96%'},
                                            'test_results': {   'thermometer_check': {   'result': '37.9 C (Low-grade '
                                                                                                   'evening fever)',
                                                                                         'info_gain': 0.1,
                                                                                         'suggests': [   'tuberculosis',
                                                                                                         'chronic_infection',
                                                                                                         'kala_azar'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Low-grade '
                                                                                                        'evening fever '
                                                                                                        '37.9C; '
                                                                                                        'consistent '
                                                                                                        'with TB '
                                                                                                        'chronicity '
                                                                                                        'but seen in '
                                                                                                        'many '
                                                                                                        'conditions — '
                                                                                                        'non-specific '
                                                                                                        'alone.'},
                                                                'chest_auscultation': {   'result': 'Crepitations in '
                                                                                                    'the apical region '
                                                                                                    'of right lung',
                                                                                          'info_gain': 0.4,
                                                                                          'suggests': [   'tuberculosis',
                                                                                                          'pneumonia'],
                                                                                          'rules_out': [   'asthma',
                                                                                                           'copd'],
                                                                                          'memory_note': 'Apical '
                                                                                                         'crepitations '
                                                                                                         'localised to '
                                                                                                         'right apex; '
                                                                                                         'strongly '
                                                                                                         'suspicious '
                                                                                                         'for '
                                                                                                         'pulmonary TB '
                                                                                                         '— sputum '
                                                                                                         'smear '
                                                                                                         'urgently '
                                                                                                         'indicated.'},
                                                                'sputum_smear': {   'result': 'Positive for Acid-Fast '
                                                                                              'Bacilli (AFB)',
                                                                                    'info_gain': 1.0,
                                                                                    'suggests': ['tuberculosis'],
                                                                                    'rules_out': [   'pneumonia',
                                                                                                     'copd_exacerbation',
                                                                                                     'lung_cancer'],
                                                                                    'memory_note': 'AFB-positive '
                                                                                                   'sputum smear; '
                                                                                                   'pulmonary '
                                                                                                   'tuberculosis '
                                                                                                   'confirmed — '
                                                                                                   'initiate DOTS '
                                                                                                   'referral '
                                                                                                   'immediately.'},
                                                                'pulse_oximeter': {   'result': 'SpO2 96%, PR 88 bpm',
                                                                                      'info_gain': 0.1,
                                                                                      'suggests': [],
                                                                                      'rules_out': [   'severe_respiratory_failure'],
                                                                                      'memory_note': 'SpO2 96%; mild '
                                                                                                     'hypoxia present, '
                                                                                                     'no acute '
                                                                                                     'respiratory '
                                                                                                     'failure at this '
                                                                                                     'stage.'},
                                                                'blood_panel': {   'result': 'Hb 10.8 g/dL, ESR 78 '
                                                                                             'mm/hr, WBC 7,200/mcL',
                                                                                   'info_gain': 0.2,
                                                                                   'suggests': [   'tuberculosis',
                                                                                                   'chronic_infection'],
                                                                                   'rules_out': [],
                                                                                   'memory_note': 'Mild anaemia with '
                                                                                                  'markedly raised ESR '
                                                                                                  '(78 mm/hr); '
                                                                                                  'supports chronic '
                                                                                                  'granulomatous '
                                                                                                  'infection '
                                                                                                  'consistent with '
                                                                                                  'TB.'},
                                                                'rapid_malaria_test': {   'result': 'Negative',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': ['malaria'],
                                                                                          'memory_note': 'Malaria '
                                                                                                         'excluded by '
                                                                                                         'RDT; fever '
                                                                                                         'with night '
                                                                                                         'sweats not '
                                                                                                         'attributable '
                                                                                                         'to malarial '
                                                                                                         'infection.'},
                                                                'skin_examination': {   'result': 'Mild wasting noted; '
                                                                                                  'no rash; no pallor',
                                                                                        'info_gain': 0.1,
                                                                                        'suggests': ['tuberculosis'],
                                                                                        'rules_out': [   'dengue',
                                                                                                         'kala_azar'],
                                                                                        'memory_note': 'Mild cachexia '
                                                                                                       'consistent '
                                                                                                       'with chronic '
                                                                                                       'TB illness; no '
                                                                                                       'cutaneous '
                                                                                                       'finding '
                                                                                                       'suggesting '
                                                                                                       'alternative '
                                                                                                       'diagnosis.'}}},
                                 '8-14': {   'symptoms': [   'chronic cough for 4 weeks',
                                                             'blood-tinged sputum (hemoptysis)',
                                                             'severe night sweats',
                                                             'visible weight loss'],
                                             'vitals': {'temp': '38.2 C', 'bp': '105/70', 'hr': 95, 'spo2': '94%'},
                                             'test_results': {   'thermometer_check': {   'result': '38.2 C '
                                                                                                    '(Escalating '
                                                                                                    'fever)',
                                                                                          'info_gain': 0.2,
                                                                                          'suggests': [   'tuberculosis',
                                                                                                          'tb_progression'],
                                                                                          'rules_out': [],
                                                                                          'memory_note': 'Escalating '
                                                                                                         'evening '
                                                                                                         'fever to '
                                                                                                         '38.2C; '
                                                                                                         'worsening TB '
                                                                                                         'systemic '
                                                                                                         'involvement '
                                                                                                         'alongside '
                                                                                                         'onset of '
                                                                                                         'hemoptysis.'},
                                                                 'chest_auscultation': {   'result': 'Worsening '
                                                                                                     'crepitations and '
                                                                                                     'reduced breath '
                                                                                                     'sounds right '
                                                                                                     'apex',
                                                                                           'info_gain': 0.5,
                                                                                           'suggests': [   'tuberculosis',
                                                                                                           'tb_cavitation'],
                                                                                           'rules_out': ['asthma'],
                                                                                           'memory_note': 'URGENT: '
                                                                                                          'Progressive '
                                                                                                          'apical '
                                                                                                          'consolidation '
                                                                                                          'with '
                                                                                                          'reduced '
                                                                                                          'breath '
                                                                                                          'sounds — '
                                                                                                          'cavitation '
                                                                                                          'advancing, '
                                                                                                          'parenchymal '
                                                                                                          'destruction '
                                                                                                          'worsening.'},
                                                                 'sputum_smear': {   'result': 'Positive for Acid-Fast '
                                                                                               'Bacilli (AFB) — heavy '
                                                                                               'bacillary load',
                                                                                     'info_gain': 1.0,
                                                                                     'suggests': ['tuberculosis'],
                                                                                     'rules_out': [   'pneumonia',
                                                                                                      'copd_exacerbation'],
                                                                                     'memory_note': 'URGENT: '
                                                                                                    'Persistently '
                                                                                                    'AFB-positive with '
                                                                                                    'escalating '
                                                                                                    'bacillary load '
                                                                                                    'and hemoptysis — '
                                                                                                    'active TB, '
                                                                                                    'immediate DOTS '
                                                                                                    'referral '
                                                                                                    'required.'},
                                                                 'pulse_oximeter': {   'result': 'SpO2 94%, PR 95 bpm',
                                                                                       'info_gain': 0.2,
                                                                                       'suggests': [   'tuberculosis_progression'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Worsening SpO2 '
                                                                                                      'to 94%; '
                                                                                                      'escalating '
                                                                                                      'respiratory '
                                                                                                      'compromise — '
                                                                                                      'referral to '
                                                                                                      'District '
                                                                                                      'Hospital now '
                                                                                                      'urgent.'},
                                                                 'blood_panel': {   'result': 'Hb 9.6 g/dL, ESR 102 '
                                                                                              'mm/hr, WBC 8,100/mcL',
                                                                                    'info_gain': 0.3,
                                                                                    'suggests': [   'tuberculosis',
                                                                                                    'tb_progression'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Worsening anaemia '
                                                                                                   'and markedly '
                                                                                                   'elevated ESR (102 '
                                                                                                   'mm/hr); confirms '
                                                                                                   'active escalating '
                                                                                                   'TB with rising '
                                                                                                   'systemic '
                                                                                                   'inflammatory '
                                                                                                   'burden.'},
                                                                 'rapid_malaria_test': {   'result': 'Negative',
                                                                                           'info_gain': 0.0,
                                                                                           'suggests': [],
                                                                                           'rules_out': ['malaria'],
                                                                                           'memory_note': 'Malaria '
                                                                                                          'definitively '
                                                                                                          'excluded; '
                                                                                                          'clinical '
                                                                                                          'picture '
                                                                                                          'entirely '
                                                                                                          'explained '
                                                                                                          'by '
                                                                                                          'confirmed '
                                                                                                          'escalating '
                                                                                                          'pulmonary '
                                                                                                          'TB.'},
                                                                 'skin_examination': {   'result': 'Progressive '
                                                                                                   'wasting and pallor '
                                                                                                   'now visible; no '
                                                                                                   'rash',
                                                                                         'info_gain': 0.15,
                                                                                         'suggests': ['tuberculosis'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Worsening '
                                                                                                        'pallor and '
                                                                                                        'visible '
                                                                                                        'cachexia; '
                                                                                                        'escalating '
                                                                                                        'TB-related '
                                                                                                        'wasting and '
                                                                                                        'anaemia now '
                                                                                                        'clinically '
                                                                                                        'apparent.'}}}}},
    {   'id': 'case_02',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 52, 'gender': 'female', 'location': 'Semi-urban Maharashtra'},
        'hidden_diagnosis': 'type_2_diabetes',
        'budget': 12,
        'test_costs': {   'thermometer_check': 1,
                          'bp_measurement': 1,
                          'skin_examination': 1,
                          'urine_dipstick': 2,
                          'blood_glucose_strip': 4},
        'relevant_tests': ['blood_glucose_strip', 'urine_dipstick'],
        'conclusive_test': 'blood_glucose_strip',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 30,
        'penalty_events': {'uncontrolled_hyperglycemia_missed': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1-15': {   'symptoms': [   'frequent urination at night',
                                                             'excessive thirst',
                                                             'blurring of vision'],
                                             'vitals': {'temp': '36.8 C', 'bp': '130/85', 'hr': 78, 'spo2': '99%'},
                                             'test_results': {   'thermometer_check': {   'result': '36.8 C (Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'malaria',
                                                                                                           'dengue',
                                                                                                           'infection'],
                                                                                          'memory_note': 'Afebrile; '
                                                                                                         'acute '
                                                                                                         'febrile '
                                                                                                         'illness '
                                                                                                         'excluded as '
                                                                                                         'cause of '
                                                                                                         'polyuria and '
                                                                                                         'thirst.'},
                                                                 'bp_measurement': {   'result': '130/85 mmHg (Stage 1 '
                                                                                                 'Hypertension)',
                                                                                       'info_gain': 0.2,
                                                                                       'suggests': [   'hypertension',
                                                                                                       'type_2_diabetes'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Borderline '
                                                                                                      'elevated BP; '
                                                                                                      'diabetic '
                                                                                                      'hypertension '
                                                                                                      'co-morbidity '
                                                                                                      'possible — '
                                                                                                      'blood glucose '
                                                                                                      'confirmation '
                                                                                                      'required.'},
                                                                 'skin_examination': {   'result': 'Darkening at nape '
                                                                                                   'and axilla — '
                                                                                                   'possible '
                                                                                                   'acanthosis '
                                                                                                   'nigricans',
                                                                                         'info_gain': 0.2,
                                                                                         'suggests': [   'type_2_diabetes',
                                                                                                         'insulin_resistance'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Suspicious '
                                                                                                        'skin '
                                                                                                        'darkening at '
                                                                                                        'neck folds; '
                                                                                                        'acanthosis '
                                                                                                        'nigricans '
                                                                                                        'raises '
                                                                                                        'insulin '
                                                                                                        'resistance '
                                                                                                        'concern.'},
                                                                 'urine_dipstick': {   'result': 'Glucose +++, Ketones '
                                                                                                 'Negative',
                                                                                       'info_gain': 0.5,
                                                                                       'suggests': ['type_2_diabetes'],
                                                                                       'rules_out': [   'diabetic_ketoacidosis'],
                                                                                       'memory_note': 'Glycosuria '
                                                                                                      'detected; '
                                                                                                      'strongly '
                                                                                                      'suggests '
                                                                                                      'hyperglycaemia '
                                                                                                      '— blood glucose '
                                                                                                      'confirmation '
                                                                                                      'required.'},
                                                                 'blood_glucose_strip': {   'result': 'Random Blood '
                                                                                                      'Sugar 285 mg/dL',
                                                                                            'info_gain': 1.0,
                                                                                            'suggests': [   'type_2_diabetes'],
                                                                                            'rules_out': [   'hypoglycemia',
                                                                                                             'normal_glucose'],
                                                                                            'memory_note': 'RBS 285 '
                                                                                                           'mg/dL '
                                                                                                           'meets WHO '
                                                                                                           'diagnostic '
                                                                                                           'threshold; '
                                                                                                           'Type 2 '
                                                                                                           'diabetes '
                                                                                                           'confirmed '
                                                                                                           '— initiate '
                                                                                                           'metformin '
                                                                                                           'and '
                                                                                                           'lifestyle '
                                                                                                           'counselling.'}}},
                                 '16-30': {   'symptoms': [   'frequent urination at night',
                                                              'excessive thirst',
                                                              'blurring of vision',
                                                              'new tingling in feet (neuropathy)'],
                                              'vitals': {'temp': '36.8 C', 'bp': '135/85', 'hr': 80, 'spo2': '99%'},
                                              'test_results': {   'thermometer_check': {   'result': '36.8 C '
                                                                                                     '(Afebrile)',
                                                                                           'info_gain': 0.0,
                                                                                           'suggests': [],
                                                                                           'rules_out': [   'malaria',
                                                                                                            'infection'],
                                                                                           'memory_note': 'Persistently '
                                                                                                          'afebrile; '
                                                                                                          'fever-based '
                                                                                                          'differential '
                                                                                                          'remains '
                                                                                                          'excluded.'},
                                                                  'bp_measurement': {   'result': '135/85 mmHg '
                                                                                                  '(Worsening)',
                                                                                        'info_gain': 0.3,
                                                                                        'suggests': [   'hypertension',
                                                                                                        'diabetic_nephropathy'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'Worsening BP '
                                                                                                       'trend; '
                                                                                                       'escalating '
                                                                                                       'hypertension '
                                                                                                       'may indicate '
                                                                                                       'early diabetic '
                                                                                                       'nephropathy — '
                                                                                                       'monitor renal '
                                                                                                       'function.'},
                                                                  'skin_examination': {   'result': 'Acanthosis '
                                                                                                    'nigricans '
                                                                                                    'confirmed at nape '
                                                                                                    'and both axillae',
                                                                                          'info_gain': 0.3,
                                                                                          'suggests': [   'type_2_diabetes',
                                                                                                          'insulin_resistance'],
                                                                                          'rules_out': [],
                                                                                          'memory_note': 'Worsening '
                                                                                                         'acanthosis '
                                                                                                         'nigricans '
                                                                                                         'now '
                                                                                                         'confirmed at '
                                                                                                         'multiple '
                                                                                                         'sites; '
                                                                                                         'escalating '
                                                                                                         'insulin '
                                                                                                         'resistance '
                                                                                                         'consistent '
                                                                                                         'with '
                                                                                                         'uncontrolled '
                                                                                                         'diabetes.'},
                                                                  'urine_dipstick': {   'result': 'Glucose +++, '
                                                                                                  'Ketones Negative, '
                                                                                                  'Protein Trace',
                                                                                        'info_gain': 0.6,
                                                                                        'suggests': [   'type_2_diabetes',
                                                                                                        'diabetic_nephropathy'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'Escalating '
                                                                                                       'microproteinuria '
                                                                                                       'now present '
                                                                                                       'alongside '
                                                                                                       'persistent '
                                                                                                       'glycosuria; '
                                                                                                       'early diabetic '
                                                                                                       'nephropathy '
                                                                                                       'emerging.'},
                                                                  'blood_glucose_strip': {   'result': 'Random Blood '
                                                                                                       'Sugar 310 '
                                                                                                       'mg/dL',
                                                                                             'info_gain': 1.0,
                                                                                             'suggests': [   'type_2_diabetes'],
                                                                                             'rules_out': [],
                                                                                             'memory_note': 'URGENT: '
                                                                                                            'Worsening '
                                                                                                            'RBS to '
                                                                                                            '310 '
                                                                                                            'mg/dL; '
                                                                                                            'uncontrolled '
                                                                                                            'diabetes '
                                                                                                            'with '
                                                                                                            'escalating '
                                                                                                            'neuropathy '
                                                                                                            'and '
                                                                                                            'nephropathy '
                                                                                                            'risk.'}}}}},
    {   'id': 'case_03',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 45, 'gender': 'male', 'location': 'Rural Punjab'},
        'hidden_diagnosis': 'hypertension',
        'budget': 10,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'bp_measurement': 1,
                          'urine_dipstick': 2,
                          'pulse_oximeter': 2},
        'relevant_tests': ['bp_measurement', 'urine_dipstick'],
        'conclusive_test': 'bp_measurement',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 30,
        'penalty_events': {'hypertensive_crisis_missed': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1-30': {   'symptoms': [   'dizziness',
                                                             'occipital headache in mornings',
                                                             'palpitations'],
                                             'vitals': {'temp': '37.0 C', 'bp': '175/105', 'hr': 92, 'spo2': '98%'},
                                             'test_results': {   'thermometer_check': {   'result': '37.0 C (Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'malaria',
                                                                                                           'infection'],
                                                                                          'memory_note': 'Afebrile '
                                                                                                         '37.0C; '
                                                                                                         'infectious '
                                                                                                         'cause of '
                                                                                                         'headache '
                                                                                                         'excluded.'},
                                                                 'skin_examination': {   'result': 'Mild facial '
                                                                                                   'flushing; no rash; '
                                                                                                   'no pallor',
                                                                                         'info_gain': 0.05,
                                                                                         'suggests': ['hypertension'],
                                                                                         'rules_out': ['anaemia'],
                                                                                         'memory_note': 'Mild facial '
                                                                                                        'flushing '
                                                                                                        'noted; '
                                                                                                        'significant '
                                                                                                        'anaemia '
                                                                                                        'excluded. '
                                                                                                        'Non-specific '
                                                                                                        'finding '
                                                                                                        'alone.'},
                                                                 'bp_measurement': {   'result': '175/105 mmHg (Stage '
                                                                                                 '2 Hypertension)',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['hypertension'],
                                                                                       'rules_out': ['normal_bp'],
                                                                                       'memory_note': 'BP 175/105 mmHg '
                                                                                                      '— Stage 2 '
                                                                                                      'Hypertension '
                                                                                                      'confirmed. '
                                                                                                      'Initiate '
                                                                                                      'antihypertensive '
                                                                                                      'therapy and '
                                                                                                      'lifestyle '
                                                                                                      'modification.'},
                                                                 'urine_dipstick': {   'result': 'Protein Trace, '
                                                                                                 'Glucose Negative',
                                                                                       'info_gain': 0.2,
                                                                                       'suggests': [   'hypertensive_nephropathy'],
                                                                                       'rules_out': ['diabetes', 'uti'],
                                                                                       'memory_note': 'Trace '
                                                                                                      'proteinuria; '
                                                                                                      'possible early '
                                                                                                      'hypertensive '
                                                                                                      'renal '
                                                                                                      'involvement. '
                                                                                                      'Diabetes and '
                                                                                                      'UTI excluded.'},
                                                                 'pulse_oximeter': {   'result': 'SpO2 98%, PR 92 bpm',
                                                                                       'info_gain': 0.05,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'heart_failure',
                                                                                                        'respiratory_cause'],
                                                                                       'memory_note': 'SpO2 98%; '
                                                                                                      'significant '
                                                                                                      'cardiac '
                                                                                                      'decompensation '
                                                                                                      'and respiratory '
                                                                                                      'cause of '
                                                                                                      'symptoms '
                                                                                                      'excluded.'}}}}},
    {   'id': 'case_04',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 60, 'gender': 'male', 'location': 'Village in Kerala'},
        'hidden_diagnosis': 'ischaemic_heart_disease',
        'budget': 9,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'chest_auscultation': 1,
                          'bp_measurement': 1,
                          'pulse_oximeter': 2},
        'relevant_tests': ['bp_measurement', 'pulse_oximeter', 'skin_examination'],
        'conclusive_test': 'skin_examination',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Cardiac Emergency)',
        'critical_window_days': 1,
        'penalty_events': {   'delayed_referral_post_symptom_onset': -1.0,
                              'budget_exhausted': -0.5,
                              'duplicate_test': -0.2},
        'daily_progression': {   '1': {   'symptoms': [   'heavy chest pain radiating to left arm',
                                                          'sweating',
                                                          'shortness of breath',
                                                          'nausea',
                                                          'feeling of impending doom'],
                                          'vitals': {'temp': '36.5 C', 'bp': '150/90', 'hr': 110, 'spo2': '94%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.5 C (Afebrile)',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'infection',
                                                                                                        'malaria'],
                                                                                       'memory_note': 'Afebrile; '
                                                                                                      'infective cause '
                                                                                                      'of chest pain '
                                                                                                      'excluded.'},
                                                              'skin_examination': {   'result': 'Profuse diaphoresis '
                                                                                                '(cold sweats), pale '
                                                                                                'extremities',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'ischaemic_heart_disease',
                                                                                                      'myocardial_infarction'],
                                                                                      'rules_out': [   'musculoskeletal_pain',
                                                                                                       'anxiety'],
                                                                                      'memory_note': 'Profuse cold '
                                                                                                     'sweats with '
                                                                                                     'peripheral '
                                                                                                     'pallor and arm '
                                                                                                     'radiation — '
                                                                                                     'classic '
                                                                                                     'autonomic '
                                                                                                     'response of '
                                                                                                     'acute MI. URGENT '
                                                                                                     'referral to '
                                                                                                     'cardiac '
                                                                                                     'emergency.'},
                                                              'chest_auscultation': {   'result': 'Normal heart '
                                                                                                  'sounds; no murmur; '
                                                                                                  'mild basal '
                                                                                                  'crepitations',
                                                                                        'info_gain': 0.3,
                                                                                        'suggests': [   'ischaemic_heart_disease',
                                                                                                        'early_heart_failure'],
                                                                                        'rules_out': [   'pneumonia',
                                                                                                         'pleuritis'],
                                                                                        'memory_note': 'Mild basal '
                                                                                                       'crepitations '
                                                                                                       'suggest early '
                                                                                                       'pulmonary '
                                                                                                       'oedema; no '
                                                                                                       'pericardial '
                                                                                                       'rub. '
                                                                                                       'Consistent '
                                                                                                       'with acute '
                                                                                                       'ischaemic '
                                                                                                       'event.'},
                                                              'bp_measurement': {   'result': '150/90 mmHg',
                                                                                    'info_gain': 0.2,
                                                                                    'suggests': [   'hypertension',
                                                                                                    'ischaemic_heart_disease'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Hypertensive BP in '
                                                                                                   'context of chest '
                                                                                                   'pain; known risk '
                                                                                                   'factor and acute '
                                                                                                   'stress response in '
                                                                                                   'MI.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 94%, PR 110 bpm '
                                                                                              '(Tachycardia)',
                                                                                    'info_gain': 0.3,
                                                                                    'suggests': [   'ischaemic_heart_disease',
                                                                                                    'heart_failure'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'SpO2 94% with '
                                                                                                   'tachycardia; '
                                                                                                   'significant '
                                                                                                   'haemodynamic '
                                                                                                   'compromise '
                                                                                                   'consistent with '
                                                                                                   'acute MI — '
                                                                                                   'immediate referral '
                                                                                                   'mandatory.'}}}}},
    {   'id': 'case_05',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 16, 'gender': 'female', 'location': 'Tribal district, Jharkhand'},
        'hidden_diagnosis': 'nutritional_anemia',
        'budget': 12,
        'test_costs': {   'thermometer_check': 1,
                          'bp_measurement': 1,
                          'urine_dipstick': 2,
                          'skin_examination': 1,
                          'hemoglobin_strip': 4},
        'relevant_tests': ['skin_examination', 'hemoglobin_strip'],
        'conclusive_test': 'hemoglobin_strip',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 30,
        'penalty_events': {'severe_anaemia_untreated': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1-30': {   'symptoms': [   'severe fatigue',
                                                             'breathlessness on walking',
                                                             'craving to eat dirt (pica)',
                                                             'dizziness'],
                                             'vitals': {'temp': '37.0 C', 'bp': '100/60', 'hr': 105, 'spo2': '98%'},
                                             'test_results': {   'thermometer_check': {   'result': '37.0 C (Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'malaria',
                                                                                                           'infection'],
                                                                                          'memory_note': 'Afebrile; '
                                                                                                         'infectious '
                                                                                                         'cause of '
                                                                                                         'fatigue '
                                                                                                         'excluded.'},
                                                                 'bp_measurement': {   'result': '100/60 mmHg (Low)',
                                                                                       'info_gain': 0.2,
                                                                                       'suggests': [   'nutritional_anemia',
                                                                                                       'dehydration'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Low BP 100/60; '
                                                                                                      'hypotension '
                                                                                                      'consistent with '
                                                                                                      'severe anaemia '
                                                                                                      'and reduced '
                                                                                                      'cardiac '
                                                                                                      'preload.'},
                                                                 'urine_dipstick': {   'result': 'Normal; Glucose '
                                                                                                 'Negative, Protein '
                                                                                                 'Negative',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'diabetes',
                                                                                                        'uti',
                                                                                                        'renal_disease'],
                                                                                       'memory_note': 'Urinalysis '
                                                                                                      'normal; renal, '
                                                                                                      'diabetic and '
                                                                                                      'urinary causes '
                                                                                                      'of fatigue '
                                                                                                      'excluded.'},
                                                                 'skin_examination': {   'result': 'Pronounced pallor '
                                                                                                   'in conjunctiva and '
                                                                                                   'palms, koilonychia '
                                                                                                   '(spoon nails)',
                                                                                         'info_gain': 0.5,
                                                                                         'suggests': [   'iron_deficiency_anemia',
                                                                                                         'nutritional_anemia'],
                                                                                         'rules_out': ['malaria'],
                                                                                         'memory_note': 'Koilonychia '
                                                                                                        'and '
                                                                                                        'conjunctival '
                                                                                                        'pallor '
                                                                                                        'strongly '
                                                                                                        'suggest iron '
                                                                                                        'deficiency '
                                                                                                        'anaemia; '
                                                                                                        'haemoglobin '
                                                                                                        'confirmation '
                                                                                                        'required.'},
                                                                 'hemoglobin_strip': {   'result': '7.2 g/dL (Severe '
                                                                                                   'Anaemia)',
                                                                                         'info_gain': 1.0,
                                                                                         'suggests': [   'nutritional_anemia',
                                                                                                         'iron_deficiency'],
                                                                                         'rules_out': [   'normal_hemoglobin'],
                                                                                         'memory_note': 'Hb 7.2 g/dL — '
                                                                                                        'severe '
                                                                                                        'anaemia '
                                                                                                        'confirmed. '
                                                                                                        'With '
                                                                                                        'koilonychia '
                                                                                                        'and pica, '
                                                                                                        'iron '
                                                                                                        'deficiency '
                                                                                                        'nutritional '
                                                                                                        'anaemia '
                                                                                                        'established. '
                                                                                                        'Initiate iron '
                                                                                                        'supplementation.'}}}}},
    {   'id': 'case_06',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 4, 'gender': 'male', 'location': 'Rural Bihar'},
        'hidden_diagnosis': 'diarrheal_disease_with_dehydration',
        'budget': 8,
        'test_costs': {'thermometer_check': 1, 'skin_examination': 1, 'pulse_oximeter': 2, 'bp_measurement': 1},
        'relevant_tests': ['skin_examination', 'bp_measurement'],
        'conclusive_test': 'skin_examination',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 1,
        'penalty_events': {'hypovolemic_shock_without_ors': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1': {   'symptoms': [   'watery loose stools 8 times today',
                                                          'vomiting',
                                                          'lethargy',
                                                          'decreased urination'],
                                          'vitals': {'temp': '37.5 C', 'bp': '85/55', 'hr': 130, 'spo2': '97%'},
                                          'test_results': {   'thermometer_check': {   'result': '37.5 C (Low-grade '
                                                                                                 'fever)',
                                                                                       'info_gain': 0.1,
                                                                                       'suggests': [   'gastroenteritis',
                                                                                                       'enteric_infection'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Low-grade fever '
                                                                                                      '37.5C; mild '
                                                                                                      'systemic '
                                                                                                      'response to '
                                                                                                      'enteric '
                                                                                                      'infection '
                                                                                                      'noted.'},
                                                              'skin_examination': {   'result': 'Decreased skin turgor '
                                                                                                '(pinch recoil slow), '
                                                                                                'sunken eyes, dry '
                                                                                                'mucosa',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'dehydration',
                                                                                                      'diarrheal_disease'],
                                                                                      'rules_out': [   'malnutrition_only'],
                                                                                      'memory_note': 'Classic triad of '
                                                                                                     'dehydration — '
                                                                                                     'decreased '
                                                                                                     'turgor, sunken '
                                                                                                     'eyes, dry mucosa '
                                                                                                     'confirmed. '
                                                                                                     'Moderate-to-severe '
                                                                                                     'dehydration. '
                                                                                                     'Initiate ORS '
                                                                                                     'immediately.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 97%, PR 130 bpm '
                                                                                              '(Tachycardia)',
                                                                                    'info_gain': 0.2,
                                                                                    'suggests': [   'dehydration',
                                                                                                    'shock'],
                                                                                    'rules_out': ['pneumonia'],
                                                                                    'memory_note': 'Tachycardia 130 '
                                                                                                   'bpm; haemodynamic '
                                                                                                   'compromise from '
                                                                                                   'dehydration. '
                                                                                                   'Respiratory '
                                                                                                   'compromise '
                                                                                                   'excluded.'},
                                                              'bp_measurement': {   'result': '85/55 mmHg (Borderline '
                                                                                              'hypotension for age)',
                                                                                    'info_gain': 0.4,
                                                                                    'suggests': [   'dehydration',
                                                                                                    'hypovolemic_shock'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Borderline '
                                                                                                   'hypotension 85/55 '
                                                                                                   'mmHg; hypovolaemic '
                                                                                                   'shock threshold '
                                                                                                   'approaching — '
                                                                                                   'urgent rehydration '
                                                                                                   'required.'}}}}},
    {   'id': 'case_07',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 28, 'gender': 'male', 'location': 'Forest fringe, Chhattisgarh'},
        'hidden_diagnosis': 'malaria',
        'budget': 14,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'pulse_oximeter': 2,
                          'blood_panel': 5,
                          'rapid_malaria_test': 3},
        'relevant_tests': ['thermometer_check', 'rapid_malaria_test', 'blood_panel'],
        'conclusive_test': 'rapid_malaria_test',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 2,
        'penalty_events': {'missed_diagnosis_after_day_2': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1': {   'symptoms': ['high grade fever', 'shivering/chills', 'sweating', 'body ache'],
                                          'vitals': {'temp': '39.6 C', 'bp': '110/70', 'hr': 108, 'spo2': '98%'},
                                          'test_results': {   'thermometer_check': {   'result': '39.6 C',
                                                                                       'info_gain': 0.3,
                                                                                       'suggests': [   'malaria',
                                                                                                       'dengue',
                                                                                                       'typhoid'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'High fever '
                                                                                                      '39.6C; febrile '
                                                                                                      'illness with '
                                                                                                      'malarial '
                                                                                                      'periodicity '
                                                                                                      'pattern '
                                                                                                      'suspected — '
                                                                                                      'non-specific '
                                                                                                      'alone.'},
                                                              'rapid_malaria_test': {   'result': 'Positive for '
                                                                                                  'Plasmodium vivax',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': ['malaria'],
                                                                                        'rules_out': [   'typhoid',
                                                                                                         'dengue',
                                                                                                         'kala_azar'],
                                                                                        'memory_note': 'RDT confirms '
                                                                                                       'P. vivax '
                                                                                                       'malaria. '
                                                                                                       'Diagnosis '
                                                                                                       'established — '
                                                                                                       'initiate '
                                                                                                       'chloroquine '
                                                                                                       'and primaquine '
                                                                                                       'regimen.'},
                                                              'blood_panel': {   'result': 'Hb 10.5 g/dL, Platelets '
                                                                                           '140,000/mcL, WBC 5,200/mcL',
                                                                                 'info_gain': 0.2,
                                                                                 'suggests': ['malaria', 'dengue'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'Mild anaemia and '
                                                                                                'borderline '
                                                                                                'thrombocytopenia; '
                                                                                                'consistent with early '
                                                                                                'malaria but '
                                                                                                'non-specific without '
                                                                                                'RDT.'},
                                                              'skin_examination': {   'result': 'No rash, no '
                                                                                                'petechiae, no '
                                                                                                'significant pallor',
                                                                                      'info_gain': 0.0,
                                                                                      'suggests': [],
                                                                                      'rules_out': [   'dengue',
                                                                                                       'nutritional_anemia'],
                                                                                      'memory_note': 'Skin examination '
                                                                                                     'unremarkable; '
                                                                                                     'dengue '
                                                                                                     'haemorrhagic '
                                                                                                     'rash and '
                                                                                                     'significant '
                                                                                                     'anaemia pallor '
                                                                                                     'excluded.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 98%, PR 108 bpm',
                                                                                    'info_gain': 0.05,
                                                                                    'suggests': [],
                                                                                    'rules_out': [   'pneumonia',
                                                                                                     'copd_exacerbation'],
                                                                                    'memory_note': 'Oxygen saturation '
                                                                                                   '98%; significant '
                                                                                                   'respiratory '
                                                                                                   'compromise '
                                                                                                   'excluded at this '
                                                                                                   'stage.'}}},
                                 '2': {   'symptoms': [   'persistent high fever',
                                                          'severe rigors',
                                                          'vomiting',
                                                          'extreme weakness',
                                                          'altered sensorium'],
                                          'vitals': {'temp': '40.1 C', 'bp': '100/65', 'hr': 120, 'spo2': '97%'},
                                          'test_results': {   'thermometer_check': {   'result': '40.1 C',
                                                                                       'info_gain': 0.4,
                                                                                       'suggests': [   'malaria',
                                                                                                       'severe_malaria'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Escalating '
                                                                                                      'fever to 40.1C '
                                                                                                      'with worsening '
                                                                                                      'rigors; severe '
                                                                                                      'malaria '
                                                                                                      'progression '
                                                                                                      'with cerebral '
                                                                                                      'involvement '
                                                                                                      'risk.'},
                                                              'rapid_malaria_test': {   'result': 'Positive for '
                                                                                                  'Plasmodium vivax',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': ['malaria'],
                                                                                        'rules_out': [   'typhoid',
                                                                                                         'dengue'],
                                                                                        'memory_note': 'URGENT: RDT '
                                                                                                       'persistently '
                                                                                                       'positive with '
                                                                                                       'altered '
                                                                                                       'sensorium — P. '
                                                                                                       'vivax '
                                                                                                       'confirmed, '
                                                                                                       'escalating to '
                                                                                                       'severe '
                                                                                                       'malaria.'},
                                                              'blood_panel': {   'result': 'Hb 9.8 g/dL, Platelets '
                                                                                           '110,000/mcL, WBC 4,800/mcL',
                                                                                 'info_gain': 0.3,
                                                                                 'suggests': [   'malaria',
                                                                                                 'severe_malaria'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'Worsening anaemia '
                                                                                                '(9.8 g/dL) and '
                                                                                                'falling platelets; '
                                                                                                'disease progression '
                                                                                                'confirms escalating '
                                                                                                'severe malaria.'},
                                                              'skin_examination': {   'result': 'Mild pallor noted in '
                                                                                                'conjunctiva; no rash',
                                                                                      'info_gain': 0.1,
                                                                                      'suggests': ['malaria'],
                                                                                      'rules_out': ['dengue'],
                                                                                      'memory_note': 'Emerging pallor '
                                                                                                     'consistent with '
                                                                                                     'worsening '
                                                                                                     'haemolysis; '
                                                                                                     'dengue rash '
                                                                                                     'absent, '
                                                                                                     'reinforcing '
                                                                                                     'malaria '
                                                                                                     'diagnosis.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 97%, PR 120 bpm',
                                                                                    'info_gain': 0.1,
                                                                                    'suggests': ['severe_malaria'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Escalating '
                                                                                                   'tachycardia (120 '
                                                                                                   'bpm); SpO2 '
                                                                                                   'marginally '
                                                                                                   'declining — '
                                                                                                   'monitor closely '
                                                                                                   'for respiratory '
                                                                                                   'deterioration.'}}}}},
    {   'id': 'case_08',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 22, 'gender': 'female', 'location': 'Urban Tamil Nadu'},
        'hidden_diagnosis': 'dengue',
        'budget': 20,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'tourniquet_test': 1,
                          'pulse_oximeter': 2,
                          'blood_panel': 5,
                          'rapid_dengue_test': 5},
        'relevant_tests': ['tourniquet_test', 'rapid_dengue_test', 'blood_panel'],
        'conclusive_test': 'rapid_dengue_test',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 3,
        'penalty_events': {'dengue_shock_without_referral': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1': {   'symptoms': [   'sudden fever',
                                                          'severe bone pain (breakbone fever)',
                                                          'retro-orbital pain',
                                                          'nausea'],
                                          'vitals': {'temp': '39.2 C', 'bp': '105/65', 'hr': 100, 'spo2': '98%'},
                                          'test_results': {   'thermometer_check': {   'result': '39.2 C (Abrupt-onset '
                                                                                                 'fever)',
                                                                                       'info_gain': 0.2,
                                                                                       'suggests': [   'dengue',
                                                                                                       'malaria',
                                                                                                       'typhoid'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'High fever '
                                                                                                      '39.2C abrupt '
                                                                                                      'onset; febrile '
                                                                                                      'illness with '
                                                                                                      'dengue-compatible '
                                                                                                      'pattern.'},
                                                              'skin_examination': {   'result': 'No petechiae visible; '
                                                                                                'no rash yet',
                                                                                      'info_gain': 0.05,
                                                                                      'suggests': [],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'No cutaneous '
                                                                                                     'haemorrhagic '
                                                                                                     'signs at this '
                                                                                                     'stage; dengue '
                                                                                                     'rash typically '
                                                                                                     'appears by day '
                                                                                                     '3.'},
                                                              'tourniquet_test': {   'result': 'Positive (>10 '
                                                                                               'petechiae)',
                                                                                     'info_gain': 0.4,
                                                                                     'suggests': [   'dengue',
                                                                                                     'dengue_haemorrhagic_fever'],
                                                                                     'rules_out': [],
                                                                                     'memory_note': 'Positive '
                                                                                                    'tourniquet test '
                                                                                                    'with >10 '
                                                                                                    'petechiae; '
                                                                                                    'capillary '
                                                                                                    'fragility '
                                                                                                    'confirmed — '
                                                                                                    'dengue '
                                                                                                    'haemorrhagic risk '
                                                                                                    'flagged.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 98%, PR 100 bpm',
                                                                                    'info_gain': 0.05,
                                                                                    'suggests': [],
                                                                                    'rules_out': [   'respiratory_failure'],
                                                                                    'memory_note': 'SpO2 98%; no '
                                                                                                   'respiratory '
                                                                                                   'compromise at this '
                                                                                                   'stage.'},
                                                              'blood_panel': {   'result': 'Platelets 95,000/mcL, WBC '
                                                                                           '3,200/mcL',
                                                                                 'info_gain': 0.3,
                                                                                 'suggests': ['dengue', 'viral_fever'],
                                                                                 'rules_out': ['bacterial_sepsis'],
                                                                                 'memory_note': 'Thrombocytopenia and '
                                                                                                'leukopenia; '
                                                                                                'characteristic of '
                                                                                                'dengue viral illness '
                                                                                                '— bacterial sepsis '
                                                                                                'excluded.'},
                                                              'rapid_dengue_test': {   'result': 'NS1 Antigen Positive',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['dengue'],
                                                                                       'rules_out': [   'malaria',
                                                                                                        'typhoid',
                                                                                                        'chikungunya'],
                                                                                       'memory_note': 'NS1 antigen '
                                                                                                      'positive on day '
                                                                                                      '1; dengue '
                                                                                                      'confirmed in '
                                                                                                      'febrile phase. '
                                                                                                      'Monitor for '
                                                                                                      'warning signs '
                                                                                                      'closely.'}}},
                                 '2': {   'symptoms': [   'fever breaking (critical phase)',
                                                          'abdominal pain',
                                                          'persistent vomiting',
                                                          'lethargy'],
                                          'vitals': {'temp': '37.5 C', 'bp': '95/60', 'hr': 110, 'spo2': '98%'},
                                          'test_results': {   'thermometer_check': {   'result': '37.5 C (Fever '
                                                                                                 'defervescing — '
                                                                                                 'critical phase '
                                                                                                 'entry)',
                                                                                       'info_gain': 0.3,
                                                                                       'suggests': [   'dengue_critical_phase'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Escalating '
                                                                                                      'concern: fever '
                                                                                                      'breaking '
                                                                                                      'signals entry '
                                                                                                      'into dengue '
                                                                                                      'critical phase '
                                                                                                      '— plasma '
                                                                                                      'leakage risk '
                                                                                                      'increases now.'},
                                                              'skin_examination': {   'result': 'Mild flushing; no '
                                                                                                'spontaneous petechiae '
                                                                                                'yet',
                                                                                      'info_gain': 0.1,
                                                                                      'suggests': ['dengue'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Worsening '
                                                                                                     'flushing; '
                                                                                                     'clinical '
                                                                                                     'evolution '
                                                                                                     'consistent with '
                                                                                                     'dengue '
                                                                                                     'progression. '
                                                                                                     'Spontaneous '
                                                                                                     'bleeding not yet '
                                                                                                     'manifest.'},
                                                              'tourniquet_test': {   'result': 'Positive (>20 '
                                                                                               'petechiae)',
                                                                                     'info_gain': 0.5,
                                                                                     'suggests': [   'dengue_haemorrhagic_fever',
                                                                                                     'plasma_leakage'],
                                                                                     'rules_out': [],
                                                                                     'memory_note': 'Worsening '
                                                                                                    'capillary '
                                                                                                    'fragility: >20 '
                                                                                                    'petechiae now. '
                                                                                                    'Escalating '
                                                                                                    'haemorrhagic '
                                                                                                    'dengue — monitor '
                                                                                                    'BP and platelets '
                                                                                                    'urgently.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 98%, PR 110 bpm',
                                                                                    'info_gain': 0.15,
                                                                                    'suggests': [   'dengue_critical_phase'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Rising tachycardia '
                                                                                                   '110 bpm during '
                                                                                                   'fever '
                                                                                                   'defervescence; '
                                                                                                   'warning sign for '
                                                                                                   'haemodynamic '
                                                                                                   'compromise.'},
                                                              'blood_panel': {   'result': 'Platelets 60,000/mcL, WBC '
                                                                                           '2,800/mcL, rising '
                                                                                           'haematocrit',
                                                                                 'info_gain': 0.5,
                                                                                 'suggests': [   'dengue_haemorrhagic_fever',
                                                                                                 'plasma_leakage'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'Worsening '
                                                                                                'thrombocytopenia '
                                                                                                '(60K) with rising '
                                                                                                'haematocrit — '
                                                                                                'classical dengue '
                                                                                                'plasma leakage '
                                                                                                'pattern escalating.'},
                                                              'rapid_dengue_test': {   'result': 'NS1 Antigen '
                                                                                                 'Positive, IgM '
                                                                                                 'Positive',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['dengue'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'URGENT: Both '
                                                                                                      'NS1 and IgM '
                                                                                                      'positive — '
                                                                                                      'confirmed '
                                                                                                      'dengue with '
                                                                                                      'escalating '
                                                                                                      'haemorrhagic '
                                                                                                      'features. '
                                                                                                      'Critical phase '
                                                                                                      'monitoring '
                                                                                                      'mandatory.'}}},
                                 '3': {   'symptoms': [   'bleeding from gums',
                                                          'severe abdominal pain',
                                                          'restlessness',
                                                          'cold clammy skin'],
                                          'vitals': {'temp': '36.8 C', 'bp': '85/55', 'hr': 130, 'spo2': '96%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.8 C (Afebrile — '
                                                                                                 'shock phase)',
                                                                                       'info_gain': 0.3,
                                                                                       'suggests': [   'dengue_shock_syndrome'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Afebrile but '
                                                                                                      'haemodynamically '
                                                                                                      'deteriorating — '
                                                                                                      'dengue shock '
                                                                                                      'syndrome now '
                                                                                                      'imminent.'},
                                                              'skin_examination': {   'result': 'Spontaneous petechiae '
                                                                                                'visible without test; '
                                                                                                'cool clammy skin',
                                                                                      'info_gain': 0.8,
                                                                                      'suggests': [   'dengue_haemorrhagic_fever',
                                                                                                      'dengue_shock_syndrome'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'URGENT: '
                                                                                                     'Spontaneous '
                                                                                                     'petechiae and '
                                                                                                     'cold clammy '
                                                                                                     'extremities — '
                                                                                                     'clinical dengue '
                                                                                                     'shock syndrome. '
                                                                                                     'Immediate '
                                                                                                     'referral '
                                                                                                     'required.'},
                                                              'tourniquet_test': {   'result': 'Spontaneous petechiae '
                                                                                               'visible — formal test '
                                                                                               'unnecessary',
                                                                                     'info_gain': 0.5,
                                                                                     'suggests': [   'dengue_shock_syndrome'],
                                                                                     'rules_out': [],
                                                                                     'memory_note': 'URGENT: Test '
                                                                                                    'unnecessary — '
                                                                                                    'spontaneous '
                                                                                                    'haemorrhage '
                                                                                                    'confirms severe '
                                                                                                    'dengue. Patient '
                                                                                                    'needs urgent '
                                                                                                    'transfusion '
                                                                                                    'facility.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 96%, PR 130 bpm',
                                                                                    'info_gain': 0.4,
                                                                                    'suggests': [   'dengue_shock_syndrome',
                                                                                                    'hypovolemia'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'URGENT: Escalating '
                                                                                                   'tachycardia 130 '
                                                                                                   'bpm with falling '
                                                                                                   'SpO2 — '
                                                                                                   'haemodynamic '
                                                                                                   'collapse '
                                                                                                   'progressing.'},
                                                              'blood_panel': {   'result': 'Platelets 25,000/mcL '
                                                                                           '(Critical); WBC 2,400/mcL',
                                                                                 'info_gain': 0.8,
                                                                                 'suggests': [   'dengue_shock_syndrome',
                                                                                                 'dengue_haemorrhagic_fever'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'URGENT: Platelets '
                                                                                                'collapsed to '
                                                                                                '25,000/mcL — '
                                                                                                'life-threatening '
                                                                                                'thrombocytopenia. '
                                                                                                'Platelet transfusion '
                                                                                                'required urgently.'},
                                                              'rapid_dengue_test': {   'result': 'IgM Positive',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['dengue'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'URGENT: '
                                                                                                      'IgM-confirmed '
                                                                                                      'dengue in shock '
                                                                                                      'phase — '
                                                                                                      'escalating to '
                                                                                                      'dengue shock '
                                                                                                      'syndrome. '
                                                                                                      'Immediate '
                                                                                                      'hospital '
                                                                                                      'referral '
                                                                                                      'mandatory.'}}}}},
    {   'id': 'case_09',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 68, 'gender': 'male', 'location': 'Village in Rajasthan'},
        'hidden_diagnosis': 'copd_exacerbation',
        'budget': 15,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'bp_measurement': 1,
                          'chest_auscultation': 1,
                          'pulse_oximeter': 2,
                          'sputum_smear': 6},
        'relevant_tests': ['pulse_oximeter', 'chest_auscultation', 'sputum_smear'],
        'conclusive_test': 'pulse_oximeter',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Respiratory Ward)',
        'critical_window_days': 1,
        'penalty_events': {'hypoxia_without_referral': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1': {   'symptoms': [   'worsening breathlessness',
                                                          'productive cough with green sputum',
                                                          'inability to speak full sentences'],
                                          'vitals': {'temp': '37.6 C', 'bp': '145/85', 'hr': 112, 'spo2': '88%'},
                                          'test_results': {   'thermometer_check': {   'result': '37.6 C (Low-grade '
                                                                                                 'fever)',
                                                                                       'info_gain': 0.1,
                                                                                       'suggests': [   'infection',
                                                                                                       'copd_infective_exacerbation'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Low-grade fever '
                                                                                                      '37.6C; '
                                                                                                      'infective '
                                                                                                      'trigger for '
                                                                                                      'COPD '
                                                                                                      'exacerbation '
                                                                                                      'likely.'},
                                                              'skin_examination': {   'result': 'Central cyanosis of '
                                                                                                'lips and fingernails; '
                                                                                                'barrel-shaped chest',
                                                                                      'info_gain': 0.4,
                                                                                      'suggests': [   'copd',
                                                                                                      'respiratory_failure'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Central cyanosis '
                                                                                                     'and barrel '
                                                                                                     'chest; chronic '
                                                                                                     'obstructive '
                                                                                                     'pulmonary '
                                                                                                     'pathology with '
                                                                                                     'acute '
                                                                                                     'decompensation '
                                                                                                     'evident.'},
                                                              'bp_measurement': {   'result': '145/85 mmHg',
                                                                                    'info_gain': 0.1,
                                                                                    'suggests': ['hypertension'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Elevated BP; '
                                                                                                   'chronic '
                                                                                                   'hypertension '
                                                                                                   'co-morbidity, not '
                                                                                                   'driving acute '
                                                                                                   'management.'},
                                                              'chest_auscultation': {   'result': 'Diffuse expiratory '
                                                                                                  'wheeze, prolonged '
                                                                                                  'expiration, '
                                                                                                  'bilateral coarse '
                                                                                                  'crepitations',
                                                                                        'info_gain': 0.5,
                                                                                        'suggests': [   'copd_exacerbation',
                                                                                                        'copd'],
                                                                                        'rules_out': ['pneumothorax'],
                                                                                        'memory_note': 'Expiratory '
                                                                                                       'wheeze with '
                                                                                                       'prolonged '
                                                                                                       'expiration — '
                                                                                                       'obstructive '
                                                                                                       'pattern '
                                                                                                       'consistent '
                                                                                                       'with COPD '
                                                                                                       'exacerbation. '
                                                                                                       'Pneumothorax '
                                                                                                       'excluded.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 88% on room air',
                                                                                    'info_gain': 1.0,
                                                                                    'suggests': [   'copd_exacerbation',
                                                                                                    'respiratory_failure'],
                                                                                    'rules_out': ['mild_bronchitis'],
                                                                                    'memory_note': 'SpO2 88% on room '
                                                                                                   'air — '
                                                                                                   'life-threatening '
                                                                                                   'hypoxia confirmed. '
                                                                                                   'COPD exacerbation '
                                                                                                   'with type 1 '
                                                                                                   'respiratory '
                                                                                                   'failure. URGENT '
                                                                                                   'referral '
                                                                                                   'required.'},
                                                              'sputum_smear': {   'result': 'Negative for AFB',
                                                                                  'info_gain': 0.0,
                                                                                  'suggests': [],
                                                                                  'rules_out': ['tuberculosis'],
                                                                                  'memory_note': 'AFB-negative sputum; '
                                                                                                 'tuberculosis '
                                                                                                 'excluded as cause of '
                                                                                                 'respiratory '
                                                                                                 'deterioration.'}}}}},
    {   'id': 'case_10',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 30, 'gender': 'female', 'location': 'Slum cluster, Mumbai'},
        'hidden_diagnosis': 'typhoid_fever',
        'budget': 20,
        'test_costs': {   'thermometer_check': 1,
                          'abdominal_exam': 1,
                          'urine_dipstick': 2,
                          'rapid_malaria_test': 3,
                          'blood_panel': 5,
                          'widal_test': 5},
        'relevant_tests': ['thermometer_check', 'abdominal_exam', 'widal_test'],
        'conclusive_test': 'widal_test',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 4,
        'penalty_events': {   'intestinal_perforation_without_referral': -1.0,
                              'budget_exhausted': -0.5,
                              'duplicate_test': -0.2},
        'daily_progression': {   '1-2': {   'symptoms': [   'fever for 8 days gradually increasing',
                                                            'dull headache',
                                                            'abdominal discomfort',
                                                            'constipation'],
                                            'vitals': {'temp': '39.0 C', 'bp': '115/75', 'hr': 80, 'spo2': '99%'},
                                            'test_results': {   'thermometer_check': {   'result': '39.0 C (Relative '
                                                                                                   'bradycardia noted)',
                                                                                         'info_gain': 0.2,
                                                                                         'suggests': [   'typhoid',
                                                                                                         'malaria',
                                                                                                         'dengue'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Sustained '
                                                                                                        '39.0C fever '
                                                                                                        'with '
                                                                                                        'pulse-temperature '
                                                                                                        'dissociation; '
                                                                                                        'relative '
                                                                                                        'bradycardia '
                                                                                                        'raises '
                                                                                                        'clinical '
                                                                                                        'suspicion for '
                                                                                                        'typhoid.'},
                                                                'abdominal_exam': {   'result': 'Mild splenomegaly, '
                                                                                                'diffuse tenderness',
                                                                                      'info_gain': 0.3,
                                                                                      'suggests': [   'typhoid',
                                                                                                      'hepatitis_a',
                                                                                                      'kala_azar'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Mild '
                                                                                                     'splenomegaly on '
                                                                                                     'palpation; '
                                                                                                     'narrows '
                                                                                                     'differential '
                                                                                                     'toward typhoid '
                                                                                                     'or viral '
                                                                                                     'hepatitis.'},
                                                                'widal_test': {   'result': 'Positive (TO 1:320, TH '
                                                                                            '1:160)',
                                                                                  'info_gain': 1.0,
                                                                                  'suggests': ['typhoid'],
                                                                                  'rules_out': [   'malaria',
                                                                                                   'dengue',
                                                                                                   'hepatitis_a'],
                                                                                  'memory_note': 'Widal TO 1:320 meets '
                                                                                                 'diagnostic '
                                                                                                 'threshold; typhoid '
                                                                                                 'fever confirmed — '
                                                                                                 'begin ciprofloxacin '
                                                                                                 'or azithromycin.'},
                                                                'blood_panel': {   'result': 'WBC 3,400/mcL '
                                                                                             '(leukopenia), Hb 11.2 '
                                                                                             'g/dL, Platelets '
                                                                                             '180,000/mcL',
                                                                                   'info_gain': 0.3,
                                                                                   'suggests': ['typhoid', 'dengue'],
                                                                                   'rules_out': [   'bacterial_pyogenic_infection'],
                                                                                   'memory_note': 'Leukopenia '
                                                                                                  'characteristic of '
                                                                                                  'Salmonella typhi; '
                                                                                                  'helps exclude '
                                                                                                  'pyogenic bacterial '
                                                                                                  'sepsis from '
                                                                                                  'differential.'},
                                                                'urine_dipstick': {   'result': 'Trace protein, '
                                                                                                'Glucose Negative, '
                                                                                                'Bilirubin Negative',
                                                                                      'info_gain': 0.05,
                                                                                      'suggests': [],
                                                                                      'rules_out': [   'diabetes',
                                                                                                       'uti',
                                                                                                       'hepatitis'],
                                                                                      'memory_note': 'Urine '
                                                                                                     'unremarkable; '
                                                                                                     'UTI, diabetes, '
                                                                                                     'and significant '
                                                                                                     'hepatic jaundice '
                                                                                                     'excluded.'},
                                                                'rapid_malaria_test': {   'result': 'Negative',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': ['malaria'],
                                                                                          'memory_note': 'Malaria '
                                                                                                         'excluded by '
                                                                                                         'RDT; febrile '
                                                                                                         'illness is '
                                                                                                         'non-malarial.'}}},
                                 '3-4': {   'symptoms': [   'high step-ladder fever',
                                                            'delirium/confusion',
                                                            'pea-soup diarrhea',
                                                            'rose spots on trunk'],
                                            'vitals': {'temp': '39.8 C', 'bp': '105/65', 'hr': 85, 'spo2': '98%'},
                                            'test_results': {   'thermometer_check': {   'result': '39.8 C '
                                                                                                   '(Step-ladder '
                                                                                                   'pattern)',
                                                                                         'info_gain': 0.35,
                                                                                         'suggests': [   'typhoid',
                                                                                                         'typhoid_complication'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Escalating '
                                                                                                        'step-ladder '
                                                                                                        'fever to '
                                                                                                        '39.8C; '
                                                                                                        'delirium and '
                                                                                                        'rose spots on '
                                                                                                        'trunk — '
                                                                                                        'worsening '
                                                                                                        'typhoid '
                                                                                                        'progression.'},
                                                                'abdominal_exam': {   'result': 'Significant '
                                                                                                'distension, tender '
                                                                                                'hepatosplenomegaly',
                                                                                      'info_gain': 0.5,
                                                                                      'suggests': [   'typhoid',
                                                                                                      'intestinal_perforation'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'URGENT: Marked '
                                                                                                     'hepatosplenomegaly '
                                                                                                     'with abdominal '
                                                                                                     'distension; '
                                                                                                     'intestinal '
                                                                                                     'perforation risk '
                                                                                                     '— consider '
                                                                                                     'urgent '
                                                                                                     'referral.'},
                                                                'widal_test': {   'result': 'Positive (TO 1:640, TH '
                                                                                            '1:320)',
                                                                                  'info_gain': 1.0,
                                                                                  'suggests': ['typhoid'],
                                                                                  'rules_out': ['malaria', 'dengue'],
                                                                                  'memory_note': 'URGENT: Widal titre '
                                                                                                 'doubled to TO 1:640; '
                                                                                                 'escalating active '
                                                                                                 'typhoid with '
                                                                                                 'impending '
                                                                                                 'complications '
                                                                                                 'confirmed.'},
                                                                'blood_panel': {   'result': 'WBC 2,800/mcL (worsening '
                                                                                             'leukopenia), Hb 10.5 '
                                                                                             'g/dL',
                                                                                   'info_gain': 0.4,
                                                                                   'suggests': [   'typhoid',
                                                                                                   'typhoid_complication'],
                                                                                   'rules_out': [],
                                                                                   'memory_note': 'Worsening '
                                                                                                  'leukopenia and '
                                                                                                  'anaemia; escalating '
                                                                                                  'systemic typhoid '
                                                                                                  'involvement with '
                                                                                                  'rising complication '
                                                                                                  'risk.'},
                                                                'urine_dipstick': {   'result': 'Trace protein, '
                                                                                                'Glucose Negative',
                                                                                      'info_gain': 0.05,
                                                                                      'suggests': [],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Persistent trace '
                                                                                                     'proteinuria; '
                                                                                                     'minor renal '
                                                                                                     'irritation, '
                                                                                                     'non-diagnostic '
                                                                                                     'and not driving '
                                                                                                     'management.'},
                                                                'rapid_malaria_test': {   'result': 'Negative',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': ['malaria'],
                                                                                          'memory_note': 'Malaria '
                                                                                                         'definitively '
                                                                                                         'excluded; '
                                                                                                         'fever '
                                                                                                         'entirely '
                                                                                                         'explained by '
                                                                                                         'worsening '
                                                                                                         'confirmed '
                                                                                                         'typhoid.'}}}}},
    {   'id': 'case_11',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 65, 'gender': 'female', 'location': 'Rural Haryana'},
        'hidden_diagnosis': 'stroke',
        'budget': 9,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'chest_auscultation': 1,
                          'bp_measurement': 1,
                          'pulse_oximeter': 2},
        'relevant_tests': ['bp_measurement', 'skin_examination'],
        'conclusive_test': 'skin_examination',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Stroke Unit)',
        'critical_window_days': 1,
        'penalty_events': {   'delayed_referral_beyond_thrombolysis_window': -1.0,
                              'budget_exhausted': -0.5,
                              'duplicate_test': -0.2},
        'daily_progression': {   '1': {   'symptoms': [   'sudden weakness in right arm and leg',
                                                          'slurred speech',
                                                          'facial droop on right side',
                                                          'confusion'],
                                          'vitals': {'temp': '36.9 C', 'bp': '185/110', 'hr': 88, 'spo2': '97%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.9 C (Afebrile)',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'febrile_seizure',
                                                                                                        'meningitis'],
                                                                                       'memory_note': 'Afebrile 36.9C; '
                                                                                                      'infective '
                                                                                                      'neurological '
                                                                                                      'cause such as '
                                                                                                      'meningitis or '
                                                                                                      'febrile seizure '
                                                                                                      'excluded.'},
                                                              'skin_examination': {   'result': 'Right-sided facial '
                                                                                                'paralysis, 0/5 motor '
                                                                                                'strength right '
                                                                                                'extremities',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'stroke',
                                                                                                      'ischaemic_stroke'],
                                                                                      'rules_out': [   'bell_palsy',
                                                                                                       'hypoglycemia_seizure'],
                                                                                      'memory_note': 'URGENT: Complete '
                                                                                                     'right hemiplegia '
                                                                                                     'with upper motor '
                                                                                                     'neuron facial '
                                                                                                     'droop — stroke '
                                                                                                     'pattern '
                                                                                                     'confirmed. '
                                                                                                     'Within '
                                                                                                     'thrombolysis '
                                                                                                     'window — '
                                                                                                     'immediate '
                                                                                                     'referral '
                                                                                                     'required.'},
                                                              'chest_auscultation': {   'result': 'Normal heart '
                                                                                                  'sounds; no added '
                                                                                                  'sounds',
                                                                                        'info_gain': 0.0,
                                                                                        'suggests': [],
                                                                                        'rules_out': [   'pneumonia',
                                                                                                         'pulmonary_oedema'],
                                                                                        'memory_note': 'Chest clear; '
                                                                                                       'pulmonary '
                                                                                                       'complication '
                                                                                                       'and aspiration '
                                                                                                       'pneumonia not '
                                                                                                       'yet present.'},
                                                              'bp_measurement': {   'result': '185/110 mmHg '
                                                                                              '(Hypertensive '
                                                                                              'Emergency)',
                                                                                    'info_gain': 0.4,
                                                                                    'suggests': [   'stroke',
                                                                                                    'hypertensive_emergency'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Hypertensive '
                                                                                                   'emergency 185/110; '
                                                                                                   'high BP consistent '
                                                                                                   'with haemorrhagic '
                                                                                                   'or ischaemic '
                                                                                                   'stroke aetiology.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 97%, PR 88 bpm',
                                                                                    'info_gain': 0.1,
                                                                                    'suggests': [],
                                                                                    'rules_out': [   'respiratory_failure'],
                                                                                    'memory_note': 'SpO2 97%; no '
                                                                                                   'respiratory '
                                                                                                   'compromise from '
                                                                                                   'aspiration at this '
                                                                                                   'stage.'}}}}},
    {   'id': 'case_12',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 25, 'gender': 'male', 'location': 'Post-flood village, Assam'},
        'hidden_diagnosis': 'hepatitis_a_or_e',
        'budget': 14,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'abdominal_exam': 1,
                          'urine_dipstick': 2,
                          'blood_panel': 5},
        'relevant_tests': ['skin_examination', 'abdominal_exam', 'urine_dipstick'],
        'conclusive_test': 'skin_examination',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Gastroenterology)',
        'critical_window_days': 7,
        'penalty_events': {   'acute_liver_failure_without_referral': -1.0,
                              'budget_exhausted': -0.5,
                              'duplicate_test': -0.2},
        'daily_progression': {   '1-3': {   'symptoms': [   'yellowish discoloration of eyes',
                                                            'dark urine',
                                                            'loss of appetite',
                                                            'nausea',
                                                            'mild right upper abdomen pain'],
                                            'vitals': {'temp': '37.5 C', 'bp': '110/70', 'hr': 82, 'spo2': '99%'},
                                            'test_results': {   'thermometer_check': {   'result': '37.5 C (Low-grade '
                                                                                                   'fever)',
                                                                                         'info_gain': 0.1,
                                                                                         'suggests': [   'hepatitis',
                                                                                                         'viral_infection'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Low-grade '
                                                                                                        'fever 37.5C; '
                                                                                                        'viral '
                                                                                                        'hepatitis '
                                                                                                        'prodromal '
                                                                                                        'fever '
                                                                                                        'pattern.'},
                                                                'skin_examination': {   'result': 'Pronounced icterus '
                                                                                                  '(yellow sclera) and '
                                                                                                  'mild generalised '
                                                                                                  'jaundice',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': [   'hepatitis_a',
                                                                                                        'hepatitis_e',
                                                                                                        'hepatitis_b'],
                                                                                        'rules_out': [   'malaria',
                                                                                                         'dengue'],
                                                                                        'memory_note': 'Icteric '
                                                                                                       'sclerae and '
                                                                                                       'jaundice '
                                                                                                       'confirmed — '
                                                                                                       'viral '
                                                                                                       'hepatitis '
                                                                                                       'established. '
                                                                                                       'Post-flood '
                                                                                                       'context '
                                                                                                       'suggests '
                                                                                                       'Hepatitis A or '
                                                                                                       'E. Referral '
                                                                                                       'indicated.'},
                                                                'abdominal_exam': {   'result': 'Tender hepatomegaly',
                                                                                      'info_gain': 0.4,
                                                                                      'suggests': [   'hepatitis',
                                                                                                      'hepatitis_a_or_e'],
                                                                                      'rules_out': ['cirrhosis'],
                                                                                      'memory_note': 'Tender '
                                                                                                     'hepatomegaly '
                                                                                                     'consistent with '
                                                                                                     'acute viral '
                                                                                                     'hepatitis; '
                                                                                                     'non-cirrhotic '
                                                                                                     'pattern.'},
                                                                'urine_dipstick': {   'result': 'Bilirubin +++, '
                                                                                                'Urobilinogen Normal',
                                                                                      'info_gain': 0.3,
                                                                                      'suggests': [   'hepatitis',
                                                                                                      'hepatocellular_jaundice'],
                                                                                      'rules_out': [   'obstructive_jaundice',
                                                                                                       'pre_hepatic_jaundice'],
                                                                                      'memory_note': 'Bilirubinuria '
                                                                                                     'with normal '
                                                                                                     'urobilinogen; '
                                                                                                     'pre-hepatic '
                                                                                                     'jaundice '
                                                                                                     'excluded, '
                                                                                                     'hepatocellular '
                                                                                                     'pattern '
                                                                                                     'consistent with '
                                                                                                     'hepatitis.'},
                                                                'blood_panel': {   'result': 'WBC 5,200/mcL (normal), '
                                                                                             'Hb 12.1 g/dL, raised '
                                                                                             'transaminases (clinical '
                                                                                             'estimate)',
                                                                                   'info_gain': 0.3,
                                                                                   'suggests': ['viral_hepatitis'],
                                                                                   'rules_out': ['bacterial_sepsis'],
                                                                                   'memory_note': 'Normal leukocyte '
                                                                                                  'count; bacterial '
                                                                                                  'sepsis excluded. '
                                                                                                  'Clinical picture '
                                                                                                  'supports acute '
                                                                                                  'viral hepatitis.'}}},
                                 '4-7': {   'symptoms': [   'deepening jaundice',
                                                            'severe fatigue',
                                                            'clay-colored stools',
                                                            'intense itching (pruritus)'],
                                            'vitals': {'temp': '37.2 C', 'bp': '105/65', 'hr': 78, 'spo2': '99%'},
                                            'test_results': {   'thermometer_check': {   'result': '37.2 C (Subsiding '
                                                                                                   'fever)',
                                                                                         'info_gain': 0.15,
                                                                                         'suggests': ['hepatitis'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Subsiding '
                                                                                                        'fever; '
                                                                                                        'typical viral '
                                                                                                        'hepatitis '
                                                                                                        'pattern — '
                                                                                                        'worsening '
                                                                                                        'jaundice '
                                                                                                        'despite '
                                                                                                        'improving '
                                                                                                        'pyrexia.'},
                                                                'skin_examination': {   'result': 'Deep icterus, '
                                                                                                  'scratch marks from '
                                                                                                  'pruritus',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': [   'hepatitis_a_or_e',
                                                                                                        'cholestatic_component'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'URGENT: '
                                                                                                       'Deepening '
                                                                                                       'jaundice with '
                                                                                                       'pruritic '
                                                                                                       'scratch marks '
                                                                                                       '— escalating '
                                                                                                       'cholestatic '
                                                                                                       'component. '
                                                                                                       'Refer for LFT '
                                                                                                       'monitoring and '
                                                                                                       'IV support.'},
                                                                'abdominal_exam': {   'result': 'Marked tender '
                                                                                                'hepatomegaly',
                                                                                      'info_gain': 0.5,
                                                                                      'suggests': [   'hepatitis_worsening',
                                                                                                      'hepatitis_a_or_e'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Worsening '
                                                                                                     'hepatomegaly and '
                                                                                                     'tenderness; '
                                                                                                     'escalating '
                                                                                                     'hepatic '
                                                                                                     'inflammation — '
                                                                                                     'acute liver '
                                                                                                     'failure risk '
                                                                                                     'rising.'},
                                                                'urine_dipstick': {   'result': 'Bilirubin +++, '
                                                                                                'Urobilinogen Absent',
                                                                                      'info_gain': 0.5,
                                                                                      'suggests': [   'obstructive_hepatitis',
                                                                                                      'cholestasis'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'URGENT: Absent '
                                                                                                     'urobilinogen '
                                                                                                     'with persistent '
                                                                                                     'bilirubinuria — '
                                                                                                     'cholestatic '
                                                                                                     'jaundice '
                                                                                                     'emerging, '
                                                                                                     'worsening '
                                                                                                     'hepatocellular '
                                                                                                     'damage.'},
                                                                'blood_panel': {   'result': 'Hb 10.5 g/dL (falling), '
                                                                                             'WBC 4,800/mcL, worsening '
                                                                                             'transaminases',
                                                                                   'info_gain': 0.4,
                                                                                   'suggests': [   'hepatitis_worsening',
                                                                                                   'acute_liver_failure_risk'],
                                                                                   'rules_out': [],
                                                                                   'memory_note': 'Worsening anaemia '
                                                                                                  'and escalating '
                                                                                                  'hepatic markers — '
                                                                                                  'progressive liver '
                                                                                                  'disease. URGENT '
                                                                                                  'referral for '
                                                                                                  'specialist '
                                                                                                  'management.'}}}}},
    {   'id': 'case_13',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 14, 'gender': 'male', 'location': 'Industrial outskirts, Gujarat'},
        'hidden_diagnosis': 'asthma',
        'budget': 9,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'bp_measurement': 1,
                          'chest_auscultation': 1,
                          'pulse_oximeter': 2},
        'relevant_tests': ['chest_auscultation', 'pulse_oximeter'],
        'conclusive_test': 'chest_auscultation',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 2,
        'penalty_events': {'silent_chest_without_referral': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1': {   'symptoms': [   'episodic shortness of breath',
                                                          'chest tightness',
                                                          'dry cough worse at night'],
                                          'vitals': {'temp': '36.8 C', 'bp': '115/75', 'hr': 95, 'spo2': '95%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.8 C (Afebrile)',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'infective_bronchitis',
                                                                                                        'pneumonia'],
                                                                                       'memory_note': 'Afebrile; '
                                                                                                      'infective '
                                                                                                      'bronchitis and '
                                                                                                      'pneumonia as '
                                                                                                      'primary cause '
                                                                                                      'less likely.'},
                                                              'skin_examination': {   'result': 'Mild eczematous '
                                                                                                'changes on forearm; '
                                                                                                'no rash',
                                                                                      'info_gain': 0.2,
                                                                                      'suggests': [   'asthma',
                                                                                                      'atopic_disease'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Eczematous skin '
                                                                                                     'changes; atopic '
                                                                                                     'triad '
                                                                                                     '(asthma/eczema/rhinitis) '
                                                                                                     'noted — supports '
                                                                                                     'allergic asthma '
                                                                                                     'diagnosis.'},
                                                              'bp_measurement': {   'result': '115/75 mmHg (Normal)',
                                                                                    'info_gain': 0.0,
                                                                                    'suggests': [],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'BP normal; '
                                                                                                   'cardiovascular '
                                                                                                   'cause of '
                                                                                                   'breathlessness '
                                                                                                   'unlikely.'},
                                                              'chest_auscultation': {   'result': 'Bilateral '
                                                                                                  'widespread '
                                                                                                  'polyphonic wheeze '
                                                                                                  'on expiration',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': ['asthma'],
                                                                                        'rules_out': [   'copd',
                                                                                                         'cardiac_failure'],
                                                                                        'memory_note': 'Polyphonic '
                                                                                                       'expiratory '
                                                                                                       'wheeze '
                                                                                                       'bilaterally — '
                                                                                                       'bronchospasm '
                                                                                                       'confirmed; '
                                                                                                       'asthma '
                                                                                                       'diagnosis '
                                                                                                       'established. '
                                                                                                       'Initiate '
                                                                                                       'salbutamol '
                                                                                                       'inhaler.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 95%, PR 95 bpm',
                                                                                    'info_gain': 0.3,
                                                                                    'suggests': [   'asthma',
                                                                                                    'moderate_asthma'],
                                                                                    'rules_out': ['severe_attack'],
                                                                                    'memory_note': 'SpO2 95% with mild '
                                                                                                   'tachycardia; '
                                                                                                   'moderate asthma '
                                                                                                   'attack, not yet '
                                                                                                   'life-threatening.'}}},
                                 '2': {   'symptoms': [   'severe breathlessness',
                                                          'inability to complete sentences',
                                                          'use of accessory muscles to breathe',
                                                          'silent chest'],
                                          'vitals': {'temp': '36.9 C', 'bp': '125/85', 'hr': 120, 'spo2': '89%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.9 C (Afebrile)',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Persistently '
                                                                                                      'afebrile; no '
                                                                                                      'infective '
                                                                                                      'exacerbation '
                                                                                                      'trigger '
                                                                                                      'identified.'},
                                                              'skin_examination': {   'result': 'Eczema unchanged; '
                                                                                                'accessory muscle use '
                                                                                                'visible',
                                                                                      'info_gain': 0.2,
                                                                                      'suggests': ['asthma'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Atopic '
                                                                                                     'background '
                                                                                                     'unchanged; '
                                                                                                     'visible '
                                                                                                     'accessory muscle '
                                                                                                     'use confirms '
                                                                                                     'severe '
                                                                                                     'respiratory '
                                                                                                     'effort.'},
                                                              'bp_measurement': {   'result': '125/85 mmHg (Mildly '
                                                                                              'elevated)',
                                                                                    'info_gain': 0.05,
                                                                                    'suggests': [],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Mildly elevated '
                                                                                                   'BP; likely anxiety '
                                                                                                   'and respiratory '
                                                                                                   'distress response, '
                                                                                                   'non-diagnostic.'},
                                                              'chest_auscultation': {   'result': 'Decreased air entry '
                                                                                                  'globally; absent '
                                                                                                  'wheeze (silent '
                                                                                                  'chest — medical '
                                                                                                  'emergency)',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': [   'severe_asthma',
                                                                                                        'life_threatening_asthma'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'URGENT: Silent '
                                                                                                       'chest — absent '
                                                                                                       'wheeze '
                                                                                                       'indicates '
                                                                                                       'near-complete '
                                                                                                       'airway '
                                                                                                       'obstruction. '
                                                                                                       'Life-threatening '
                                                                                                       'asthma attack. '
                                                                                                       'Immediate '
                                                                                                       'referral '
                                                                                                       'mandatory.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 89%, PR 120 bpm',
                                                                                    'info_gain': 0.5,
                                                                                    'suggests': [   'severe_asthma',
                                                                                                    'respiratory_failure'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'URGENT: SpO2 '
                                                                                                   'fallen to 89% with '
                                                                                                   'escalating '
                                                                                                   'tachycardia — '
                                                                                                   'impending '
                                                                                                   'respiratory '
                                                                                                   'failure. Immediate '
                                                                                                   'oxygen and '
                                                                                                   'referral.'}}}}},
    {   'id': 'case_14',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 40, 'gender': 'male', 'location': 'Endemic district, UP'},
        'hidden_diagnosis': 'lymphatic_filariasis',
        'budget': 14,
        'test_costs': {   'thermometer_check': 1,
                          'bp_measurement': 1,
                          'urine_dipstick': 2,
                          'skin_examination': 1,
                          'blood_panel': 5},
        'relevant_tests': ['skin_examination', 'blood_panel'],
        'conclusive_test': 'skin_examination',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Filariae Control Programme)',
        'critical_window_days': 30,
        'penalty_events': {'missed_referral_for_dec_therapy': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1-30': {   'symptoms': [   'massive painless swelling of left leg',
                                                             'thickening of skin on leg',
                                                             'heaviness while walking'],
                                             'vitals': {'temp': '37.1 C', 'bp': '125/80', 'hr': 76, 'spo2': '99%'},
                                             'test_results': {   'thermometer_check': {   'result': '37.1 C (Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'cellulitis',
                                                                                                           'acute_infection'],
                                                                                          'memory_note': 'Afebrile; '
                                                                                                         'acute '
                                                                                                         'infective '
                                                                                                         'cellulitis '
                                                                                                         'excluded as '
                                                                                                         'sole cause '
                                                                                                         'of limb '
                                                                                                         'swelling.'},
                                                                 'bp_measurement': {   'result': '125/80 mmHg (Normal)',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'BP normal; '
                                                                                                      'cardiovascular '
                                                                                                      'cause of oedema '
                                                                                                      'less likely.'},
                                                                 'urine_dipstick': {   'result': 'Normal; Protein '
                                                                                                 'Negative, Glucose '
                                                                                                 'Negative',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'nephrotic_syndrome',
                                                                                                        'renal_disease'],
                                                                                       'memory_note': 'Urinalysis '
                                                                                                      'normal; renal '
                                                                                                      'causes of '
                                                                                                      'oedema such as '
                                                                                                      'nephrotic '
                                                                                                      'syndrome '
                                                                                                      'excluded.'},
                                                                 'skin_examination': {   'result': 'Non-pitting edema '
                                                                                                   'of left lower '
                                                                                                   'extremity, '
                                                                                                   'hyperkeratosis '
                                                                                                   '(elephantiasis)',
                                                                                         'info_gain': 1.0,
                                                                                         'suggests': [   'lymphatic_filariasis',
                                                                                                         'elephantiasis'],
                                                                                         'rules_out': [   'deep_vein_thrombosis',
                                                                                                          'cardiac_oedema'],
                                                                                         'memory_note': 'Non-pitting '
                                                                                                        'elephantiasis '
                                                                                                        'with '
                                                                                                        'hyperkeratosis '
                                                                                                        '— '
                                                                                                        'pathognomonic '
                                                                                                        'of advanced '
                                                                                                        'lymphatic '
                                                                                                        'filariasis. '
                                                                                                        'Refer for DEC '
                                                                                                        'therapy.'},
                                                                 'blood_panel': {   'result': 'Eosinophilia 12%, Hb '
                                                                                              '11.5 g/dL, WBC '
                                                                                              '7,800/mcL',
                                                                                    'info_gain': 0.4,
                                                                                    'suggests': [   'filariasis',
                                                                                                    'parasitic_infection'],
                                                                                    'rules_out': [   'bacterial_infection'],
                                                                                    'memory_note': 'Eosinophilia 12% '
                                                                                                   'supports '
                                                                                                   'helminthic/parasitic '
                                                                                                   'infection; '
                                                                                                   'consistent with '
                                                                                                   'lymphatic '
                                                                                                   'filariasis in '
                                                                                                   'endemic zone.'}}}}},
    {   'id': 'case_15',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 35, 'gender': 'male', 'location': 'Remote village, MP'},
        'hidden_diagnosis': 'leprosy',
        'budget': 12,
        'test_costs': {'thermometer_check': 1, 'urine_dipstick': 2, 'skin_examination': 1, 'blood_panel': 5},
        'relevant_tests': ['skin_examination'],
        'conclusive_test': 'skin_examination',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Leprosy Control Unit)',
        'critical_window_days': 45,
        'penalty_events': {'missed_mdt_initiation': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1-45': {   'symptoms': [   'light colored patches on back',
                                                             'loss of sensation over the patches',
                                                             'weakness in gripping objects',
                                                             'painless ulcers on feet'],
                                             'vitals': {'temp': '37.0 C', 'bp': '120/75', 'hr': 80, 'spo2': '99%'},
                                             'test_results': {   'thermometer_check': {   'result': '37.0 C (Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'acute_infection'],
                                                                                          'memory_note': 'Afebrile; '
                                                                                                         'acute '
                                                                                                         'febrile '
                                                                                                         'illness '
                                                                                                         'excluded. '
                                                                                                         'Chronic '
                                                                                                         'insidious '
                                                                                                         'onset '
                                                                                                         'confirmed.'},
                                                                 'urine_dipstick': {   'result': 'Normal; Glucose '
                                                                                                 'Negative, Protein '
                                                                                                 'Negative',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'renal_disease',
                                                                                                        'diabetes'],
                                                                                       'memory_note': 'Urinalysis '
                                                                                                      'normal; renal '
                                                                                                      'and diabetic '
                                                                                                      'neuropathy as '
                                                                                                      'alternative '
                                                                                                      'cause '
                                                                                                      'excluded.'},
                                                                 'skin_examination': {   'result': 'Multiple '
                                                                                                   'hypopigmented '
                                                                                                   'macules on trunk '
                                                                                                   'with complete '
                                                                                                   'anesthesia to '
                                                                                                   'touch and '
                                                                                                   'pinprick; '
                                                                                                   'thickened ulnar '
                                                                                                   'nerve palpated',
                                                                                         'info_gain': 1.0,
                                                                                         'suggests': [   'leprosy',
                                                                                                         'borderline_leprosy'],
                                                                                         'rules_out': [   'tinea_versicolor',
                                                                                                          'vitiligo'],
                                                                                         'memory_note': 'Hypopigmented '
                                                                                                        'anaesthetic '
                                                                                                        'macules with '
                                                                                                        'thickened '
                                                                                                        'peripheral '
                                                                                                        'nerve — '
                                                                                                        'pathognomonic '
                                                                                                        'triad of '
                                                                                                        'leprosy. MDT '
                                                                                                        'regimen and '
                                                                                                        'referral '
                                                                                                        'required.'},
                                                                 'blood_panel': {   'result': 'Mild eosinophilia 8%, '
                                                                                              'Hb 11.8 g/dL, WBC '
                                                                                              '6,500/mcL',
                                                                                    'info_gain': 0.1,
                                                                                    'suggests': [   'parasitic_or_granulomatous_infection'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Mild eosinophilia; '
                                                                                                   'non-specific for '
                                                                                                   'leprosy but '
                                                                                                   'consistent with '
                                                                                                   'chronic '
                                                                                                   'granulomatous '
                                                                                                   'infection.'}}}}},
    {   'id': 'case_16',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 50, 'gender': 'female', 'location': 'Rural West Bengal'},
        'hidden_diagnosis': 'cervical_cancer',
        'budget': 13,
        'test_costs': {   'thermometer_check': 1,
                          'bp_measurement': 1,
                          'urine_dipstick': 2,
                          'abdominal_exam': 1,
                          'hemoglobin_strip': 4},
        'relevant_tests': ['abdominal_exam', 'hemoglobin_strip'],
        'conclusive_test': 'abdominal_exam',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Gynaecological Oncology)',
        'critical_window_days': 14,
        'penalty_events': {'missed_malignancy_referral': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1-14': {   'symptoms': [   'irregular vaginal bleeding',
                                                             'foul-smelling vaginal discharge',
                                                             'pelvic pain',
                                                             'severe fatigue',
                                                             'weight loss'],
                                             'vitals': {'temp': '37.2 C', 'bp': '105/65', 'hr': 96, 'spo2': '98%'},
                                             'test_results': {   'thermometer_check': {   'result': '37.2 C (Low-grade '
                                                                                                    'fever)',
                                                                                          'info_gain': 0.05,
                                                                                          'suggests': [   'infection',
                                                                                                          'cancer_associated_fever'],
                                                                                          'rules_out': [],
                                                                                          'memory_note': 'Low-grade '
                                                                                                         'fever; may '
                                                                                                         'indicate '
                                                                                                         'associated '
                                                                                                         'pelvic '
                                                                                                         'infection or '
                                                                                                         'tumour '
                                                                                                         'necrosis.'},
                                                                 'bp_measurement': {   'result': '105/65 mmHg (Low)',
                                                                                       'info_gain': 0.1,
                                                                                       'suggests': [   'anaemia',
                                                                                                       'haemorrhage'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Low BP '
                                                                                                      'consistent with '
                                                                                                      'significant '
                                                                                                      'blood loss from '
                                                                                                      'chronic vaginal '
                                                                                                      'bleeding.'},
                                                                 'urine_dipstick': {   'result': 'Blood Trace, Protein '
                                                                                                 'Trace',
                                                                                       'info_gain': 0.2,
                                                                                       'suggests': [   'cervical_cancer',
                                                                                                       'bladder_involvement'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Trace '
                                                                                                      'haematuria may '
                                                                                                      'indicate tumour '
                                                                                                      'invasion to '
                                                                                                      'bladder — '
                                                                                                      'cervical cancer '
                                                                                                      'local extension '
                                                                                                      'suspected.'},
                                                                 'abdominal_exam': {   'result': 'Hard, fixed, '
                                                                                                 'irregular suprapubic '
                                                                                                 'mass palpated',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': [   'cervical_cancer',
                                                                                                       'pelvic_malignancy'],
                                                                                       'rules_out': [   'fibroid',
                                                                                                        'ovarian_cyst_benign'],
                                                                                       'memory_note': 'Hard, fixed, '
                                                                                                      'irregular '
                                                                                                      'suprapubic mass '
                                                                                                      '— highly '
                                                                                                      'suspicious for '
                                                                                                      'advanced pelvic '
                                                                                                      'malignancy. '
                                                                                                      'URGENT referral '
                                                                                                      'to '
                                                                                                      'gynaecological '
                                                                                                      'oncology.'},
                                                                 'hemoglobin_strip': {   'result': '8.5 g/dL '
                                                                                                   '(Significant '
                                                                                                   'Anaemia)',
                                                                                         'info_gain': 0.3,
                                                                                         'suggests': [   'anaemia_of_chronic_disease',
                                                                                                         'haemorrhagic_anaemia'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Haemoglobin '
                                                                                                        '8.5 g/dL; '
                                                                                                        'significant '
                                                                                                        'anaemia from '
                                                                                                        'chronic blood '
                                                                                                        'loss '
                                                                                                        'consistent '
                                                                                                        'with cervical '
                                                                                                        'malignancy.'}}}}},
    {   'id': 'case_17',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 58, 'gender': 'male', 'location': 'Farming community, Andhra Pradesh'},
        'hidden_diagnosis': 'chronic_kidney_disease',
        'budget': 16,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'bp_measurement': 1,
                          'pulse_oximeter': 2,
                          'urine_dipstick': 2,
                          'blood_panel': 5},
        'relevant_tests': ['bp_measurement', 'urine_dipstick', 'skin_examination'],
        'conclusive_test': 'urine_dipstick',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Nephrology)',
        'critical_window_days': 10,
        'penalty_events': {'uraemia_without_dialysis_referral': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1-5': {   'symptoms': [   'swelling in legs and face',
                                                            'fatigue',
                                                            'nausea',
                                                            'decreased urine output'],
                                            'vitals': {'temp': '36.8 C', 'bp': '165/100', 'hr': 85, 'spo2': '97%'},
                                            'test_results': {   'thermometer_check': {   'result': '36.8 C (Afebrile)',
                                                                                         'info_gain': 0.0,
                                                                                         'suggests': [],
                                                                                         'rules_out': ['infection'],
                                                                                         'memory_note': 'Afebrile; '
                                                                                                        'infective '
                                                                                                        'cause of '
                                                                                                        'oedema '
                                                                                                        'excluded.'},
                                                                'skin_examination': {   'result': 'Bilateral pitting '
                                                                                                  'edema up to knees, '
                                                                                                  'periorbital '
                                                                                                  'puffiness',
                                                                                        'info_gain': 0.4,
                                                                                        'suggests': [   'chronic_kidney_disease',
                                                                                                        'nephrotic_syndrome',
                                                                                                        'cardiac_failure'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'Bilateral '
                                                                                                       'pitting oedema '
                                                                                                       'with '
                                                                                                       'periorbital '
                                                                                                       'puffiness; '
                                                                                                       'nephrotic/renal '
                                                                                                       'syndrome '
                                                                                                       'pattern — CKD '
                                                                                                       'workup '
                                                                                                       'indicated.'},
                                                                'bp_measurement': {   'result': '165/100 mmHg',
                                                                                      'info_gain': 0.3,
                                                                                      'suggests': [   'chronic_kidney_disease',
                                                                                                      'renal_hypertension'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Hypertension '
                                                                                                     '165/100; renal '
                                                                                                     'hypertension '
                                                                                                     'pattern in '
                                                                                                     'context of '
                                                                                                     'oedema and '
                                                                                                     'proteinuria.'},
                                                                'pulse_oximeter': {   'result': 'SpO2 97%, PR 85 bpm',
                                                                                      'info_gain': 0.05,
                                                                                      'suggests': [],
                                                                                      'rules_out': [   'severe_cardiac_failure',
                                                                                                       'respiratory_failure'],
                                                                                      'memory_note': 'SpO2 97%; no '
                                                                                                     'significant '
                                                                                                     'respiratory '
                                                                                                     'compromise at '
                                                                                                     'this stage.'},
                                                                'urine_dipstick': {   'result': 'Protein +++, Blood '
                                                                                                'Trace',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'chronic_kidney_disease',
                                                                                                      'nephrotic_syndrome'],
                                                                                      'rules_out': [   'cardiac_oedema',
                                                                                                       'hepatic_oedema'],
                                                                                      'memory_note': 'Massive '
                                                                                                     'proteinuria '
                                                                                                     '(Protein +++) — '
                                                                                                     'renal origin of '
                                                                                                     'oedema '
                                                                                                     'confirmed. CKD '
                                                                                                     'likely. '
                                                                                                     'Immediate '
                                                                                                     'referral to '
                                                                                                     'District '
                                                                                                     'Hospital '
                                                                                                     'required.'},
                                                                'blood_panel': {   'result': 'Hb 9.5 g/dL, WBC '
                                                                                             '6,200/mcL, elevated '
                                                                                             'creatinine (clinical '
                                                                                             'estimate)',
                                                                                   'info_gain': 0.4,
                                                                                   'suggests': [   'chronic_kidney_disease',
                                                                                                   'renal_anaemia'],
                                                                                   'rules_out': [],
                                                                                   'memory_note': 'Normocytic anaemia '
                                                                                                  'consistent with '
                                                                                                  'CKD-associated '
                                                                                                  'erythropoietin '
                                                                                                  'deficiency; renal '
                                                                                                  'origin '
                                                                                                  'confirmed.'}}},
                                 '6-10': {   'symptoms': [   'severe shortness of breath (fluid overload)',
                                                             'vomiting',
                                                             'confusion (uremia)',
                                                             'muscle twitches'],
                                             'vitals': {'temp': '36.5 C', 'bp': '180/110', 'hr': 95, 'spo2': '92%'},
                                             'test_results': {   'thermometer_check': {   'result': '36.5 C '
                                                                                                    '(Subnormal)',
                                                                                          'info_gain': 0.05,
                                                                                          'suggests': [],
                                                                                          'rules_out': [],
                                                                                          'memory_note': 'Subnormal '
                                                                                                         'temperature; '
                                                                                                         'uraemia '
                                                                                                         'causing '
                                                                                                         'temperature '
                                                                                                         'dysregulation '
                                                                                                         '— worsening '
                                                                                                         'CKD '
                                                                                                         'progression.'},
                                                                 'skin_examination': {   'result': 'Massive anasarca '
                                                                                                   '(generalised '
                                                                                                   'edema), uremic '
                                                                                                   'frost visible',
                                                                                         'info_gain': 0.6,
                                                                                         'suggests': [   'end_stage_renal_disease',
                                                                                                         'uraemia'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'URGENT: '
                                                                                                        'Uremic frost '
                                                                                                        'and anasarca '
                                                                                                        '— end-stage '
                                                                                                        'renal '
                                                                                                        'failure. '
                                                                                                        'Immediate '
                                                                                                        'dialysis-capable '
                                                                                                        'referral '
                                                                                                        'mandatory.'},
                                                                 'bp_measurement': {   'result': '180/110 mmHg '
                                                                                                 '(Hypertensive '
                                                                                                 'Emergency)',
                                                                                       'info_gain': 0.4,
                                                                                       'suggests': [   'hypertensive_emergency',
                                                                                                       'ckd_progression'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'URGENT: '
                                                                                                      'Escalating BP '
                                                                                                      'to 180/110 — '
                                                                                                      'hypertensive '
                                                                                                      'emergency from '
                                                                                                      'worsening CKD. '
                                                                                                      'Risk of '
                                                                                                      'hypertensive '
                                                                                                      'encephalopathy.'},
                                                                 'pulse_oximeter': {   'result': 'SpO2 92%, PR 95 bpm',
                                                                                       'info_gain': 0.3,
                                                                                       'suggests': [   'fluid_overload',
                                                                                                       'pulmonary_oedema'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Worsening SpO2 '
                                                                                                      '92%; pulmonary '
                                                                                                      'oedema from '
                                                                                                      'fluid overload '
                                                                                                      'escalating — '
                                                                                                      'respiratory '
                                                                                                      'compromise now '
                                                                                                      'present.'},
                                                                 'urine_dipstick': {   'result': 'Protein +++, Blood '
                                                                                                 'Trace (unchanged)',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': [   'chronic_kidney_disease'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'URGENT: '
                                                                                                      'Persistent '
                                                                                                      'massive '
                                                                                                      'proteinuria — '
                                                                                                      'established CKD '
                                                                                                      'with end-organ '
                                                                                                      'failure '
                                                                                                      'escalating. '
                                                                                                      'Dialysis '
                                                                                                      'referral '
                                                                                                      'critical.'},
                                                                 'blood_panel': {   'result': 'Hb 7.8 g/dL, markedly '
                                                                                              'elevated creatinine, '
                                                                                              'raised potassium '
                                                                                              '(clinical)',
                                                                                    'info_gain': 0.5,
                                                                                    'suggests': [   'end_stage_renal_disease',
                                                                                                    'hyperkalaemia_risk'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'URGENT: Worsening '
                                                                                                   'anaemia with '
                                                                                                   'rising creatinine '
                                                                                                   'and potassium — '
                                                                                                   'life-threatening '
                                                                                                   'uraemia and '
                                                                                                   'hyperkalaemia '
                                                                                                   'risk.'}}}}},
    {   'id': 'case_18',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 28, 'gender': 'male', 'location': 'Endemic zone, Bihar'},
        'hidden_diagnosis': 'kala_azar',
        'budget': 17,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'urine_dipstick': 2,
                          'rapid_malaria_test': 3,
                          'abdominal_exam': 1,
                          'blood_panel': 5},
        'relevant_tests': ['abdominal_exam', 'blood_panel', 'skin_examination'],
        'conclusive_test': 'abdominal_exam',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Kala-Azar Elimination Programme)',
        'critical_window_days': 7,
        'penalty_events': {'missed_referral_for_amb_therapy': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1-7': {   'symptoms': [   'fever for 2 months',
                                                            'progressive extreme weight loss',
                                                            'massive swelling in abdomen',
                                                            'darkening of skin',
                                                            'bleeding gums'],
                                            'vitals': {'temp': '38.5 C', 'bp': '95/60', 'hr': 105, 'spo2': '98%'},
                                            'test_results': {   'thermometer_check': {   'result': '38.5 C (Prolonged '
                                                                                                   'fever over 2 '
                                                                                                   'months)',
                                                                                         'info_gain': 0.2,
                                                                                         'suggests': [   'kala_azar',
                                                                                                         'malaria',
                                                                                                         'typhoid'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Prolonged '
                                                                                                        'fever 38.5C '
                                                                                                        'over 2 '
                                                                                                        'months; '
                                                                                                        'chronic '
                                                                                                        'febrile '
                                                                                                        'illness '
                                                                                                        'requiring '
                                                                                                        'systematic '
                                                                                                        'evaluation.'},
                                                                'skin_examination': {   'result': 'Hyperpigmentation '
                                                                                                  'on hands, feet, '
                                                                                                  'abdomen, and face',
                                                                                        'info_gain': 0.5,
                                                                                        'suggests': [   'kala_azar',
                                                                                                        'visceral_leishmaniasis'],
                                                                                        'rules_out': ['malaria'],
                                                                                        'memory_note': 'Generalised '
                                                                                                       'hyperpigmentation '
                                                                                                       '(kala-azar = '
                                                                                                       'black fever); '
                                                                                                       'highly '
                                                                                                       'characteristic '
                                                                                                       'of visceral '
                                                                                                       'leishmaniasis '
                                                                                                       'in Bihar '
                                                                                                       'endemic zone.'},
                                                                'urine_dipstick': {   'result': 'Protein Trace, '
                                                                                                'Glucose Negative',
                                                                                      'info_gain': 0.05,
                                                                                      'suggests': [],
                                                                                      'rules_out': ['diabetes', 'uti'],
                                                                                      'memory_note': 'Trace '
                                                                                                     'proteinuria; '
                                                                                                     'minor renal '
                                                                                                     'irritation. No '
                                                                                                     'alternative '
                                                                                                     'diagnosis '
                                                                                                     'suggested.'},
                                                                'rapid_malaria_test': {   'result': 'Negative',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': ['malaria'],
                                                                                          'memory_note': 'Malaria '
                                                                                                         'excluded by '
                                                                                                         'RDT; '
                                                                                                         'prolonged '
                                                                                                         'fever with '
                                                                                                         'splenomegaly '
                                                                                                         'is '
                                                                                                         'non-malarial.'},
                                                                'abdominal_exam': {   'result': 'Massive splenomegaly '
                                                                                                'crossing umbilicus, '
                                                                                                'firm and non-tender. '
                                                                                                'Hepatomegaly present.',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'kala_azar',
                                                                                                      'visceral_leishmaniasis'],
                                                                                      'rules_out': [   'malaria',
                                                                                                       'typhoid',
                                                                                                       'lymphoma'],
                                                                                      'memory_note': 'Massive '
                                                                                                     'crossing-umbilicus '
                                                                                                     'splenomegaly — '
                                                                                                     'pathognomonic of '
                                                                                                     'kala-azar in '
                                                                                                     'Bihar endemic '
                                                                                                     'context. '
                                                                                                     'Immediate '
                                                                                                     'referral for '
                                                                                                     'rK39 test and '
                                                                                                     'AmBisome '
                                                                                                     'therapy.'},
                                                                'blood_panel': {   'result': 'Severe Pancytopenia: Hb '
                                                                                             '5.5 g/dL, WBC 1,500/mcL, '
                                                                                             'Platelets 45,000/mcL',
                                                                                   'info_gain': 0.5,
                                                                                   'suggests': [   'kala_azar',
                                                                                                   'visceral_leishmaniasis'],
                                                                                   'rules_out': ['dengue_alone'],
                                                                                   'memory_note': 'Severe pancytopenia '
                                                                                                  'with bone marrow '
                                                                                                  'suppression; '
                                                                                                  'strongly supports '
                                                                                                  'visceral '
                                                                                                  'leishmaniasis over '
                                                                                                  'other '
                                                                                                  'diagnoses.'}}}}},
    {   'id': 'case_19',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 2, 'gender': 'female', 'location': 'Tribal village, Odisha'},
        'hidden_diagnosis': 'severe_pneumonia_under_5',
        'budget': 9,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'bp_measurement': 1,
                          'chest_auscultation': 1,
                          'pulse_oximeter': 2},
        'relevant_tests': ['pulse_oximeter', 'chest_auscultation', 'thermometer_check'],
        'conclusive_test': 'pulse_oximeter',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Paediatric Ward)',
        'critical_window_days': 1,
        'penalty_events': {'hypoxia_without_referral_child': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1': {   'symptoms': [   'high fever',
                                                          'fast breathing',
                                                          'lower chest wall indrawing',
                                                          'inability to drink',
                                                          'grunting'],
                                          'vitals': {'temp': '39.4 C', 'bp': '90/60', 'hr': 150, 'spo2': '89%'},
                                          'test_results': {   'thermometer_check': {   'result': '39.4 C (High fever)',
                                                                                       'info_gain': 0.2,
                                                                                       'suggests': [   'pneumonia',
                                                                                                       'malaria',
                                                                                                       'sepsis'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'High fever '
                                                                                                      '39.4C in a '
                                                                                                      '2-year-old; '
                                                                                                      'serious '
                                                                                                      'bacterial '
                                                                                                      'infection and '
                                                                                                      'pneumonia in '
                                                                                                      'differential.'},
                                                              'skin_examination': {   'result': 'Central cyanosis of '
                                                                                                'lips; intercostal '
                                                                                                'retractions visible',
                                                                                      'info_gain': 0.4,
                                                                                      'suggests': [   'severe_pneumonia',
                                                                                                      'respiratory_failure'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Central cyanosis '
                                                                                                     'and chest '
                                                                                                     'retractions — '
                                                                                                     'severe '
                                                                                                     'respiratory '
                                                                                                     'distress in a '
                                                                                                     'child. Pneumonia '
                                                                                                     'with hypoxia '
                                                                                                     'highly likely.'},
                                                              'bp_measurement': {   'result': '90/60 mmHg (Low for '
                                                                                              'age)',
                                                                                    'info_gain': 0.2,
                                                                                    'suggests': [   'sepsis',
                                                                                                    'severe_illness'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Low BP for age; '
                                                                                                   'haemodynamic '
                                                                                                   'compromise '
                                                                                                   'consistent with '
                                                                                                   'severe pneumonia '
                                                                                                   'or sepsis.'},
                                                              'chest_auscultation': {   'result': 'Bronchial breath '
                                                                                                  'sounds and '
                                                                                                  'crepitations over '
                                                                                                  'right mid and lower '
                                                                                                  'zones',
                                                                                        'info_gain': 0.5,
                                                                                        'suggests': [   'pneumonia',
                                                                                                        'severe_pneumonia'],
                                                                                        'rules_out': [   'asthma',
                                                                                                         'bronchiolitis'],
                                                                                        'memory_note': 'Right-sided '
                                                                                                       'bronchial '
                                                                                                       'breathing with '
                                                                                                       'crepitations; '
                                                                                                       'lobar '
                                                                                                       'consolidation '
                                                                                                       'consistent '
                                                                                                       'with bacterial '
                                                                                                       'pneumonia '
                                                                                                       'confirmed.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 89%, PR 150 bpm',
                                                                                    'info_gain': 1.0,
                                                                                    'suggests': [   'severe_pneumonia',
                                                                                                    'hypoxia'],
                                                                                    'rules_out': ['mild_rti'],
                                                                                    'memory_note': 'SpO2 89% in a '
                                                                                                   'child — WHO severe '
                                                                                                   'pneumonia criteria '
                                                                                                   'met. URGENT '
                                                                                                   'referral for '
                                                                                                   'oxygen and IV '
                                                                                                   'antibiotics. '
                                                                                                   'Life-threatening.'}}}}},
    {   'id': 'case_20',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 7, 'gender': 'male', 'location': 'Rural UP'},
        'hidden_diagnosis': 'intestinal_worms',
        'budget': 12,
        'test_costs': {   'thermometer_check': 1,
                          'urine_dipstick': 2,
                          'skin_examination': 1,
                          'abdominal_exam': 1,
                          'hemoglobin_strip': 4},
        'relevant_tests': ['abdominal_exam', 'hemoglobin_strip'],
        'conclusive_test': 'hemoglobin_strip',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 14,
        'penalty_events': {'untreated_worm_burden_anaemia': -1.0, 'budget_exhausted': -0.5, 'duplicate_test': -0.2},
        'daily_progression': {   '1-14': {   'symptoms': [   'vague abdominal pain',
                                                             'poor appetite',
                                                             "passing 'long white worms' in stool",
                                                             'fatigue',
                                                             'teeth grinding at night'],
                                             'vitals': {'temp': '37.0 C', 'bp': '100/65', 'hr': 88, 'spo2': '99%'},
                                             'test_results': {   'thermometer_check': {   'result': '37.0 C (Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'malaria',
                                                                                                           'infection'],
                                                                                          'memory_note': 'Afebrile; '
                                                                                                         'febrile '
                                                                                                         'illness '
                                                                                                         'excluded. '
                                                                                                         'Helminthic '
                                                                                                         'infestation '
                                                                                                         'is typically '
                                                                                                         'non-pyrexial.'},
                                                                 'urine_dipstick': {   'result': 'Normal; Glucose '
                                                                                                 'Negative, Protein '
                                                                                                 'Negative',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'uti',
                                                                                                        'diabetes',
                                                                                                        'renal_disease'],
                                                                                       'memory_note': 'Urinalysis '
                                                                                                      'normal; UTI and '
                                                                                                      'renal causes '
                                                                                                      'excluded.'},
                                                                 'skin_examination': {   'result': 'Mild pallor in '
                                                                                                   'conjunctiva; no '
                                                                                                   'rash; no oedema',
                                                                                         'info_gain': 0.2,
                                                                                         'suggests': [   'nutritional_anemia',
                                                                                                         'intestinal_worms'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Mild '
                                                                                                        'conjunctival '
                                                                                                        'pallor; '
                                                                                                        'anaemia from '
                                                                                                        'worm-related '
                                                                                                        'malabsorption '
                                                                                                        'and blood '
                                                                                                        'loss likely.'},
                                                                 'abdominal_exam': {   'result': 'Soft, non-tender, '
                                                                                                 'slight distension',
                                                                                       'info_gain': 0.3,
                                                                                       'suggests': [   'intestinal_worms',
                                                                                                       'malnutrition'],
                                                                                       'rules_out': [   'appendicitis',
                                                                                                        'organomegaly'],
                                                                                       'memory_note': 'Mild abdominal '
                                                                                                      'distension '
                                                                                                      'without '
                                                                                                      'tenderness; '
                                                                                                      'consistent with '
                                                                                                      'intestinal '
                                                                                                      'helminthiasis. '
                                                                                                      'No acute '
                                                                                                      'abdomen.'},
                                                                 'hemoglobin_strip': {   'result': '9.5 g/dL (Moderate '
                                                                                                   'Anaemia)',
                                                                                         'info_gain': 1.0,
                                                                                         'suggests': [   'intestinal_worms',
                                                                                                         'nutritional_deficiency'],
                                                                                         'rules_out': [   'normal_hemoglobin'],
                                                                                         'memory_note': 'Hb 9.5 g/dL — '
                                                                                                        'moderate '
                                                                                                        'anaemia in a '
                                                                                                        'school-age '
                                                                                                        'child with '
                                                                                                        'visible worms '
                                                                                                        'in stool. '
                                                                                                        'Helminthiasis '
                                                                                                        'confirmed. '
                                                                                                        'Administer '
                                                                                                        'albendazole '
                                                                                                        'and iron '
                                                                                                        'supplementation.'}}}}},
    {   'id': 'case_01_var1',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 28, 'gender': 'male', 'location': 'Desert community, Rajasthan'},
        'hidden_diagnosis': 'tuberculosis',
        'budget': 21,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'chest_auscultation': 1,
                          'pulse_oximeter': 3,
                          'rapid_malaria_test': 3,
                          'blood_panel': 5,
                          'sputum_smear': 5},
        'relevant_tests': ['thermometer_check', 'chest_auscultation', 'sputum_smear'],
        'conclusive_test': 'sputum_smear',
        'requires_referral': True,
        'referral_destination': 'District Hospital (DOTS Centre)',
        'critical_window_days': 14,
        'penalty_events': {'hemoptysis_without_referral': -0.95, 'budget_exhausted': -0.59, 'duplicate_test': -0.17},
        'daily_progression': {   '1-7': {   'symptoms': [   'Patient reports night sweats',
                                                            'Patient reports weight loss',
                                                            'Patient reports chronic cough for 3 weeks',
                                                            'Patient reports low-grade evening fever'],
                                            'vitals': {'temp': '38.0 C', 'bp': '110/72', 'hr': 90, 'spo2': '97%'},
                                            'test_results': {   'thermometer_check': {   'result': 'Recorded: 37.9 C '
                                                                                                   '(slight evening '
                                                                                                   'elevated temp)',
                                                                                         'info_gain': 0.1,
                                                                                         'suggests': [   'tuberculosis',
                                                                                                         'chronic_infection',
                                                                                                         'kala_azar'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'slight '
                                                                                                        'evening '
                                                                                                        'elevated temp '
                                                                                                        '37.9C; '
                                                                                                        'consistent '
                                                                                                        'with TB '
                                                                                                        'chronicity '
                                                                                                        'but seen in '
                                                                                                        'many '
                                                                                                        'conditions — '
                                                                                                        'non-specific '
                                                                                                        'alone.'},
                                                                'chest_auscultation': {   'result': 'Rales in the '
                                                                                                    'apical region of '
                                                                                                    'right lung',
                                                                                          'info_gain': 0.41,
                                                                                          'suggests': [   'tuberculosis',
                                                                                                          'pneumonia'],
                                                                                          'rules_out': [   'asthma',
                                                                                                           'copd'],
                                                                                          'memory_note': 'Apical '
                                                                                                         'alveolar '
                                                                                                         'sounds '
                                                                                                         'localised to '
                                                                                                         'right apex; '
                                                                                                         'strongly '
                                                                                                         'suspicious '
                                                                                                         'for '
                                                                                                         'pulmonary TB '
                                                                                                         '— sputum '
                                                                                                         'smear '
                                                                                                         'urgently '
                                                                                                         'indicated.'},
                                                                'sputum_smear': {   'result': 'Reactive for Acid-Fast '
                                                                                              'Bacilli (AFB)',
                                                                                    'info_gain': 1.0,
                                                                                    'suggests': ['tuberculosis'],
                                                                                    'rules_out': [   'pneumonia',
                                                                                                     'copd_exacerbation',
                                                                                                     'lung_cancer'],
                                                                                    'memory_note': 'Status: '
                                                                                                   'AFB-positive '
                                                                                                   'sputum smear; '
                                                                                                   'pulmonary '
                                                                                                   'tuberculosis '
                                                                                                   'established — '
                                                                                                   'initiate DOTS '
                                                                                                   'referral '
                                                                                                   'immediately.'},
                                                                'pulse_oximeter': {   'result': 'SpO2 96%, PR 88 bpm',
                                                                                      'info_gain': 0.11,
                                                                                      'suggests': [],
                                                                                      'rules_out': [   'severe_respiratory_failure'],
                                                                                      'memory_note': 'Recorded: SpO2 '
                                                                                                     '96%; '
                                                                                                     'low-intensity '
                                                                                                     'reduced '
                                                                                                     'oxygenation '
                                                                                                     'present, no '
                                                                                                     'acute '
                                                                                                     'respiratory '
                                                                                                     'failure at this '
                                                                                                     'stage.'},
                                                                'blood_panel': {   'result': 'Hb 10.8 g/dL, ESR 78 '
                                                                                             'mm/hr, WBC 7,200/mcL',
                                                                                   'info_gain': 0.22,
                                                                                   'suggests': [   'tuberculosis',
                                                                                                   'chronic_infection'],
                                                                                   'rules_out': [],
                                                                                   'memory_note': 'Minor anaemia with '
                                                                                                  'markedly raised ESR '
                                                                                                  '(78 mm/hr); '
                                                                                                  'supports '
                                                                                                  'long-standing '
                                                                                                  'granulomatous '
                                                                                                  'infectious process '
                                                                                                  'consistent with '
                                                                                                  'TB.'},
                                                                'rapid_malaria_test': {   'result': 'Negative',
                                                                                          'info_gain': 0.03,
                                                                                          'suggests': [],
                                                                                          'rules_out': ['malaria'],
                                                                                          'memory_note': 'Malaria '
                                                                                                         'excluded by '
                                                                                                         'RDT; '
                                                                                                         'elevated '
                                                                                                         'temp with '
                                                                                                         'night sweats '
                                                                                                         'not '
                                                                                                         'attributable '
                                                                                                         'to malarial '
                                                                                                         'pathogen '
                                                                                                         'presence.'},
                                                                'skin_examination': {   'result': 'Slight wasting '
                                                                                                  'noted; no rash; no '
                                                                                                  'pallor',
                                                                                        'info_gain': 0.15,
                                                                                        'suggests': ['tuberculosis'],
                                                                                        'rules_out': [   'dengue',
                                                                                                         'kala_azar'],
                                                                                        'memory_note': 'Finding: '
                                                                                                       'Slight '
                                                                                                       'cachexia '
                                                                                                       'consistent '
                                                                                                       'with chronic '
                                                                                                       'TB illness; no '
                                                                                                       'cutaneous '
                                                                                                       'finding '
                                                                                                       'suggesting '
                                                                                                       'alternative '
                                                                                                       'assessment.'}}},
                                 '8-14': {   'symptoms': [   'Patient reports severe night sweats',
                                                             'Patient reports chronic cough for 4 weeks',
                                                             'Patient reports blood-tinged sputum (hemoptysis)',
                                                             'Patient reports visible weight loss'],
                                             'vitals': {'temp': '38.1 C', 'bp': '100/71', 'hr': 101, 'spo2': '95%'},
                                             'test_results': {   'thermometer_check': {   'result': '38.2 C '
                                                                                                    '(Escalating '
                                                                                                    'elevated temp)',
                                                                                          'info_gain': 0.24,
                                                                                          'suggests': [   'tuberculosis',
                                                                                                          'tb_progression'],
                                                                                          'rules_out': [],
                                                                                          'memory_note': 'Escalating '
                                                                                                         'evening '
                                                                                                         'pyrexia to '
                                                                                                         '38.2C; '
                                                                                                         'escalating '
                                                                                                         'TB systemic '
                                                                                                         'involvement '
                                                                                                         'alongside '
                                                                                                         'onset of '
                                                                                                         'hemoptysis.'},
                                                                 'chest_auscultation': {   'result': 'Provider note: '
                                                                                                     'Escalating '
                                                                                                     'alveolar sounds '
                                                                                                     'and reduced '
                                                                                                     'breath sounds '
                                                                                                     'right apex',
                                                                                           'info_gain': 0.47,
                                                                                           'suggests': [   'tuberculosis',
                                                                                                           'tb_cavitation'],
                                                                                           'rules_out': ['asthma'],
                                                                                           'memory_note': 'URGENT: '
                                                                                                          'Progressive '
                                                                                                          'lung apex '
                                                                                                          'consolidation '
                                                                                                          'with '
                                                                                                          'reduced '
                                                                                                          'breath '
                                                                                                          'sounds — '
                                                                                                          'cavitation '
                                                                                                          'advancing, '
                                                                                                          'parenchymal '
                                                                                                          'destruction '
                                                                                                          'escalating.'},
                                                                 'sputum_smear': {   'result': 'Status: Confirmed '
                                                                                               'Presence Of for '
                                                                                               'Acid-Fast Bacilli '
                                                                                               '(AFB) — heavy '
                                                                                               'bacillary load',
                                                                                     'info_gain': 1.0,
                                                                                     'suggests': ['tuberculosis'],
                                                                                     'rules_out': [   'pneumonia',
                                                                                                      'copd_exacerbation'],
                                                                                     'memory_note': 'URGENT: '
                                                                                                    'Persistently '
                                                                                                    'AFB-positive with '
                                                                                                    'escalating '
                                                                                                    'bacillary load '
                                                                                                    'and hemoptysis — '
                                                                                                    'active TB, '
                                                                                                    'immediate DOTS '
                                                                                                    'referral '
                                                                                                    'required.'},
                                                                 'pulse_oximeter': {   'result': 'Status: SpO2 94%, PR '
                                                                                                 '95 bpm',
                                                                                       'info_gain': 0.23,
                                                                                       'suggests': [   'tuberculosis_progression'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Provider note: '
                                                                                                      'Worsening SpO2 '
                                                                                                      'to 94%; '
                                                                                                      'escalating '
                                                                                                      'respiratory '
                                                                                                      'compromise — '
                                                                                                      'referral to '
                                                                                                      'District '
                                                                                                      'Hospital now '
                                                                                                      'time-sensitive.'},
                                                                 'blood_panel': {   'result': 'Finding: Hb 9.6 g/dL, '
                                                                                              'ESR 102 mm/hr, WBC '
                                                                                              '8,100/mcL',
                                                                                    'info_gain': 0.35,
                                                                                    'suggests': [   'tuberculosis',
                                                                                                    'tb_progression'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Deteriorating '
                                                                                                   'anaemia and '
                                                                                                   'markedly elevated '
                                                                                                   'ESR (102 mm/hr); '
                                                                                                   'confirms active '
                                                                                                   'escalating TB with '
                                                                                                   'rising systemic '
                                                                                                   'inflammatory '
                                                                                                   'burden.'},
                                                                 'rapid_malaria_test': {   'result': 'Not Detected',
                                                                                           'info_gain': 0.09,
                                                                                           'suggests': [],
                                                                                           'rules_out': ['malaria'],
                                                                                           'memory_note': 'Finding: '
                                                                                                          'Malaria '
                                                                                                          'definitively '
                                                                                                          'removed '
                                                                                                          'from '
                                                                                                          'consideration; '
                                                                                                          'clinical '
                                                                                                          'picture '
                                                                                                          'entirely '
                                                                                                          'explained '
                                                                                                          'by '
                                                                                                          'confirmed '
                                                                                                          'escalating '
                                                                                                          'pulmonary '
                                                                                                          'TB.'},
                                                                 'skin_examination': {   'result': 'Progressive '
                                                                                                   'wasting and pallor '
                                                                                                   'now visible; no '
                                                                                                   'rash',
                                                                                         'info_gain': 0.25,
                                                                                         'suggests': ['tuberculosis'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Worsening '
                                                                                                        'pallor and '
                                                                                                        'visible '
                                                                                                        'cachexia; '
                                                                                                        'escalating '
                                                                                                        'TB-related '
                                                                                                        'wasting and '
                                                                                                        'anaemia now '
                                                                                                        'clinically '
                                                                                                        'apparent.'}}}}},
    {   'id': 'case_01_var2',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 41, 'gender': 'female', 'location': 'Tea estate, Assam'},
        'hidden_diagnosis': 'tuberculosis',
        'budget': 20,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'chest_auscultation': 1,
                          'pulse_oximeter': 1,
                          'rapid_malaria_test': 2,
                          'blood_panel': 5,
                          'sputum_smear': 7},
        'relevant_tests': ['thermometer_check', 'chest_auscultation', 'sputum_smear'],
        'conclusive_test': 'sputum_smear',
        'requires_referral': True,
        'referral_destination': 'District Hospital (DOTS Centre)',
        'critical_window_days': 14,
        'penalty_events': {'hemoptysis_without_referral': -1.09, 'budget_exhausted': -0.59, 'duplicate_test': -0.21},
        'daily_progression': {   '1-7': {   'symptoms': [   'chronic cough for 3 weeks',
                                                            'low-grade evening fever',
                                                            'weight loss',
                                                            'night sweats'],
                                            'vitals': {'temp': '37.9 C', 'bp': '107/78', 'hr': 84, 'spo2': '94%'},
                                            'test_results': {   'thermometer_check': {   'result': '37.9 C (Low-grade '
                                                                                                   'evening fever)',
                                                                                         'info_gain': 0.06,
                                                                                         'suggests': [   'tuberculosis',
                                                                                                         'chronic_infection',
                                                                                                         'kala_azar'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'mild evening '
                                                                                                        'fever 37.9C; '
                                                                                                        'consistent '
                                                                                                        'with TB '
                                                                                                        'chronicity '
                                                                                                        'but seen in '
                                                                                                        'many '
                                                                                                        'conditions — '
                                                                                                        'non-specific '
                                                                                                        'alone.'},
                                                                'chest_auscultation': {   'result': 'Alveolar Sounds '
                                                                                                    'in the upper lobe '
                                                                                                    'region of right '
                                                                                                    'lung',
                                                                                          'info_gain': 0.42,
                                                                                          'suggests': [   'tuberculosis',
                                                                                                          'pneumonia'],
                                                                                          'rules_out': [   'asthma',
                                                                                                           'copd'],
                                                                                          'memory_note': 'Lung Apex '
                                                                                                         'crackles '
                                                                                                         'localised to '
                                                                                                         'right apex; '
                                                                                                         'strongly '
                                                                                                         'suspicious '
                                                                                                         'for '
                                                                                                         'pulmonary TB '
                                                                                                         '— sputum '
                                                                                                         'smear '
                                                                                                         'urgently '
                                                                                                         'indicated.'},
                                                                'sputum_smear': {   'result': 'Positive for Acid-Fast '
                                                                                              'Bacilli (AFB)',
                                                                                    'info_gain': 1.0,
                                                                                    'suggests': ['tuberculosis'],
                                                                                    'rules_out': [   'pneumonia',
                                                                                                     'copd_exacerbation',
                                                                                                     'lung_cancer'],
                                                                                    'memory_note': 'AFB-positive '
                                                                                                   'sputum smear; '
                                                                                                   'pulmonary '
                                                                                                   'tuberculosis '
                                                                                                   'diagnostically '
                                                                                                   'verified — '
                                                                                                   'initiate DOTS '
                                                                                                   'referral '
                                                                                                   'immediately.'},
                                                                'pulse_oximeter': {   'result': 'SpO2 96%, PR 88 bpm',
                                                                                      'info_gain': 0.07,
                                                                                      'suggests': [],
                                                                                      'rules_out': [   'severe_respiratory_failure'],
                                                                                      'memory_note': 'SpO2 96%; '
                                                                                                     'low-intensity '
                                                                                                     'low SpO2 '
                                                                                                     'present, no '
                                                                                                     'acute '
                                                                                                     'respiratory '
                                                                                                     'failure at this '
                                                                                                     'stage.'},
                                                                'blood_panel': {   'result': 'Hb 10.8 g/dL, ESR 78 '
                                                                                             'mm/hr, WBC 7,200/mcL',
                                                                                   'info_gain': 0.18,
                                                                                   'suggests': [   'tuberculosis',
                                                                                                   'chronic_infection'],
                                                                                   'rules_out': [],
                                                                                   'memory_note': 'Slight anaemia with '
                                                                                                  'markedly raised ESR '
                                                                                                  '(78 mm/hr); '
                                                                                                  'supports prolonged '
                                                                                                  'granulomatous '
                                                                                                  'infectious process '
                                                                                                  'consistent with '
                                                                                                  'TB.'},
                                                                'rapid_malaria_test': {   'result': 'Not Detected',
                                                                                          'info_gain': 0.04,
                                                                                          'suggests': [],
                                                                                          'rules_out': ['malaria'],
                                                                                          'memory_note': 'Malaria '
                                                                                                         'eliminated '
                                                                                                         'by RDT; '
                                                                                                         'elevated '
                                                                                                         'temp with '
                                                                                                         'night sweats '
                                                                                                         'not '
                                                                                                         'attributable '
                                                                                                         'to malarial '
                                                                                                         'pathogen '
                                                                                                         'presence.'},
                                                                'skin_examination': {   'result': 'Minor wasting '
                                                                                                  'noted; no rash; no '
                                                                                                  'pallor',
                                                                                        'info_gain': 0.12,
                                                                                        'suggests': ['tuberculosis'],
                                                                                        'rules_out': [   'dengue',
                                                                                                         'kala_azar'],
                                                                                        'memory_note': 'Mild cachexia '
                                                                                                       'consistent '
                                                                                                       'with '
                                                                                                       'persistent TB '
                                                                                                       'illness; no '
                                                                                                       'cutaneous '
                                                                                                       'finding '
                                                                                                       'suggesting '
                                                                                                       'alternative '
                                                                                                       'diagnosis.'}}},
                                 '8-14': {   'symptoms': [   'Patient reports chronic cough for 4 weeks',
                                                             'Patient reports severe night sweats',
                                                             'Patient reports blood-tinged sputum (hemoptysis)',
                                                             'Patient reports visible weight loss'],
                                             'vitals': {'temp': '38.2 C', 'bp': '107/73', 'hr': 91, 'spo2': '93%'},
                                             'test_results': {   'thermometer_check': {   'result': '38.2 C '
                                                                                                    '(Escalating '
                                                                                                    'elevated temp)',
                                                                                          'info_gain': 0.14,
                                                                                          'suggests': [   'tuberculosis',
                                                                                                          'tb_progression'],
                                                                                          'rules_out': [],
                                                                                          'memory_note': 'Escalating '
                                                                                                         'evening '
                                                                                                         'elevated '
                                                                                                         'temp to '
                                                                                                         '38.2C; '
                                                                                                         'worsening TB '
                                                                                                         'systemic '
                                                                                                         'involvement '
                                                                                                         'alongside '
                                                                                                         'onset of '
                                                                                                         'hemoptysis.'},
                                                                 'chest_auscultation': {   'result': 'Progressing '
                                                                                                     'crepitations and '
                                                                                                     'reduced breath '
                                                                                                     'sounds right '
                                                                                                     'apex',
                                                                                           'info_gain': 0.5,
                                                                                           'suggests': [   'tuberculosis',
                                                                                                           'tb_cavitation'],
                                                                                           'rules_out': ['asthma'],
                                                                                           'memory_note': 'URGENT: '
                                                                                                          'Progressive '
                                                                                                          'lung apex '
                                                                                                          'consolidation '
                                                                                                          'with '
                                                                                                          'reduced '
                                                                                                          'breath '
                                                                                                          'sounds — '
                                                                                                          'cavitation '
                                                                                                          'advancing, '
                                                                                                          'parenchymal '
                                                                                                          'destruction '
                                                                                                          'progressing.'},
                                                                 'sputum_smear': {   'result': 'Positive for Acid-Fast '
                                                                                               'Bacilli (AFB) — heavy '
                                                                                               'bacillary load',
                                                                                     'info_gain': 1.0,
                                                                                     'suggests': ['tuberculosis'],
                                                                                     'rules_out': [   'pneumonia',
                                                                                                      'copd_exacerbation'],
                                                                                     'memory_note': 'URGENT: '
                                                                                                    'Persistently '
                                                                                                    'AFB-positive with '
                                                                                                    'escalating '
                                                                                                    'bacillary load '
                                                                                                    'and hemoptysis — '
                                                                                                    'active TB, '
                                                                                                    'immediate DOTS '
                                                                                                    'referral '
                                                                                                    'required.'},
                                                                 'pulse_oximeter': {   'result': 'SpO2 94%, PR 95 bpm',
                                                                                       'info_gain': 0.19,
                                                                                       'suggests': [   'tuberculosis_progression'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Worsening SpO2 '
                                                                                                      'to 94%; '
                                                                                                      'escalating '
                                                                                                      'respiratory '
                                                                                                      'compromise — '
                                                                                                      'referral to '
                                                                                                      'District '
                                                                                                      'Hospital now '
                                                                                                      'immediate '
                                                                                                      'action needed.'},
                                                                 'blood_panel': {   'result': 'Hb 9.6 g/dL, ESR 102 '
                                                                                              'mm/hr, WBC 8,100/mcL',
                                                                                    'info_gain': 0.27,
                                                                                    'suggests': [   'tuberculosis',
                                                                                                    'tb_progression'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Worsening anaemia '
                                                                                                   'and markedly '
                                                                                                   'elevated ESR (102 '
                                                                                                   'mm/hr); confirms '
                                                                                                   'active escalating '
                                                                                                   'TB with rising '
                                                                                                   'systemic '
                                                                                                   'inflammatory '
                                                                                                   'burden.'},
                                                                 'rapid_malaria_test': {   'result': 'Non-Reactive',
                                                                                           'info_gain': 0.19,
                                                                                           'suggests': [],
                                                                                           'rules_out': ['malaria'],
                                                                                           'memory_note': 'Malaria '
                                                                                                          'definitively '
                                                                                                          'removed '
                                                                                                          'from '
                                                                                                          'consideration; '
                                                                                                          'clinical '
                                                                                                          'picture '
                                                                                                          'entirely '
                                                                                                          'explained '
                                                                                                          'by '
                                                                                                          'confirmed '
                                                                                                          'escalating '
                                                                                                          'pulmonary '
                                                                                                          'TB.'},
                                                                 'skin_examination': {   'result': 'Progressive '
                                                                                                   'wasting and pallor '
                                                                                                   'now visible; no '
                                                                                                   'rash',
                                                                                         'info_gain': 0.26,
                                                                                         'suggests': ['tuberculosis'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Escalating '
                                                                                                        'pallor and '
                                                                                                        'visible '
                                                                                                        'cachexia; '
                                                                                                        'escalating '
                                                                                                        'TB-related '
                                                                                                        'wasting and '
                                                                                                        'anaemia now '
                                                                                                        'clinically '
                                                                                                        'apparent.'}}}}},
    {   'id': 'case_02_var1',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 57, 'gender': 'male', 'location': 'Remote hamlet, Odisha'},
        'hidden_diagnosis': 'type_2_diabetes',
        'budget': 13,
        'test_costs': {   'thermometer_check': 2,
                          'bp_measurement': 2,
                          'skin_examination': 2,
                          'urine_dipstick': 1,
                          'blood_glucose_strip': 4},
        'relevant_tests': ['blood_glucose_strip', 'urine_dipstick'],
        'conclusive_test': 'blood_glucose_strip',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 30,
        'penalty_events': {   'uncontrolled_hyperglycemia_missed': -1.09,
                              'budget_exhausted': -0.47,
                              'duplicate_test': -0.22},
        'daily_progression': {   '1-15': {   'symptoms': [   'Patient reports blurring of vision',
                                                             'Patient reports frequent urination at night',
                                                             'Patient reports excessive thirst'],
                                             'vitals': {'temp': '36.7 C', 'bp': '130/82', 'hr': 81, 'spo2': '99%'},
                                             'test_results': {   'thermometer_check': {   'result': '36.8 C (Afebrile)',
                                                                                          'info_gain': 0.04,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'malaria',
                                                                                                           'dengue',
                                                                                                           'infection'],
                                                                                          'memory_note': 'Status: '
                                                                                                         'Afebrile; '
                                                                                                         'acute '
                                                                                                         'febrile '
                                                                                                         'illness '
                                                                                                         'excluded as '
                                                                                                         'cause of '
                                                                                                         'polyuria and '
                                                                                                         'thirst.'},
                                                                 'bp_measurement': {   'result': 'Clinical '
                                                                                                 'observation: 130/85 '
                                                                                                 'mmHg (Stage 1 '
                                                                                                 'Hypertension)',
                                                                                       'info_gain': 0.19,
                                                                                       'suggests': [   'hypertension',
                                                                                                       'type_2_diabetes'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Borderline '
                                                                                                      'elevated BP; '
                                                                                                      'diabetic '
                                                                                                      'hypertension '
                                                                                                      'co-morbidity '
                                                                                                      'possible — '
                                                                                                      'vascular '
                                                                                                      'glucose '
                                                                                                      'confirmation '
                                                                                                      'required.'},
                                                                 'skin_examination': {   'result': 'Finding: Darkening '
                                                                                                   'at nape and axilla '
                                                                                                   '— possible '
                                                                                                   'acanthosis '
                                                                                                   'nigricans',
                                                                                         'info_gain': 0.25,
                                                                                         'suggests': [   'type_2_diabetes',
                                                                                                         'insulin_resistance'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Assessment '
                                                                                                        'notes: '
                                                                                                        'Suspicious '
                                                                                                        'skin '
                                                                                                        'darkening at '
                                                                                                        'neck folds; '
                                                                                                        'acanthosis '
                                                                                                        'nigricans '
                                                                                                        'raises '
                                                                                                        'insulin '
                                                                                                        'resistance '
                                                                                                        'concern.'},
                                                                 'urine_dipstick': {   'result': 'Clinical '
                                                                                                 'observation: Glucose '
                                                                                                 '+++, Ketones Absent',
                                                                                       'info_gain': 0.54,
                                                                                       'suggests': ['type_2_diabetes'],
                                                                                       'rules_out': [   'diabetic_ketoacidosis'],
                                                                                       'memory_note': 'Recorded: '
                                                                                                      'Glycosuria '
                                                                                                      'detected; '
                                                                                                      'strongly points '
                                                                                                      'to '
                                                                                                      'hyperglycaemia '
                                                                                                      '— blood glucose '
                                                                                                      'confirmation '
                                                                                                      'required.'},
                                                                 'blood_glucose_strip': {   'result': 'Status: Random '
                                                                                                      'Haematic Fluid '
                                                                                                      'Sugar 285 mg/dL',
                                                                                            'info_gain': 1.0,
                                                                                            'suggests': [   'type_2_diabetes'],
                                                                                            'rules_out': [   'hypoglycemia',
                                                                                                             'normal_glucose'],
                                                                                            'memory_note': 'Recorded: '
                                                                                                           'RBS 285 '
                                                                                                           'mg/dL '
                                                                                                           'meets WHO '
                                                                                                           'diagnostic '
                                                                                                           'threshold; '
                                                                                                           'Type 2 '
                                                                                                           'diabetes '
                                                                                                           'diagnostically '
                                                                                                           'verified — '
                                                                                                           'initiate '
                                                                                                           'metformin '
                                                                                                           'and '
                                                                                                           'lifestyle '
                                                                                                           'counselling.'}}},
                                 '16-30': {   'symptoms': [   'blurring of vision',
                                                              'new tingling in feet (neuropathy)',
                                                              'frequent urination at night',
                                                              'excessive thirst'],
                                              'vitals': {'temp': '36.7 C', 'bp': '131/86', 'hr': 74, 'spo2': '98%'},
                                              'test_results': {   'thermometer_check': {   'result': 'Clinical '
                                                                                                     'observation: '
                                                                                                     '36.8 C '
                                                                                                     '(Afebrile)',
                                                                                           'info_gain': 0.03,
                                                                                           'suggests': [],
                                                                                           'rules_out': [   'malaria',
                                                                                                            'infection'],
                                                                                           'memory_note': 'Assessment '
                                                                                                          'notes: '
                                                                                                          'Persistently '
                                                                                                          'afebrile; '
                                                                                                          'fever-based '
                                                                                                          'differential '
                                                                                                          'remains '
                                                                                                          'removed '
                                                                                                          'from '
                                                                                                          'consideration.'},
                                                                  'bp_measurement': {   'result': '135/85 mmHg '
                                                                                                  '(Worsening)',
                                                                                        'info_gain': 0.27,
                                                                                        'suggests': [   'hypertension',
                                                                                                        'diabetic_nephropathy'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'Deteriorating '
                                                                                                       'BP trend; '
                                                                                                       'escalating '
                                                                                                       'hypertension '
                                                                                                       'may indicate '
                                                                                                       'early diabetic '
                                                                                                       'nephropathy — '
                                                                                                       'monitor renal '
                                                                                                       'function.'},
                                                                  'skin_examination': {   'result': 'Acanthosis '
                                                                                                    'nigricans '
                                                                                                    'diagnostically '
                                                                                                    'verified at nape '
                                                                                                    'and both axillae',
                                                                                          'info_gain': 0.35,
                                                                                          'suggests': [   'type_2_diabetes',
                                                                                                          'insulin_resistance'],
                                                                                          'rules_out': [],
                                                                                          'memory_note': 'Clinical '
                                                                                                         'observation: '
                                                                                                         'Worsening '
                                                                                                         'acanthosis '
                                                                                                         'nigricans '
                                                                                                         'now '
                                                                                                         'established '
                                                                                                         'at multiple '
                                                                                                         'sites; '
                                                                                                         'escalating '
                                                                                                         'insulin '
                                                                                                         'resistance '
                                                                                                         'consistent '
                                                                                                         'with '
                                                                                                         'uncontrolled '
                                                                                                         'diabetes.'},
                                                                  'urine_dipstick': {   'result': 'Glucose +++, '
                                                                                                  'Ketones Not '
                                                                                                  'Detected, Protein '
                                                                                                  'Trace',
                                                                                        'info_gain': 0.64,
                                                                                        'suggests': [   'type_2_diabetes',
                                                                                                        'diabetic_nephropathy'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'Provider note: '
                                                                                                       'Escalating '
                                                                                                       'microproteinuria '
                                                                                                       'now present '
                                                                                                       'alongside '
                                                                                                       'persistent '
                                                                                                       'glycosuria; '
                                                                                                       'early diabetic '
                                                                                                       'nephropathy '
                                                                                                       'emerging.'},
                                                                  'blood_glucose_strip': {   'result': 'Recorded: '
                                                                                                       'Random Blood '
                                                                                                       'Sugar 310 '
                                                                                                       'mg/dL',
                                                                                             'info_gain': 1.0,
                                                                                             'suggests': [   'type_2_diabetes'],
                                                                                             'rules_out': [],
                                                                                             'memory_note': 'URGENT: '
                                                                                                            'Escalating '
                                                                                                            'RBS to '
                                                                                                            '310 '
                                                                                                            'mg/dL; '
                                                                                                            'uncontrolled '
                                                                                                            'diabetes '
                                                                                                            'with '
                                                                                                            'escalating '
                                                                                                            'neuropathy '
                                                                                                            'and '
                                                                                                            'nephropathy '
                                                                                                            'risk.'}}}}},
    {   'id': 'case_02_var2',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 46, 'gender': 'female', 'location': 'Remote hamlet, Odisha'},
        'hidden_diagnosis': 'type_2_diabetes',
        'budget': 13,
        'test_costs': {   'thermometer_check': 2,
                          'bp_measurement': 1,
                          'skin_examination': 2,
                          'urine_dipstick': 2,
                          'blood_glucose_strip': 5},
        'relevant_tests': ['blood_glucose_strip', 'urine_dipstick'],
        'conclusive_test': 'blood_glucose_strip',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 30,
        'penalty_events': {   'uncontrolled_hyperglycemia_missed': -0.97,
                              'budget_exhausted': -0.48,
                              'duplicate_test': -0.22},
        'daily_progression': {   '1-15': {   'symptoms': [   'excessive thirst',
                                                             'blurring of vision',
                                                             'frequent urination at night'],
                                             'vitals': {'temp': '37.0 C', 'bp': '126/82', 'hr': 74, 'spo2': '100%'},
                                             'test_results': {   'thermometer_check': {   'result': '36.8 C (Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'malaria',
                                                                                                           'dengue',
                                                                                                           'infection'],
                                                                                          'memory_note': 'Afebrile; '
                                                                                                         'acute '
                                                                                                         'febrile '
                                                                                                         'illness '
                                                                                                         'removed from '
                                                                                                         'consideration '
                                                                                                         'as cause of '
                                                                                                         'polyuria and '
                                                                                                         'thirst.'},
                                                                 'bp_measurement': {   'result': '130/85 mmHg (Stage 1 '
                                                                                                 'Hypertension)',
                                                                                       'info_gain': 0.15,
                                                                                       'suggests': [   'hypertension',
                                                                                                       'type_2_diabetes'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Borderline '
                                                                                                      'elevated BP; '
                                                                                                      'diabetic '
                                                                                                      'hypertension '
                                                                                                      'co-morbidity '
                                                                                                      'possible — '
                                                                                                      'blood glucose '
                                                                                                      'confirmation '
                                                                                                      'required.'},
                                                                 'skin_examination': {   'result': 'Darkening at nape '
                                                                                                   'and axilla — '
                                                                                                   'possible '
                                                                                                   'acanthosis '
                                                                                                   'nigricans',
                                                                                         'info_gain': 0.23,
                                                                                         'suggests': [   'type_2_diabetes',
                                                                                                         'insulin_resistance'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Suspicious '
                                                                                                        'skin '
                                                                                                        'darkening at '
                                                                                                        'neck folds; '
                                                                                                        'acanthosis '
                                                                                                        'nigricans '
                                                                                                        'raises '
                                                                                                        'insulin '
                                                                                                        'resistance '
                                                                                                        'concern.'},
                                                                 'urine_dipstick': {   'result': 'Glucose +++, Ketones '
                                                                                                 'Non-Reactive',
                                                                                       'info_gain': 0.54,
                                                                                       'suggests': ['type_2_diabetes'],
                                                                                       'rules_out': [   'diabetic_ketoacidosis'],
                                                                                       'memory_note': 'Glycosuria '
                                                                                                      'detected; '
                                                                                                      'strongly points '
                                                                                                      'to '
                                                                                                      'hyperglycaemia '
                                                                                                      '— haematic '
                                                                                                      'fluid glucose '
                                                                                                      'confirmation '
                                                                                                      'required.'},
                                                                 'blood_glucose_strip': {   'result': 'Random Blood '
                                                                                                      'Sugar 285 mg/dL',
                                                                                            'info_gain': 1.0,
                                                                                            'suggests': [   'type_2_diabetes'],
                                                                                            'rules_out': [   'hypoglycemia',
                                                                                                             'normal_glucose'],
                                                                                            'memory_note': 'RBS 285 '
                                                                                                           'mg/dL '
                                                                                                           'meets WHO '
                                                                                                           'diagnostic '
                                                                                                           'threshold; '
                                                                                                           'Type 2 '
                                                                                                           'diabetes '
                                                                                                           'diagnostically '
                                                                                                           'verified — '
                                                                                                           'initiate '
                                                                                                           'metformin '
                                                                                                           'and '
                                                                                                           'lifestyle '
                                                                                                           'counselling.'}}},
                                 '16-30': {   'symptoms': [   'Patient reports excessive thirst',
                                                              'Patient reports frequent urination at night',
                                                              'Patient reports blurring of vision',
                                                              'Patient reports new tingling in feet (neuropathy)'],
                                              'vitals': {'temp': '37.0 C', 'bp': '138/85', 'hr': 74, 'spo2': '97%'},
                                              'test_results': {   'thermometer_check': {   'result': '36.8 C '
                                                                                                     '(Afebrile)',
                                                                                           'info_gain': 0.05,
                                                                                           'suggests': [],
                                                                                           'rules_out': [   'malaria',
                                                                                                            'infection'],
                                                                                           'memory_note': 'Persistently '
                                                                                                          'afebrile; '
                                                                                                          'fever-based '
                                                                                                          'differential '
                                                                                                          'remains '
                                                                                                          'excluded.'},
                                                                  'bp_measurement': {   'result': '135/85 mmHg '
                                                                                                  '(Escalating)',
                                                                                        'info_gain': 0.31,
                                                                                        'suggests': [   'hypertension',
                                                                                                        'diabetic_nephropathy'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'Escalating BP '
                                                                                                       'trend; '
                                                                                                       'escalating '
                                                                                                       'hypertension '
                                                                                                       'may indicate '
                                                                                                       'early diabetic '
                                                                                                       'nephropathy — '
                                                                                                       'monitor renal '
                                                                                                       'function.'},
                                                                  'skin_examination': {   'result': 'Acanthosis '
                                                                                                    'nigricans proven '
                                                                                                    'at nape and both '
                                                                                                    'axillae',
                                                                                          'info_gain': 0.29,
                                                                                          'suggests': [   'type_2_diabetes',
                                                                                                          'insulin_resistance'],
                                                                                          'rules_out': [],
                                                                                          'memory_note': 'Escalating '
                                                                                                         'acanthosis '
                                                                                                         'nigricans '
                                                                                                         'now '
                                                                                                         'diagnostically '
                                                                                                         'verified at '
                                                                                                         'multiple '
                                                                                                         'sites; '
                                                                                                         'escalating '
                                                                                                         'insulin '
                                                                                                         'resistance '
                                                                                                         'consistent '
                                                                                                         'with '
                                                                                                         'uncontrolled '
                                                                                                         'diabetes.'},
                                                                  'urine_dipstick': {   'result': 'Glucose +++, '
                                                                                                  'Ketones '
                                                                                                  'Non-Reactive, '
                                                                                                  'Protein Trace',
                                                                                        'info_gain': 0.58,
                                                                                        'suggests': [   'type_2_diabetes',
                                                                                                        'diabetic_nephropathy'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'Escalating '
                                                                                                       'microproteinuria '
                                                                                                       'now present '
                                                                                                       'alongside '
                                                                                                       'persistent '
                                                                                                       'glycosuria; '
                                                                                                       'early diabetic '
                                                                                                       'nephropathy '
                                                                                                       'emerging.'},
                                                                  'blood_glucose_strip': {   'result': 'Random '
                                                                                                       'Vascular Sugar '
                                                                                                       '310 mg/dL',
                                                                                             'info_gain': 1.0,
                                                                                             'suggests': [   'type_2_diabetes'],
                                                                                             'rules_out': [],
                                                                                             'memory_note': 'URGENT: '
                                                                                                            'Worsening '
                                                                                                            'RBS to '
                                                                                                            '310 '
                                                                                                            'mg/dL; '
                                                                                                            'uncontrolled '
                                                                                                            'diabetes '
                                                                                                            'with '
                                                                                                            'escalating '
                                                                                                            'neuropathy '
                                                                                                            'and '
                                                                                                            'nephropathy '
                                                                                                            'risk.'}}}}},
    {   'id': 'case_03_var1',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 41, 'gender': 'female', 'location': 'Desert community, Rajasthan'},
        'hidden_diagnosis': 'hypertension',
        'budget': 14,
        'test_costs': {   'thermometer_check': 2,
                          'skin_examination': 2,
                          'bp_measurement': 1,
                          'urine_dipstick': 3,
                          'pulse_oximeter': 3},
        'relevant_tests': ['bp_measurement', 'urine_dipstick'],
        'conclusive_test': 'bp_measurement',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 30,
        'penalty_events': {'hypertensive_crisis_missed': -0.95, 'budget_exhausted': -0.58, 'duplicate_test': -0.11},
        'daily_progression': {   '1-30': {   'symptoms': [   'occipital headache in mornings',
                                                             'palpitations',
                                                             'dizziness'],
                                             'vitals': {'temp': '37.3 C', 'bp': '180/109', 'hr': 90, 'spo2': '97%'},
                                             'test_results': {   'thermometer_check': {   'result': 'Assessment notes: '
                                                                                                    '37.0 C (Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'malaria',
                                                                                                           'infection'],
                                                                                          'memory_note': 'Recorded: '
                                                                                                         'Afebrile '
                                                                                                         '37.0C; '
                                                                                                         'infectious '
                                                                                                         'cause of '
                                                                                                         'headache '
                                                                                                         'excluded.'},
                                                                 'skin_examination': {   'result': 'Recorded: Slight '
                                                                                                   'facial flushing; '
                                                                                                   'no rash; no pallor',
                                                                                         'info_gain': 0.03,
                                                                                         'suggests': ['hypertension'],
                                                                                         'rules_out': ['anaemia'],
                                                                                         'memory_note': 'Finding: Mild '
                                                                                                        'facial '
                                                                                                        'flushing '
                                                                                                        'noted; '
                                                                                                        'significant '
                                                                                                        'anaemia ruled '
                                                                                                        'out. '
                                                                                                        'Non-specific '
                                                                                                        'finding '
                                                                                                        'alone.'},
                                                                 'bp_measurement': {   'result': '175/105 mmHg (Stage '
                                                                                                 '2 Hypertension)',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['hypertension'],
                                                                                       'rules_out': ['normal_bp'],
                                                                                       'memory_note': 'BP 175/105 mmHg '
                                                                                                      '— Stage 2 '
                                                                                                      'Hypertension '
                                                                                                      'proven. '
                                                                                                      'Initiate '
                                                                                                      'antihypertensive '
                                                                                                      'therapy and '
                                                                                                      'lifestyle '
                                                                                                      'modification.'},
                                                                 'urine_dipstick': {   'result': 'Assessment notes: '
                                                                                                 'Protein Trace, '
                                                                                                 'Glucose Absent',
                                                                                       'info_gain': 0.2,
                                                                                       'suggests': [   'hypertensive_nephropathy'],
                                                                                       'rules_out': ['diabetes', 'uti'],
                                                                                       'memory_note': 'Clinical '
                                                                                                      'observation: '
                                                                                                      'Trace '
                                                                                                      'proteinuria; '
                                                                                                      'possible early '
                                                                                                      'hypertensive '
                                                                                                      'renal '
                                                                                                      'involvement. '
                                                                                                      'Diabetes and '
                                                                                                      'UTI removed '
                                                                                                      'from '
                                                                                                      'consideration.'},
                                                                 'pulse_oximeter': {   'result': 'Status: SpO2 98%, PR '
                                                                                                 '92 bpm',
                                                                                       'info_gain': 0.09,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'heart_failure',
                                                                                                        'respiratory_cause'],
                                                                                       'memory_note': 'Provider note: '
                                                                                                      'SpO2 98%; '
                                                                                                      'significant '
                                                                                                      'cardiac '
                                                                                                      'decompensation '
                                                                                                      'and respiratory '
                                                                                                      'cause of '
                                                                                                      'symptoms '
                                                                                                      'excluded.'}}}}},
    {   'id': 'case_03_var2',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 39, 'gender': 'female', 'location': 'Industrial outskirts, Gujarat'},
        'hidden_diagnosis': 'hypertension',
        'budget': 12,
        'test_costs': {   'thermometer_check': 2,
                          'skin_examination': 2,
                          'bp_measurement': 1,
                          'urine_dipstick': 1,
                          'pulse_oximeter': 3},
        'relevant_tests': ['bp_measurement', 'urine_dipstick'],
        'conclusive_test': 'bp_measurement',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 30,
        'penalty_events': {'hypertensive_crisis_missed': -0.99, 'budget_exhausted': -0.57, 'duplicate_test': -0.25},
        'daily_progression': {   '1-30': {   'symptoms': [   'palpitations',
                                                             'occipital headache in mornings',
                                                             'dizziness'],
                                             'vitals': {'temp': '36.9 C', 'bp': '172/102', 'hr': 87, 'spo2': '99%'},
                                             'test_results': {   'thermometer_check': {   'result': '37.0 C (Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'malaria',
                                                                                                           'infection'],
                                                                                          'memory_note': 'Afebrile '
                                                                                                         '37.0C; '
                                                                                                         'infectious '
                                                                                                         'cause of '
                                                                                                         'headache '
                                                                                                         'ruled out.'},
                                                                 'skin_examination': {   'result': 'Slight facial '
                                                                                                   'flushing; no rash; '
                                                                                                   'no pallor',
                                                                                         'info_gain': 0.03,
                                                                                         'suggests': ['hypertension'],
                                                                                         'rules_out': ['anaemia'],
                                                                                         'memory_note': 'Slight facial '
                                                                                                        'flushing '
                                                                                                        'noted; '
                                                                                                        'significant '
                                                                                                        'anaemia '
                                                                                                        'excluded. '
                                                                                                        'Non-specific '
                                                                                                        'finding '
                                                                                                        'alone.'},
                                                                 'bp_measurement': {   'result': '175/105 mmHg (Stage '
                                                                                                 '2 Hypertension)',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['hypertension'],
                                                                                       'rules_out': ['normal_bp'],
                                                                                       'memory_note': 'BP 175/105 mmHg '
                                                                                                      '— Stage 2 '
                                                                                                      'Hypertension '
                                                                                                      'established. '
                                                                                                      'Initiate '
                                                                                                      'antihypertensive '
                                                                                                      'therapy and '
                                                                                                      'lifestyle '
                                                                                                      'modification.'},
                                                                 'urine_dipstick': {   'result': 'Protein Trace, '
                                                                                                 'Glucose Non-Reactive',
                                                                                       'info_gain': 0.22,
                                                                                       'suggests': [   'hypertensive_nephropathy'],
                                                                                       'rules_out': ['diabetes', 'uti'],
                                                                                       'memory_note': 'Trace '
                                                                                                      'proteinuria; '
                                                                                                      'possible early '
                                                                                                      'hypertensive '
                                                                                                      'renal '
                                                                                                      'involvement. '
                                                                                                      'Diabetes and '
                                                                                                      'UTI excluded.'},
                                                                 'pulse_oximeter': {   'result': 'SpO2 98%, PR 92 bpm',
                                                                                       'info_gain': 0.01,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'heart_failure',
                                                                                                        'respiratory_cause'],
                                                                                       'memory_note': 'SpO2 98%; '
                                                                                                      'significant '
                                                                                                      'cardiac '
                                                                                                      'decompensation '
                                                                                                      'and respiratory '
                                                                                                      'cause of '
                                                                                                      'symptoms '
                                                                                                      'excluded.'}}}}},
    {   'id': 'case_04_var1',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 62, 'gender': 'male', 'location': 'Agricultural town, Punjab'},
        'hidden_diagnosis': 'ischaemic_heart_disease',
        'budget': 11,
        'test_costs': {   'thermometer_check': 2,
                          'skin_examination': 1,
                          'chest_auscultation': 2,
                          'bp_measurement': 1,
                          'pulse_oximeter': 3},
        'relevant_tests': ['bp_measurement', 'pulse_oximeter', 'skin_examination'],
        'conclusive_test': 'skin_examination',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Cardiac Emergency)',
        'critical_window_days': 1,
        'penalty_events': {   'delayed_referral_post_symptom_onset': -1.07,
                              'budget_exhausted': -0.44,
                              'duplicate_test': -0.27},
        'daily_progression': {   '1': {   'symptoms': [   'sweating',
                                                          'nausea',
                                                          'feeling of impending doom',
                                                          'shortness of breath',
                                                          'heavy chest pain radiating to left arm'],
                                          'vitals': {'temp': '36.4 C', 'bp': '145/92', 'hr': 111, 'spo2': '95%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.5 C (Afebrile)',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'infection',
                                                                                                        'malaria'],
                                                                                       'memory_note': 'Afebrile; '
                                                                                                      'infective cause '
                                                                                                      'of chest pain '
                                                                                                      'excluded.'},
                                                              'skin_examination': {   'result': 'Profuse diaphoresis '
                                                                                                '(cold sweats), pale '
                                                                                                'extremities',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'ischaemic_heart_disease',
                                                                                                      'myocardial_infarction'],
                                                                                      'rules_out': [   'musculoskeletal_pain',
                                                                                                       'anxiety'],
                                                                                      'memory_note': 'Provider note: '
                                                                                                     'Profuse cold '
                                                                                                     'sweats with '
                                                                                                     'peripheral '
                                                                                                     'pallor and arm '
                                                                                                     'radiation — '
                                                                                                     'classic '
                                                                                                     'autonomic '
                                                                                                     'response of '
                                                                                                     'acute MI. '
                                                                                                     'critical '
                                                                                                     'referral to '
                                                                                                     'cardiac '
                                                                                                     'emergency.'},
                                                              'chest_auscultation': {   'result': 'Benign heart '
                                                                                                  'sounds; no murmur; '
                                                                                                  'slight basal rales',
                                                                                        'info_gain': 0.33,
                                                                                        'suggests': [   'ischaemic_heart_disease',
                                                                                                        'early_heart_failure'],
                                                                                        'rules_out': [   'pneumonia',
                                                                                                         'pleuritis'],
                                                                                        'memory_note': 'Recorded: Mild '
                                                                                                       'basal '
                                                                                                       'crepitations '
                                                                                                       'suggest early '
                                                                                                       'pulmonary '
                                                                                                       'oedema; no '
                                                                                                       'pericardial '
                                                                                                       'rub. '
                                                                                                       'Consistent '
                                                                                                       'with acute '
                                                                                                       'ischaemic '
                                                                                                       'event.'},
                                                              'bp_measurement': {   'result': '150/90 mmHg',
                                                                                    'info_gain': 0.18,
                                                                                    'suggests': [   'hypertension',
                                                                                                    'ischaemic_heart_disease'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Finding: '
                                                                                                   'Hypertensive BP in '
                                                                                                   'context of chest '
                                                                                                   'pain; known risk '
                                                                                                   'factor and acute '
                                                                                                   'stress response in '
                                                                                                   'MI.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 94%, PR 110 bpm '
                                                                                              '(Rapid Pulse)',
                                                                                    'info_gain': 0.34,
                                                                                    'suggests': [   'ischaemic_heart_disease',
                                                                                                    'heart_failure'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Provider note: '
                                                                                                   'SpO2 94% with '
                                                                                                   'rapid pulse; '
                                                                                                   'significant '
                                                                                                   'haemodynamic '
                                                                                                   'compromise '
                                                                                                   'consistent with '
                                                                                                   'acute MI — '
                                                                                                   'immediate referral '
                                                                                                   'mandatory.'}}}}},
    {   'id': 'case_04_var2',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 66, 'gender': 'male', 'location': 'Suburban area, Karnataka'},
        'hidden_diagnosis': 'ischaemic_heart_disease',
        'budget': 9,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'chest_auscultation': 2,
                          'bp_measurement': 1,
                          'pulse_oximeter': 2},
        'relevant_tests': ['bp_measurement', 'pulse_oximeter', 'skin_examination'],
        'conclusive_test': 'skin_examination',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Cardiac Emergency)',
        'critical_window_days': 1,
        'penalty_events': {   'delayed_referral_post_symptom_onset': -1.03,
                              'budget_exhausted': -0.5,
                              'duplicate_test': -0.28},
        'daily_progression': {   '1': {   'symptoms': [   'feeling of impending doom',
                                                          'shortness of breath',
                                                          'nausea',
                                                          'sweating',
                                                          'heavy chest pain radiating to left arm'],
                                          'vitals': {'temp': '36.3 C', 'bp': '153/90', 'hr': 109, 'spo2': '94%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.5 C (Afebrile)',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'infection',
                                                                                                        'malaria'],
                                                                                       'memory_note': 'Afebrile; '
                                                                                                      'infective cause '
                                                                                                      'of chest pain '
                                                                                                      'ruled out.'},
                                                              'skin_examination': {   'result': 'Profuse diaphoresis '
                                                                                                '(cold sweats), pale '
                                                                                                'extremities',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'ischaemic_heart_disease',
                                                                                                      'myocardial_infarction'],
                                                                                      'rules_out': [   'musculoskeletal_pain',
                                                                                                       'anxiety'],
                                                                                      'memory_note': 'Profuse cold '
                                                                                                     'sweats with '
                                                                                                     'peripheral '
                                                                                                     'pallor and arm '
                                                                                                     'radiation — '
                                                                                                     'classic '
                                                                                                     'autonomic '
                                                                                                     'response of '
                                                                                                     'acute MI. '
                                                                                                     'immediate action '
                                                                                                     'needed referral '
                                                                                                     'to cardiac '
                                                                                                     'emergency.'},
                                                              'chest_auscultation': {   'result': 'Normal heart '
                                                                                                  'sounds; no murmur; '
                                                                                                  'minor basal '
                                                                                                  'crepitations',
                                                                                        'info_gain': 0.35,
                                                                                        'suggests': [   'ischaemic_heart_disease',
                                                                                                        'early_heart_failure'],
                                                                                        'rules_out': [   'pneumonia',
                                                                                                         'pleuritis'],
                                                                                        'memory_note': 'Slight basal '
                                                                                                       'rales suggest '
                                                                                                       'early '
                                                                                                       'pulmonary '
                                                                                                       'oedema; no '
                                                                                                       'pericardial '
                                                                                                       'rub. '
                                                                                                       'Consistent '
                                                                                                       'with acute '
                                                                                                       'ischaemic '
                                                                                                       'event.'},
                                                              'bp_measurement': {   'result': '150/90 mmHg',
                                                                                    'info_gain': 0.16,
                                                                                    'suggests': [   'hypertension',
                                                                                                    'ischaemic_heart_disease'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Hypertensive BP in '
                                                                                                   'context of chest '
                                                                                                   'tenderness; known '
                                                                                                   'risk factor and '
                                                                                                   'acute stress '
                                                                                                   'response in MI.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 94%, PR 110 bpm '
                                                                                              '(Tachycardia)',
                                                                                    'info_gain': 0.27,
                                                                                    'suggests': [   'ischaemic_heart_disease',
                                                                                                    'heart_failure'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'SpO2 94% with '
                                                                                                   'tachycardia; '
                                                                                                   'significant '
                                                                                                   'haemodynamic '
                                                                                                   'compromise '
                                                                                                   'consistent with '
                                                                                                   'acute MI — '
                                                                                                   'immediate referral '
                                                                                                   'mandatory.'}}}}},
    {   'id': 'case_05_var1',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 23, 'gender': 'male', 'location': 'Semi-urban clinic, Maharashtra'},
        'hidden_diagnosis': 'nutritional_anemia',
        'budget': 10,
        'test_costs': {   'thermometer_check': 1,
                          'bp_measurement': 2,
                          'urine_dipstick': 1,
                          'skin_examination': 1,
                          'hemoglobin_strip': 3},
        'relevant_tests': ['skin_examination', 'hemoglobin_strip'],
        'conclusive_test': 'hemoglobin_strip',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 30,
        'penalty_events': {'severe_anaemia_untreated': -1.01, 'budget_exhausted': -0.48, 'duplicate_test': -0.14},
        'daily_progression': {   '1-30': {   'symptoms': [   'craving to eat dirt (pica)',
                                                             'severe fatigue',
                                                             'dizziness',
                                                             'breathlessness on walking'],
                                             'vitals': {'temp': '37.2 C', 'bp': '97/56', 'hr': 103, 'spo2': '96%'},
                                             'test_results': {   'thermometer_check': {   'result': '37.0 C (Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'malaria',
                                                                                                           'infection'],
                                                                                          'memory_note': 'Afebrile; '
                                                                                                         'infectious '
                                                                                                         'cause of '
                                                                                                         'fatigue '
                                                                                                         'ruled out.'},
                                                                 'bp_measurement': {   'result': 'Finding: 100/60 mmHg '
                                                                                                 '(Depressed)',
                                                                                       'info_gain': 0.25,
                                                                                       'suggests': [   'nutritional_anemia',
                                                                                                       'dehydration'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Low BP 100/60; '
                                                                                                      'hypotension '
                                                                                                      'consistent with '
                                                                                                      'intense anaemia '
                                                                                                      'and reduced '
                                                                                                      'cardiac '
                                                                                                      'preload.'},
                                                                 'urine_dipstick': {   'result': 'Unremarkable; '
                                                                                                 'Glucose Absent, '
                                                                                                 'Protein Negative',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'diabetes',
                                                                                                        'uti',
                                                                                                        'renal_disease'],
                                                                                       'memory_note': 'Urinalysis '
                                                                                                      'unremarkable; '
                                                                                                      'renal, diabetic '
                                                                                                      'and urinary '
                                                                                                      'causes of '
                                                                                                      'fatigue '
                                                                                                      'eliminated.'},
                                                                 'skin_examination': {   'result': 'Pronounced pallor '
                                                                                                   'in conjunctiva and '
                                                                                                   'palms, koilonychia '
                                                                                                   '(spoon nails)',
                                                                                         'info_gain': 0.55,
                                                                                         'suggests': [   'iron_deficiency_anemia',
                                                                                                         'nutritional_anemia'],
                                                                                         'rules_out': ['malaria'],
                                                                                         'memory_note': 'Provider '
                                                                                                        'note: '
                                                                                                        'Koilonychia '
                                                                                                        'and '
                                                                                                        'conjunctival '
                                                                                                        'pallor '
                                                                                                        'strongly '
                                                                                                        'suggest iron '
                                                                                                        'deficiency '
                                                                                                        'anaemia; '
                                                                                                        'haemoglobin '
                                                                                                        'confirmation '
                                                                                                        'required.'},
                                                                 'hemoglobin_strip': {   'result': 'Status: 7.2 g/dL '
                                                                                                   '(Significant '
                                                                                                   'Anaemia)',
                                                                                         'info_gain': 1.0,
                                                                                         'suggests': [   'nutritional_anemia',
                                                                                                         'iron_deficiency'],
                                                                                         'rules_out': [   'normal_hemoglobin'],
                                                                                         'memory_note': 'Hb 7.2 g/dL — '
                                                                                                        'intense '
                                                                                                        'anaemia '
                                                                                                        'established. '
                                                                                                        'With '
                                                                                                        'koilonychia '
                                                                                                        'and pica, '
                                                                                                        'iron '
                                                                                                        'deficiency '
                                                                                                        'nutritional '
                                                                                                        'anaemia '
                                                                                                        'established. '
                                                                                                        'Initiate iron '
                                                                                                        'supplementation.'}}}}},
    {   'id': 'case_05_var2',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 24, 'gender': 'male', 'location': 'Tea estate, Assam'},
        'hidden_diagnosis': 'nutritional_anemia',
        'budget': 9,
        'test_costs': {   'thermometer_check': 1,
                          'bp_measurement': 1,
                          'urine_dipstick': 1,
                          'skin_examination': 1,
                          'hemoglobin_strip': 4},
        'relevant_tests': ['skin_examination', 'hemoglobin_strip'],
        'conclusive_test': 'hemoglobin_strip',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 30,
        'penalty_events': {'severe_anaemia_untreated': -0.91, 'budget_exhausted': -0.46, 'duplicate_test': -0.2},
        'daily_progression': {   '1-30': {   'symptoms': [   'severe fatigue',
                                                             'craving to eat dirt (pica)',
                                                             'breathlessness on walking',
                                                             'dizziness'],
                                             'vitals': {'temp': '37.2 C', 'bp': '105/58', 'hr': 110, 'spo2': '98%'},
                                             'test_results': {   'thermometer_check': {   'result': '37.0 C (Afebrile)',
                                                                                          'info_gain': 0.02,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'malaria',
                                                                                                           'infection'],
                                                                                          'memory_note': 'Afebrile; '
                                                                                                         'infectious '
                                                                                                         'cause of '
                                                                                                         'fatigue '
                                                                                                         'ruled out.'},
                                                                 'bp_measurement': {   'result': '100/60 mmHg '
                                                                                                 '(Decreased)',
                                                                                       'info_gain': 0.22,
                                                                                       'suggests': [   'nutritional_anemia',
                                                                                                       'dehydration'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Depressed BP '
                                                                                                      '100/60; '
                                                                                                      'hypotension '
                                                                                                      'consistent with '
                                                                                                      'significant '
                                                                                                      'anaemia and '
                                                                                                      'reduced cardiac '
                                                                                                      'preload.'},
                                                                 'urine_dipstick': {   'result': 'Unremarkable; '
                                                                                                 'Glucose Absent, '
                                                                                                 'Protein Absent',
                                                                                       'info_gain': 0.04,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'diabetes',
                                                                                                        'uti',
                                                                                                        'renal_disease'],
                                                                                       'memory_note': 'Urinalysis '
                                                                                                      'benign; renal, '
                                                                                                      'diabetic and '
                                                                                                      'urinary causes '
                                                                                                      'of fatigue '
                                                                                                      'excluded.'},
                                                                 'skin_examination': {   'result': 'Pronounced pallor '
                                                                                                   'in conjunctiva and '
                                                                                                   'palms, koilonychia '
                                                                                                   '(spoon nails)',
                                                                                         'info_gain': 0.45,
                                                                                         'suggests': [   'iron_deficiency_anemia',
                                                                                                         'nutritional_anemia'],
                                                                                         'rules_out': ['malaria'],
                                                                                         'memory_note': 'Koilonychia '
                                                                                                        'and '
                                                                                                        'conjunctival '
                                                                                                        'pallor '
                                                                                                        'strongly '
                                                                                                        'suggest iron '
                                                                                                        'deficiency '
                                                                                                        'anaemia; '
                                                                                                        'haemoglobin '
                                                                                                        'confirmation '
                                                                                                        'required.'},
                                                                 'hemoglobin_strip': {   'result': '7.2 g/dL (Severe '
                                                                                                   'Anaemia)',
                                                                                         'info_gain': 1.0,
                                                                                         'suggests': [   'nutritional_anemia',
                                                                                                         'iron_deficiency'],
                                                                                         'rules_out': [   'normal_hemoglobin'],
                                                                                         'memory_note': 'Hb 7.2 g/dL — '
                                                                                                        'marked '
                                                                                                        'anaemia '
                                                                                                        'confirmed. '
                                                                                                        'With '
                                                                                                        'koilonychia '
                                                                                                        'and pica, '
                                                                                                        'iron '
                                                                                                        'deficiency '
                                                                                                        'nutritional '
                                                                                                        'anaemia '
                                                                                                        'established. '
                                                                                                        'Initiate iron '
                                                                                                        'supplementation.'}}}}},
    {   'id': 'case_06_var1',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 1, 'gender': 'female', 'location': 'Industrial outskirts, Gujarat'},
        'hidden_diagnosis': 'diarrheal_disease_with_dehydration',
        'budget': 7,
        'test_costs': {'thermometer_check': 1, 'skin_examination': 2, 'pulse_oximeter': 2, 'bp_measurement': 1},
        'relevant_tests': ['skin_examination', 'bp_measurement'],
        'conclusive_test': 'skin_examination',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 1,
        'penalty_events': {'hypovolemic_shock_without_ors': -1.06, 'budget_exhausted': -0.53, 'duplicate_test': -0.17},
        'daily_progression': {   '1': {   'symptoms': [   'Patient reports decreased urination',
                                                          'Patient reports watery loose stools 8 times today',
                                                          'Patient reports lethargy',
                                                          'Patient reports vomiting'],
                                          'vitals': {'temp': '37.2 C', 'bp': '87/58', 'hr': 127, 'spo2': '95%'},
                                          'test_results': {   'thermometer_check': {   'result': 'Assessment notes: '
                                                                                                 '37.5 C (Low-grade '
                                                                                                 'febrile state)',
                                                                                       'info_gain': 0.07,
                                                                                       'suggests': [   'gastroenteritis',
                                                                                                       'enteric_infection'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'mild febrile '
                                                                                                      'state 37.5C; '
                                                                                                      'low-intensity '
                                                                                                      'systemic '
                                                                                                      'response to '
                                                                                                      'enteric '
                                                                                                      'infectious '
                                                                                                      'process noted.'},
                                                              'skin_examination': {   'result': 'Clinical observation: '
                                                                                                'Decreased skin turgor '
                                                                                                '(pinch recoil slow), '
                                                                                                'sunken eyes, dry '
                                                                                                'mucosa',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'dehydration',
                                                                                                      'diarrheal_disease'],
                                                                                      'rules_out': [   'malnutrition_only'],
                                                                                      'memory_note': 'Classic triad of '
                                                                                                     'dehydration — '
                                                                                                     'decreased '
                                                                                                     'turgor, sunken '
                                                                                                     'eyes, dry mucosa '
                                                                                                     'confirmed. '
                                                                                                     'Moderate-to-severe '
                                                                                                     'dehydration. '
                                                                                                     'Initiate ORS '
                                                                                                     'immediately.'},
                                                              'pulse_oximeter': {   'result': 'Recorded: SpO2 97%, PR '
                                                                                              '130 bpm (Tachycardia)',
                                                                                    'info_gain': 0.19,
                                                                                    'suggests': [   'dehydration',
                                                                                                    'shock'],
                                                                                    'rules_out': ['pneumonia'],
                                                                                    'memory_note': 'Tachycardia 130 '
                                                                                                   'bpm; haemodynamic '
                                                                                                   'compromise from '
                                                                                                   'dehydration. '
                                                                                                   'Respiratory '
                                                                                                   'compromise '
                                                                                                   'excluded.'},
                                                              'bp_measurement': {   'result': '85/55 mmHg (Borderline '
                                                                                              'hypotension for age)',
                                                                                    'info_gain': 0.44,
                                                                                    'suggests': [   'dehydration',
                                                                                                    'hypovolemic_shock'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Recorded: '
                                                                                                   'Borderline '
                                                                                                   'hypotension 85/55 '
                                                                                                   'mmHg; hypovolaemic '
                                                                                                   'shock threshold '
                                                                                                   'approaching — '
                                                                                                   'critical '
                                                                                                   'rehydration '
                                                                                                   'required.'}}}}},
    {   'id': 'case_06_var2',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 8, 'gender': 'female', 'location': 'Rural Village, UP'},
        'hidden_diagnosis': 'diarrheal_disease_with_dehydration',
        'budget': 10,
        'test_costs': {'thermometer_check': 2, 'skin_examination': 1, 'pulse_oximeter': 2, 'bp_measurement': 1},
        'relevant_tests': ['skin_examination', 'bp_measurement'],
        'conclusive_test': 'skin_examination',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 1,
        'penalty_events': {'hypovolemic_shock_without_ors': -0.98, 'budget_exhausted': -0.45, 'duplicate_test': -0.19},
        'daily_progression': {   '1': {   'symptoms': [   'lethargy',
                                                          'vomiting',
                                                          'watery loose stools 8 times today',
                                                          'decreased urination'],
                                          'vitals': {'temp': '37.5 C', 'bp': '82/51', 'hr': 135, 'spo2': '98%'},
                                          'test_results': {   'thermometer_check': {   'result': '37.5 C (mild fever)',
                                                                                       'info_gain': 0.11,
                                                                                       'suggests': [   'gastroenteritis',
                                                                                                       'enteric_infection'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'mild pyrexia '
                                                                                                      '37.5C; '
                                                                                                      'low-intensity '
                                                                                                      'systemic '
                                                                                                      'response to '
                                                                                                      'enteric '
                                                                                                      'pathogen '
                                                                                                      'presence '
                                                                                                      'noted.'},
                                                              'skin_examination': {   'result': 'Decreased skin turgor '
                                                                                                '(pinch recoil slow), '
                                                                                                'sunken eyes, dry '
                                                                                                'mucosa',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'dehydration',
                                                                                                      'diarrheal_disease'],
                                                                                      'rules_out': [   'malnutrition_only'],
                                                                                      'memory_note': 'Classic triad of '
                                                                                                     'dehydration — '
                                                                                                     'decreased '
                                                                                                     'turgor, sunken '
                                                                                                     'eyes, dry mucosa '
                                                                                                     'proven. '
                                                                                                     'Moderate-to-severe '
                                                                                                     'dehydration. '
                                                                                                     'Initiate ORS '
                                                                                                     'immediately.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 97%, PR 130 bpm '
                                                                                              '(Elevated Heart Rate)',
                                                                                    'info_gain': 0.24,
                                                                                    'suggests': [   'dehydration',
                                                                                                    'shock'],
                                                                                    'rules_out': ['pneumonia'],
                                                                                    'memory_note': 'Elevated Heart '
                                                                                                   'Rate 130 bpm; '
                                                                                                   'haemodynamic '
                                                                                                   'compromise from '
                                                                                                   'dehydration. '
                                                                                                   'Respiratory '
                                                                                                   'compromise '
                                                                                                   'excluded.'},
                                                              'bp_measurement': {   'result': '85/55 mmHg (Borderline '
                                                                                              'hypotension for age)',
                                                                                    'info_gain': 0.36,
                                                                                    'suggests': [   'dehydration',
                                                                                                    'hypovolemic_shock'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Borderline '
                                                                                                   'hypotension 85/55 '
                                                                                                   'mmHg; hypovolaemic '
                                                                                                   'shock threshold '
                                                                                                   'approaching — '
                                                                                                   'critical '
                                                                                                   'rehydration '
                                                                                                   'required.'}}}}},
    {   'id': 'case_07_var1',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 29, 'gender': 'male', 'location': 'River island, Majuli'},
        'hidden_diagnosis': 'malaria',
        'budget': 13,
        'test_costs': {   'thermometer_check': 2,
                          'skin_examination': 1,
                          'pulse_oximeter': 1,
                          'blood_panel': 5,
                          'rapid_malaria_test': 3},
        'relevant_tests': ['thermometer_check', 'rapid_malaria_test', 'blood_panel'],
        'conclusive_test': 'rapid_malaria_test',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 2,
        'penalty_events': {'missed_diagnosis_after_day_2': -0.94, 'budget_exhausted': -0.45, 'duplicate_test': -0.28},
        'daily_progression': {   '1': {   'symptoms': [   'Patient reports high grade fever',
                                                          'Patient reports shivering/chills',
                                                          'Patient reports sweating',
                                                          'Patient reports body ache'],
                                          'vitals': {'temp': '39.9 C', 'bp': '105/66', 'hr': 106, 'spo2': '96%'},
                                          'test_results': {   'thermometer_check': {   'result': '39.6 C',
                                                                                       'info_gain': 0.35,
                                                                                       'suggests': [   'malaria',
                                                                                                       'dengue',
                                                                                                       'typhoid'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Elevated '
                                                                                                      'elevated temp '
                                                                                                      '39.6C; febrile '
                                                                                                      'illness with '
                                                                                                      'malarial '
                                                                                                      'periodicity '
                                                                                                      'pattern '
                                                                                                      'suspected — '
                                                                                                      'non-specific '
                                                                                                      'alone.'},
                                                              'rapid_malaria_test': {   'result': 'Confirmed Presence '
                                                                                                  'Of for Plasmodium '
                                                                                                  'vivax',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': ['malaria'],
                                                                                        'rules_out': [   'typhoid',
                                                                                                         'dengue',
                                                                                                         'kala_azar'],
                                                                                        'memory_note': 'RDT confirms '
                                                                                                       'P. vivax '
                                                                                                       'malaria. '
                                                                                                       'Assessment '
                                                                                                       'established — '
                                                                                                       'initiate '
                                                                                                       'chloroquine '
                                                                                                       'and primaquine '
                                                                                                       'regimen.'},
                                                              'blood_panel': {   'result': 'Hb 10.5 g/dL, Platelets '
                                                                                           '140,000/mcL, WBC 5,200/mcL',
                                                                                 'info_gain': 0.22,
                                                                                 'suggests': ['malaria', 'dengue'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'Low-Intensity anaemia '
                                                                                                'and borderline '
                                                                                                'thrombocytopenia; '
                                                                                                'consistent with early '
                                                                                                'malaria but '
                                                                                                'non-specific without '
                                                                                                'RDT.'},
                                                              'skin_examination': {   'result': 'No rash, no '
                                                                                                'petechiae, no '
                                                                                                'significant pallor',
                                                                                      'info_gain': 0.02,
                                                                                      'suggests': [],
                                                                                      'rules_out': [   'dengue',
                                                                                                       'nutritional_anemia'],
                                                                                      'memory_note': 'Skin examination '
                                                                                                     'unremarkable; '
                                                                                                     'dengue '
                                                                                                     'haemorrhagic '
                                                                                                     'rash and '
                                                                                                     'significant '
                                                                                                     'anaemia pallor '
                                                                                                     'removed from '
                                                                                                     'consideration.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 98%, PR 108 bpm',
                                                                                    'info_gain': 0.03,
                                                                                    'suggests': [],
                                                                                    'rules_out': [   'pneumonia',
                                                                                                     'copd_exacerbation'],
                                                                                    'memory_note': 'Recorded: Oxygen '
                                                                                                   'saturation 98%; '
                                                                                                   'significant '
                                                                                                   'respiratory '
                                                                                                   'compromise '
                                                                                                   'eliminated at this '
                                                                                                   'stage.'}}},
                                 '2': {   'symptoms': [   'severe rigors',
                                                          'extreme weakness',
                                                          'vomiting',
                                                          'altered sensorium',
                                                          'persistent high fever'],
                                          'vitals': {'temp': '39.9 C', 'bp': '97/66', 'hr': 122, 'spo2': '96%'},
                                          'test_results': {   'thermometer_check': {   'result': 'Clinical '
                                                                                                 'observation: 40.1 C',
                                                                                       'info_gain': 0.44,
                                                                                       'suggests': [   'malaria',
                                                                                                       'severe_malaria'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Status: '
                                                                                                      'Escalating '
                                                                                                      'elevated temp '
                                                                                                      'to 40.1C with '
                                                                                                      'worsening '
                                                                                                      'rigors; marked '
                                                                                                      'malaria '
                                                                                                      'progression '
                                                                                                      'with cerebral '
                                                                                                      'involvement '
                                                                                                      'risk.'},
                                                              'rapid_malaria_test': {   'result': 'Recorded: Positive '
                                                                                                  'for Plasmodium '
                                                                                                  'vivax',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': ['malaria'],
                                                                                        'rules_out': [   'typhoid',
                                                                                                         'dengue'],
                                                                                        'memory_note': 'URGENT: RDT '
                                                                                                       'persistently '
                                                                                                       'detected with '
                                                                                                       'altered '
                                                                                                       'sensorium — P. '
                                                                                                       'vivax '
                                                                                                       'established, '
                                                                                                       'escalating to '
                                                                                                       'significant '
                                                                                                       'malaria.'},
                                                              'blood_panel': {   'result': 'Hb 9.8 g/dL, Platelets '
                                                                                           '110,000/mcL, WBC 4,800/mcL',
                                                                                 'info_gain': 0.32,
                                                                                 'suggests': [   'malaria',
                                                                                                 'severe_malaria'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'Provider note: '
                                                                                                'Worsening anaemia '
                                                                                                '(9.8 g/dL) and '
                                                                                                'falling platelets; '
                                                                                                'disease progression '
                                                                                                'confirms escalating '
                                                                                                'intense malaria.'},
                                                              'skin_examination': {   'result': 'Mild pallor noted in '
                                                                                                'conjunctiva; no rash',
                                                                                      'info_gain': 0.1,
                                                                                      'suggests': ['malaria'],
                                                                                      'rules_out': ['dengue'],
                                                                                      'memory_note': 'Clinical '
                                                                                                     'observation: '
                                                                                                     'Emerging pallor '
                                                                                                     'consistent with '
                                                                                                     'worsening '
                                                                                                     'haemolysis; '
                                                                                                     'dengue rash '
                                                                                                     'absent, '
                                                                                                     'reinforcing '
                                                                                                     'malaria clinical '
                                                                                                     'impression.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 97%, PR 120 bpm',
                                                                                    'info_gain': 0.13,
                                                                                    'suggests': ['severe_malaria'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Assessment notes: '
                                                                                                   'Escalating rapid '
                                                                                                   'pulse (120 bpm); '
                                                                                                   'SpO2 marginally '
                                                                                                   'declining — '
                                                                                                   'monitor closely '
                                                                                                   'for respiratory '
                                                                                                   'deterioration.'}}}}},
    {   'id': 'case_07_var2',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 24, 'gender': 'male', 'location': 'Forest fringes, Chhattisgarh'},
        'hidden_diagnosis': 'malaria',
        'budget': 15,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'pulse_oximeter': 1,
                          'blood_panel': 5,
                          'rapid_malaria_test': 3},
        'relevant_tests': ['thermometer_check', 'rapid_malaria_test', 'blood_panel'],
        'conclusive_test': 'rapid_malaria_test',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 2,
        'penalty_events': {'missed_diagnosis_after_day_2': -0.95, 'budget_exhausted': -0.55, 'duplicate_test': -0.14},
        'daily_progression': {   '1': {   'symptoms': ['body ache', 'shivering/chills', 'sweating', 'high grade fever'],
                                          'vitals': {'temp': '39.7 C', 'bp': '107/70', 'hr': 103, 'spo2': '98%'},
                                          'test_results': {   'thermometer_check': {   'result': '39.6 C',
                                                                                       'info_gain': 0.27,
                                                                                       'suggests': [   'malaria',
                                                                                                       'dengue',
                                                                                                       'typhoid'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Raised pyrexia '
                                                                                                      '39.6C; febrile '
                                                                                                      'illness with '
                                                                                                      'malarial '
                                                                                                      'periodicity '
                                                                                                      'pattern '
                                                                                                      'suspected — '
                                                                                                      'non-specific '
                                                                                                      'alone.'},
                                                              'rapid_malaria_test': {   'result': 'Confirmed Presence '
                                                                                                  'Of for Plasmodium '
                                                                                                  'vivax',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': ['malaria'],
                                                                                        'rules_out': [   'typhoid',
                                                                                                         'dengue',
                                                                                                         'kala_azar'],
                                                                                        'memory_note': 'RDT confirms '
                                                                                                       'P. vivax '
                                                                                                       'malaria. '
                                                                                                       'Assessment '
                                                                                                       'established — '
                                                                                                       'initiate '
                                                                                                       'chloroquine '
                                                                                                       'and primaquine '
                                                                                                       'regimen.'},
                                                              'blood_panel': {   'result': 'Hb 10.5 g/dL, Platelets '
                                                                                           '140,000/mcL, WBC 5,200/mcL',
                                                                                 'info_gain': 0.24,
                                                                                 'suggests': ['malaria', 'dengue'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'Minor anaemia and '
                                                                                                'borderline '
                                                                                                'thrombocytopenia; '
                                                                                                'consistent with early '
                                                                                                'malaria but '
                                                                                                'non-specific without '
                                                                                                'RDT.'},
                                                              'skin_examination': {   'result': 'No rash, no '
                                                                                                'petechiae, no '
                                                                                                'significant pallor',
                                                                                      'info_gain': 0.02,
                                                                                      'suggests': [],
                                                                                      'rules_out': [   'dengue',
                                                                                                       'nutritional_anemia'],
                                                                                      'memory_note': 'Skin examination '
                                                                                                     'unremarkable; '
                                                                                                     'dengue '
                                                                                                     'haemorrhagic '
                                                                                                     'rash and '
                                                                                                     'significant '
                                                                                                     'anaemia pallor '
                                                                                                     'ruled out.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 98%, PR 108 bpm',
                                                                                    'info_gain': 0.06,
                                                                                    'suggests': [],
                                                                                    'rules_out': [   'pneumonia',
                                                                                                     'copd_exacerbation'],
                                                                                    'memory_note': 'Oxygen saturation '
                                                                                                   '98%; significant '
                                                                                                   'respiratory '
                                                                                                   'compromise ruled '
                                                                                                   'out at this '
                                                                                                   'stage.'}}},
                                 '2': {   'symptoms': [   'Patient reports severe rigors',
                                                          'Patient reports vomiting',
                                                          'Patient reports extreme weakness',
                                                          'Patient reports persistent high fever',
                                                          'Patient reports altered sensorium'],
                                          'vitals': {'temp': '39.8 C', 'bp': '98/67', 'hr': 126, 'spo2': '95%'},
                                          'test_results': {   'thermometer_check': {   'result': '40.1 C',
                                                                                       'info_gain': 0.35,
                                                                                       'suggests': [   'malaria',
                                                                                                       'severe_malaria'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Escalating '
                                                                                                      'pyrexia to '
                                                                                                      '40.1C with '
                                                                                                      'worsening '
                                                                                                      'rigors; severe '
                                                                                                      'malaria '
                                                                                                      'progression '
                                                                                                      'with cerebral '
                                                                                                      'involvement '
                                                                                                      'risk.'},
                                                              'rapid_malaria_test': {   'result': 'Reactive for '
                                                                                                  'Plasmodium vivax',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': ['malaria'],
                                                                                        'rules_out': [   'typhoid',
                                                                                                         'dengue'],
                                                                                        'memory_note': 'URGENT: RDT '
                                                                                                       'persistently '
                                                                                                       'reactive with '
                                                                                                       'altered '
                                                                                                       'sensorium — P. '
                                                                                                       'vivax '
                                                                                                       'established, '
                                                                                                       'escalating to '
                                                                                                       'marked '
                                                                                                       'malaria.'},
                                                              'blood_panel': {   'result': 'Hb 9.8 g/dL, Platelets '
                                                                                           '110,000/mcL, WBC 4,800/mcL',
                                                                                 'info_gain': 0.39,
                                                                                 'suggests': [   'malaria',
                                                                                                 'severe_malaria'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'Progressing anaemia '
                                                                                                '(9.8 g/dL) and '
                                                                                                'falling platelets; '
                                                                                                'disease progression '
                                                                                                'confirms escalating '
                                                                                                'marked malaria.'},
                                                              'skin_examination': {   'result': 'Minor pallor noted in '
                                                                                                'conjunctiva; no rash',
                                                                                      'info_gain': 0.08,
                                                                                      'suggests': ['malaria'],
                                                                                      'rules_out': ['dengue'],
                                                                                      'memory_note': 'Emerging pallor '
                                                                                                     'consistent with '
                                                                                                     'worsening '
                                                                                                     'haemolysis; '
                                                                                                     'dengue rash '
                                                                                                     'absent, '
                                                                                                     'reinforcing '
                                                                                                     'malaria '
                                                                                                     'diagnosis.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 97%, PR 120 bpm',
                                                                                    'info_gain': 0.14,
                                                                                    'suggests': ['severe_malaria'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Escalating '
                                                                                                   'tachycardia (120 '
                                                                                                   'bpm); SpO2 '
                                                                                                   'marginally '
                                                                                                   'declining — '
                                                                                                   'monitor closely '
                                                                                                   'for respiratory '
                                                                                                   'deterioration.'}}}}},
    {   'id': 'case_08_var1',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 23, 'gender': 'male', 'location': 'Forest fringes, Chhattisgarh'},
        'hidden_diagnosis': 'dengue',
        'budget': 19,
        'test_costs': {   'thermometer_check': 2,
                          'skin_examination': 1,
                          'tourniquet_test': 1,
                          'pulse_oximeter': 3,
                          'blood_panel': 6,
                          'rapid_dengue_test': 4},
        'relevant_tests': ['tourniquet_test', 'rapid_dengue_test', 'blood_panel'],
        'conclusive_test': 'rapid_dengue_test',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 3,
        'penalty_events': {'dengue_shock_without_referral': -1.07, 'budget_exhausted': -0.57, 'duplicate_test': -0.2},
        'daily_progression': {   '1': {   'symptoms': [   'Patient reports retro-orbital pain',
                                                          'Patient reports severe bone pain (breakbone fever)',
                                                          'Patient reports sudden fever',
                                                          'Patient reports nausea'],
                                          'vitals': {'temp': '39.3 C', 'bp': '100/62', 'hr': 106, 'spo2': '97%'},
                                          'test_results': {   'thermometer_check': {   'result': '39.2 C (Abrupt-onset '
                                                                                                 'fever)',
                                                                                       'info_gain': 0.23,
                                                                                       'suggests': [   'dengue',
                                                                                                       'malaria',
                                                                                                       'typhoid'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Raised pyrexia '
                                                                                                      '39.2C abrupt '
                                                                                                      'onset; febrile '
                                                                                                      'illness with '
                                                                                                      'dengue-compatible '
                                                                                                      'pattern.'},
                                                              'skin_examination': {   'result': 'Assessment notes: No '
                                                                                                'petechiae visible; no '
                                                                                                'rash yet',
                                                                                      'info_gain': 0.1,
                                                                                      'suggests': [],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'No cutaneous '
                                                                                                     'haemorrhagic '
                                                                                                     'signs at this '
                                                                                                     'stage; dengue '
                                                                                                     'rash typically '
                                                                                                     'appears by day '
                                                                                                     '3.'},
                                                              'tourniquet_test': {   'result': 'Positive (>10 '
                                                                                               'petechiae)',
                                                                                     'info_gain': 0.44,
                                                                                     'suggests': [   'dengue',
                                                                                                     'dengue_haemorrhagic_fever'],
                                                                                     'rules_out': [],
                                                                                     'memory_note': 'Detected '
                                                                                                    'tourniquet test '
                                                                                                    'with >10 '
                                                                                                    'petechiae; '
                                                                                                    'capillary '
                                                                                                    'fragility proven '
                                                                                                    '— dengue '
                                                                                                    'haemorrhagic risk '
                                                                                                    'flagged.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 98%, PR 100 bpm',
                                                                                    'info_gain': 0.08,
                                                                                    'suggests': [],
                                                                                    'rules_out': [   'respiratory_failure'],
                                                                                    'memory_note': 'SpO2 98%; no '
                                                                                                   'respiratory '
                                                                                                   'compromise at this '
                                                                                                   'stage.'},
                                                              'blood_panel': {   'result': 'Platelets 95,000/mcL, WBC '
                                                                                           '3,200/mcL',
                                                                                 'info_gain': 0.28,
                                                                                 'suggests': ['dengue', 'viral_fever'],
                                                                                 'rules_out': ['bacterial_sepsis'],
                                                                                 'memory_note': 'Thrombocytopenia and '
                                                                                                'leukopenia; '
                                                                                                'characteristic of '
                                                                                                'dengue viral illness '
                                                                                                '— bacterial sepsis '
                                                                                                'excluded.'},
                                                              'rapid_dengue_test': {   'result': 'NS1 Antigen Positive',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['dengue'],
                                                                                       'rules_out': [   'malaria',
                                                                                                        'typhoid',
                                                                                                        'chikungunya'],
                                                                                       'memory_note': 'NS1 antigen '
                                                                                                      'reactive on day '
                                                                                                      '1; dengue '
                                                                                                      'established in '
                                                                                                      'febrile phase. '
                                                                                                      'Monitor for '
                                                                                                      'warning signs '
                                                                                                      'closely.'}}},
                                 '2': {   'symptoms': [   'Patient reports lethargy',
                                                          'Patient reports persistent vomiting',
                                                          'Patient reports fever breaking (critical phase)',
                                                          'Patient reports abdominal pain'],
                                          'vitals': {'temp': '37.4 C', 'bp': '92/63', 'hr': 109, 'spo2': '98%'},
                                          'test_results': {   'thermometer_check': {   'result': 'Recorded: 37.5 C '
                                                                                                 '(Pyrexia '
                                                                                                 'defervescing — '
                                                                                                 'critical phase '
                                                                                                 'entry)',
                                                                                       'info_gain': 0.31,
                                                                                       'suggests': [   'dengue_critical_phase'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Provider note: '
                                                                                                      'Escalating '
                                                                                                      'concern: fever '
                                                                                                      'breaking '
                                                                                                      'signals entry '
                                                                                                      'into dengue '
                                                                                                      'critical phase '
                                                                                                      '— plasma '
                                                                                                      'leakage risk '
                                                                                                      'increases now.'},
                                                              'skin_examination': {   'result': 'Mild flushing; no '
                                                                                                'spontaneous petechiae '
                                                                                                'yet',
                                                                                      'info_gain': 0.18,
                                                                                      'suggests': ['dengue'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Assessment '
                                                                                                     'notes: '
                                                                                                     'Escalating '
                                                                                                     'flushing; '
                                                                                                     'clinical '
                                                                                                     'evolution '
                                                                                                     'consistent with '
                                                                                                     'dengue '
                                                                                                     'progression. '
                                                                                                     'Spontaneous '
                                                                                                     'bleeding not yet '
                                                                                                     'manifest.'},
                                                              'tourniquet_test': {   'result': 'Positive (>20 '
                                                                                               'petechiae)',
                                                                                     'info_gain': 0.55,
                                                                                     'suggests': [   'dengue_haemorrhagic_fever',
                                                                                                     'plasma_leakage'],
                                                                                     'rules_out': [],
                                                                                     'memory_note': 'Escalating '
                                                                                                    'capillary '
                                                                                                    'fragility: >20 '
                                                                                                    'petechiae now. '
                                                                                                    'Escalating '
                                                                                                    'haemorrhagic '
                                                                                                    'dengue — monitor '
                                                                                                    'BP and platelets '
                                                                                                    'urgently.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 98%, PR 110 bpm',
                                                                                    'info_gain': 0.19,
                                                                                    'suggests': [   'dengue_critical_phase'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Clinical '
                                                                                                   'observation: '
                                                                                                   'Rising elevated '
                                                                                                   'heart rate 110 bpm '
                                                                                                   'during fever '
                                                                                                   'defervescence; '
                                                                                                   'warning sign for '
                                                                                                   'haemodynamic '
                                                                                                   'compromise.'},
                                                              'blood_panel': {   'result': 'Platelets 60,000/mcL, WBC '
                                                                                           '2,800/mcL, rising '
                                                                                           'haematocrit',
                                                                                 'info_gain': 0.35,
                                                                                 'suggests': [   'dengue_haemorrhagic_fever',
                                                                                                 'plasma_leakage'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'Status: Escalating '
                                                                                                'thrombocytopenia '
                                                                                                '(60K) with rising '
                                                                                                'haematocrit — '
                                                                                                'classical dengue '
                                                                                                'plasma leakage '
                                                                                                'pattern escalating.'},
                                                              'rapid_dengue_test': {   'result': 'NS1 Antigen '
                                                                                                 'Detected, IgM '
                                                                                                 'Confirmed Presence '
                                                                                                 'Of',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['dengue'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'URGENT: Both '
                                                                                                      'NS1 and IgM '
                                                                                                      'detected — '
                                                                                                      'established '
                                                                                                      'dengue with '
                                                                                                      'escalating '
                                                                                                      'haemorrhagic '
                                                                                                      'features. '
                                                                                                      'Critical phase '
                                                                                                      'monitoring '
                                                                                                      'mandatory.'}}},
                                 '3': {   'symptoms': [   'Patient reports severe abdominal pain',
                                                          'Patient reports cold clammy skin',
                                                          'Patient reports restlessness',
                                                          'Patient reports bleeding from gums'],
                                          'vitals': {'temp': '36.6 C', 'bp': '81/58', 'hr': 124, 'spo2': '97%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.8 C (Afebrile — '
                                                                                                 'shock phase)',
                                                                                       'info_gain': 0.44,
                                                                                       'suggests': [   'dengue_shock_syndrome'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Afebrile but '
                                                                                                      'haemodynamically '
                                                                                                      'deteriorating — '
                                                                                                      'dengue shock '
                                                                                                      'syndrome now '
                                                                                                      'imminent.'},
                                                              'skin_examination': {   'result': 'Provider note: '
                                                                                                'Spontaneous petechiae '
                                                                                                'visible without test; '
                                                                                                'cool clammy skin',
                                                                                      'info_gain': 0.28,
                                                                                      'suggests': [   'dengue_haemorrhagic_fever',
                                                                                                      'dengue_shock_syndrome'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'URGENT: '
                                                                                                     'Spontaneous '
                                                                                                     'petechiae and '
                                                                                                     'cold clammy '
                                                                                                     'extremities — '
                                                                                                     'clinical dengue '
                                                                                                     'shock syndrome. '
                                                                                                     'Immediate '
                                                                                                     'referral '
                                                                                                     'required.'},
                                                              'tourniquet_test': {   'result': 'Spontaneous petechiae '
                                                                                               'visible — formal test '
                                                                                               'unnecessary',
                                                                                     'info_gain': 0.64,
                                                                                     'suggests': [   'dengue_shock_syndrome'],
                                                                                     'rules_out': [],
                                                                                     'memory_note': 'URGENT: Test '
                                                                                                    'unnecessary — '
                                                                                                    'spontaneous '
                                                                                                    'haemorrhage '
                                                                                                    'confirms severe '
                                                                                                    'dengue. Patient '
                                                                                                    'needs critical '
                                                                                                    'transfusion '
                                                                                                    'facility.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 96%, PR 130 bpm',
                                                                                    'info_gain': 0.29,
                                                                                    'suggests': [   'dengue_shock_syndrome',
                                                                                                    'hypovolemia'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'URGENT: Escalating '
                                                                                                   'tachycardia 130 '
                                                                                                   'bpm with falling '
                                                                                                   'SpO2 — '
                                                                                                   'haemodynamic '
                                                                                                   'collapse '
                                                                                                   'progressing.'},
                                                              'blood_panel': {   'result': 'Recorded: Platelets '
                                                                                           '25,000/mcL (Critical); WBC '
                                                                                           '2,400/mcL',
                                                                                 'info_gain': 0.45,
                                                                                 'suggests': [   'dengue_shock_syndrome',
                                                                                                 'dengue_haemorrhagic_fever'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'URGENT: Platelets '
                                                                                                'collapsed to '
                                                                                                '25,000/mcL — '
                                                                                                'life-threatening '
                                                                                                'thrombocytopenia. '
                                                                                                'Platelet transfusion '
                                                                                                'required urgently.'},
                                                              'rapid_dengue_test': {   'result': 'Assessment notes: '
                                                                                                 'IgM Reactive',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['dengue'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'URGENT: '
                                                                                                      'IgM-confirmed '
                                                                                                      'dengue in shock '
                                                                                                      'phase — '
                                                                                                      'escalating to '
                                                                                                      'dengue shock '
                                                                                                      'syndrome. '
                                                                                                      'Immediate '
                                                                                                      'hospital '
                                                                                                      'referral '
                                                                                                      'mandatory.'}}}}},
    {   'id': 'case_08_var2',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 15, 'gender': 'male', 'location': 'Agricultural town, Punjab'},
        'hidden_diagnosis': 'dengue',
        'budget': 18,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 2,
                          'tourniquet_test': 1,
                          'pulse_oximeter': 2,
                          'blood_panel': 5,
                          'rapid_dengue_test': 5},
        'relevant_tests': ['tourniquet_test', 'rapid_dengue_test', 'blood_panel'],
        'conclusive_test': 'rapid_dengue_test',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 3,
        'penalty_events': {'dengue_shock_without_referral': -1.07, 'budget_exhausted': -0.57, 'duplicate_test': -0.24},
        'daily_progression': {   '1': {   'symptoms': [   'Patient reports sudden fever',
                                                          'Patient reports nausea',
                                                          'Patient reports retro-orbital pain',
                                                          'Patient reports severe bone pain (breakbone fever)'],
                                          'vitals': {'temp': '39.2 C', 'bp': '105/63', 'hr': 104, 'spo2': '96%'},
                                          'test_results': {   'thermometer_check': {   'result': '39.2 C (Abrupt-onset '
                                                                                                 'elevated temp)',
                                                                                       'info_gain': 0.18,
                                                                                       'suggests': [   'dengue',
                                                                                                       'malaria',
                                                                                                       'typhoid'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Increased fever '
                                                                                                      '39.2C abrupt '
                                                                                                      'onset; febrile '
                                                                                                      'illness with '
                                                                                                      'dengue-compatible '
                                                                                                      'pattern.'},
                                                              'skin_examination': {   'result': 'No petechiae visible; '
                                                                                                'no rash yet',
                                                                                      'info_gain': 0.09,
                                                                                      'suggests': [],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'No cutaneous '
                                                                                                     'haemorrhagic '
                                                                                                     'signs at this '
                                                                                                     'stage; dengue '
                                                                                                     'rash typically '
                                                                                                     'appears by day '
                                                                                                     '3.'},
                                                              'tourniquet_test': {   'result': 'Reactive (>10 '
                                                                                               'petechiae)',
                                                                                     'info_gain': 0.43,
                                                                                     'suggests': [   'dengue',
                                                                                                     'dengue_haemorrhagic_fever'],
                                                                                     'rules_out': [],
                                                                                     'memory_note': 'Confirmed '
                                                                                                    'Presence Of '
                                                                                                    'tourniquet test '
                                                                                                    'with >10 '
                                                                                                    'petechiae; '
                                                                                                    'capillary '
                                                                                                    'fragility '
                                                                                                    'diagnostically '
                                                                                                    'verified — dengue '
                                                                                                    'haemorrhagic risk '
                                                                                                    'flagged.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 98%, PR 100 bpm',
                                                                                    'info_gain': 0.0,
                                                                                    'suggests': [],
                                                                                    'rules_out': [   'respiratory_failure'],
                                                                                    'memory_note': 'SpO2 98%; no '
                                                                                                   'respiratory '
                                                                                                   'compromise at this '
                                                                                                   'stage.'},
                                                              'blood_panel': {   'result': 'Platelets 95,000/mcL, WBC '
                                                                                           '3,200/mcL',
                                                                                 'info_gain': 0.26,
                                                                                 'suggests': ['dengue', 'viral_fever'],
                                                                                 'rules_out': ['bacterial_sepsis'],
                                                                                 'memory_note': 'Thrombocytopenia and '
                                                                                                'leukopenia; '
                                                                                                'characteristic of '
                                                                                                'dengue viral illness '
                                                                                                '— bacterial sepsis '
                                                                                                'excluded.'},
                                                              'rapid_dengue_test': {   'result': 'NS1 Antigen '
                                                                                                 'Confirmed Presence '
                                                                                                 'Of',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['dengue'],
                                                                                       'rules_out': [   'malaria',
                                                                                                        'typhoid',
                                                                                                        'chikungunya'],
                                                                                       'memory_note': 'NS1 antigen '
                                                                                                      'confirmed '
                                                                                                      'presence of on '
                                                                                                      'day 1; dengue '
                                                                                                      'diagnostically '
                                                                                                      'verified in '
                                                                                                      'febrile phase. '
                                                                                                      'Monitor for '
                                                                                                      'warning signs '
                                                                                                      'closely.'}}},
                                 '2': {   'symptoms': [   'Patient reports abdominal pain',
                                                          'Patient reports lethargy',
                                                          'Patient reports persistent vomiting',
                                                          'Patient reports fever breaking (critical phase)'],
                                          'vitals': {'temp': '37.6 C', 'bp': '98/64', 'hr': 110, 'spo2': '96%'},
                                          'test_results': {   'thermometer_check': {   'result': '37.5 C (Fever '
                                                                                                 'defervescing — '
                                                                                                 'critical phase '
                                                                                                 'entry)',
                                                                                       'info_gain': 0.3,
                                                                                       'suggests': [   'dengue_critical_phase'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Escalating '
                                                                                                      'concern: '
                                                                                                      'elevated temp '
                                                                                                      'breaking '
                                                                                                      'signals entry '
                                                                                                      'into dengue '
                                                                                                      'critical phase '
                                                                                                      '— plasma '
                                                                                                      'leakage risk '
                                                                                                      'increases now.'},
                                                              'skin_examination': {   'result': 'Low-Intensity '
                                                                                                'flushing; no '
                                                                                                'spontaneous petechiae '
                                                                                                'yet',
                                                                                      'info_gain': 0.23,
                                                                                      'suggests': ['dengue'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Progressing '
                                                                                                     'flushing; '
                                                                                                     'clinical '
                                                                                                     'evolution '
                                                                                                     'consistent with '
                                                                                                     'dengue '
                                                                                                     'progression. '
                                                                                                     'Spontaneous '
                                                                                                     'bleeding not yet '
                                                                                                     'manifest.'},
                                                              'tourniquet_test': {   'result': 'Reactive (>20 '
                                                                                               'petechiae)',
                                                                                     'info_gain': 0.58,
                                                                                     'suggests': [   'dengue_haemorrhagic_fever',
                                                                                                     'plasma_leakage'],
                                                                                     'rules_out': [],
                                                                                     'memory_note': 'Progressing '
                                                                                                    'capillary '
                                                                                                    'fragility: >20 '
                                                                                                    'petechiae now. '
                                                                                                    'Escalating '
                                                                                                    'haemorrhagic '
                                                                                                    'dengue — monitor '
                                                                                                    'BP and platelets '
                                                                                                    'urgently.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 98%, PR 110 bpm',
                                                                                    'info_gain': 0.13,
                                                                                    'suggests': [   'dengue_critical_phase'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Rising tachycardia '
                                                                                                   '110 bpm during '
                                                                                                   'febrile state '
                                                                                                   'defervescence; '
                                                                                                   'warning sign for '
                                                                                                   'haemodynamic '
                                                                                                   'compromise.'},
                                                              'blood_panel': {   'result': 'Platelets 60,000/mcL, WBC '
                                                                                           '2,800/mcL, rising '
                                                                                           'haematocrit',
                                                                                 'info_gain': 0.34,
                                                                                 'suggests': [   'dengue_haemorrhagic_fever',
                                                                                                 'plasma_leakage'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'Escalating '
                                                                                                'thrombocytopenia '
                                                                                                '(60K) with rising '
                                                                                                'haematocrit — '
                                                                                                'classical dengue '
                                                                                                'plasma leakage '
                                                                                                'pattern escalating.'},
                                                              'rapid_dengue_test': {   'result': 'NS1 Antigen '
                                                                                                 'Confirmed Presence '
                                                                                                 'Of, IgM Detected',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['dengue'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'URGENT: Both '
                                                                                                      'NS1 and IgM '
                                                                                                      'positive — '
                                                                                                      'proven dengue '
                                                                                                      'with escalating '
                                                                                                      'haemorrhagic '
                                                                                                      'features. '
                                                                                                      'Critical phase '
                                                                                                      'monitoring '
                                                                                                      'mandatory.'}}},
                                 '3': {   'symptoms': [   'severe abdominal pain',
                                                          'cold clammy skin',
                                                          'restlessness',
                                                          'bleeding from gums'],
                                          'vitals': {'temp': '36.5 C', 'bp': '83/58', 'hr': 135, 'spo2': '95%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.8 C (Afebrile — '
                                                                                                 'shock phase)',
                                                                                       'info_gain': 0.4,
                                                                                       'suggests': [   'dengue_shock_syndrome'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Afebrile but '
                                                                                                      'haemodynamically '
                                                                                                      'deteriorating — '
                                                                                                      'dengue shock '
                                                                                                      'syndrome now '
                                                                                                      'imminent.'},
                                                              'skin_examination': {   'result': 'Spontaneous petechiae '
                                                                                                'visible without test; '
                                                                                                'cool clammy skin',
                                                                                      'info_gain': 0.35,
                                                                                      'suggests': [   'dengue_haemorrhagic_fever',
                                                                                                      'dengue_shock_syndrome'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'URGENT: '
                                                                                                     'Spontaneous '
                                                                                                     'petechiae and '
                                                                                                     'cold clammy '
                                                                                                     'extremities — '
                                                                                                     'clinical dengue '
                                                                                                     'shock syndrome. '
                                                                                                     'Immediate '
                                                                                                     'referral '
                                                                                                     'required.'},
                                                              'tourniquet_test': {   'result': 'Spontaneous petechiae '
                                                                                               'visible — formal test '
                                                                                               'unnecessary',
                                                                                     'info_gain': 0.64,
                                                                                     'suggests': [   'dengue_shock_syndrome'],
                                                                                     'rules_out': [],
                                                                                     'memory_note': 'URGENT: Test '
                                                                                                    'unnecessary — '
                                                                                                    'spontaneous '
                                                                                                    'haemorrhage '
                                                                                                    'confirms marked '
                                                                                                    'dengue. Patient '
                                                                                                    'needs immediate '
                                                                                                    'action needed '
                                                                                                    'transfusion '
                                                                                                    'facility.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 96%, PR 130 bpm',
                                                                                    'info_gain': 0.25,
                                                                                    'suggests': [   'dengue_shock_syndrome',
                                                                                                    'hypovolemia'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'URGENT: Escalating '
                                                                                                   'elevated heart '
                                                                                                   'rate 130 bpm with '
                                                                                                   'falling SpO2 — '
                                                                                                   'haemodynamic '
                                                                                                   'collapse '
                                                                                                   'progressing.'},
                                                              'blood_panel': {   'result': 'Platelets 25,000/mcL '
                                                                                           '(Critical); WBC 2,400/mcL',
                                                                                 'info_gain': 0.45,
                                                                                 'suggests': [   'dengue_shock_syndrome',
                                                                                                 'dengue_haemorrhagic_fever'],
                                                                                 'rules_out': [],
                                                                                 'memory_note': 'URGENT: Platelets '
                                                                                                'collapsed to '
                                                                                                '25,000/mcL — '
                                                                                                'life-threatening '
                                                                                                'thrombocytopenia. '
                                                                                                'Platelet transfusion '
                                                                                                'required urgently.'},
                                                              'rapid_dengue_test': {   'result': 'IgM Reactive',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': ['dengue'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'URGENT: '
                                                                                                      'IgM-confirmed '
                                                                                                      'dengue in shock '
                                                                                                      'phase — '
                                                                                                      'escalating to '
                                                                                                      'dengue shock '
                                                                                                      'syndrome. '
                                                                                                      'Immediate '
                                                                                                      'hospital '
                                                                                                      'referral '
                                                                                                      'mandatory.'}}}}},
    {   'id': 'case_09_var1',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 60, 'gender': 'male', 'location': 'Tribal area, Jharkhand'},
        'hidden_diagnosis': 'copd_exacerbation',
        'budget': 15,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'bp_measurement': 2,
                          'chest_auscultation': 1,
                          'pulse_oximeter': 3,
                          'sputum_smear': 5},
        'relevant_tests': ['pulse_oximeter', 'chest_auscultation', 'sputum_smear'],
        'conclusive_test': 'pulse_oximeter',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Respiratory Ward)',
        'critical_window_days': 1,
        'penalty_events': {'hypoxia_without_referral': -0.98, 'budget_exhausted': -0.51, 'duplicate_test': -0.15},
        'daily_progression': {   '1': {   'symptoms': [   'Patient reports worsening breathlessness',
                                                          'Patient reports inability to speak full sentences',
                                                          'Patient reports productive cough with green sputum'],
                                          'vitals': {'temp': '37.4 C', 'bp': '149/89', 'hr': 108, 'spo2': '87%'},
                                          'test_results': {   'thermometer_check': {   'result': '37.6 C (mild '
                                                                                                 'pyrexia)',
                                                                                       'info_gain': 0.08,
                                                                                       'suggests': [   'infection',
                                                                                                       'copd_infective_exacerbation'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Low-grade '
                                                                                                      'febrile state '
                                                                                                      '37.6C; '
                                                                                                      'infective '
                                                                                                      'trigger for '
                                                                                                      'COPD '
                                                                                                      'exacerbation '
                                                                                                      'likely.'},
                                                              'skin_examination': {   'result': 'Central cyanosis of '
                                                                                                'lips and fingernails; '
                                                                                                'barrel-shaped chest',
                                                                                      'info_gain': 0.36,
                                                                                      'suggests': [   'copd',
                                                                                                      'respiratory_failure'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Central cyanosis '
                                                                                                     'and barrel '
                                                                                                     'chest; '
                                                                                                     'long-standing '
                                                                                                     'obstructive '
                                                                                                     'pulmonary '
                                                                                                     'pathology with '
                                                                                                     'acute '
                                                                                                     'decompensation '
                                                                                                     'evident.'},
                                                              'bp_measurement': {   'result': 'Finding: 145/85 mmHg',
                                                                                    'info_gain': 0.07,
                                                                                    'suggests': ['hypertension'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Elevated BP; '
                                                                                                   'persistent '
                                                                                                   'hypertension '
                                                                                                   'co-morbidity, not '
                                                                                                   'driving acute '
                                                                                                   'management.'},
                                                              'chest_auscultation': {   'result': 'Diffuse expiratory '
                                                                                                  'wheeze, prolonged '
                                                                                                  'expiration, '
                                                                                                  'bilateral coarse '
                                                                                                  'alveolar sounds',
                                                                                        'info_gain': 0.48,
                                                                                        'suggests': [   'copd_exacerbation',
                                                                                                        'copd'],
                                                                                        'rules_out': ['pneumothorax'],
                                                                                        'memory_note': 'Expiratory '
                                                                                                       'wheeze with '
                                                                                                       'prolonged '
                                                                                                       'expiration — '
                                                                                                       'obstructive '
                                                                                                       'pattern '
                                                                                                       'consistent '
                                                                                                       'with COPD '
                                                                                                       'exacerbation. '
                                                                                                       'Pneumothorax '
                                                                                                       'ruled out.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 88% on room air',
                                                                                    'info_gain': 1.0,
                                                                                    'suggests': [   'copd_exacerbation',
                                                                                                    'respiratory_failure'],
                                                                                    'rules_out': ['mild_bronchitis'],
                                                                                    'memory_note': 'SpO2 88% on room '
                                                                                                   'air — '
                                                                                                   'life-threatening '
                                                                                                   'reduced '
                                                                                                   'oxygenation '
                                                                                                   'confirmed. COPD '
                                                                                                   'exacerbation with '
                                                                                                   'type 1 respiratory '
                                                                                                   'failure. critical '
                                                                                                   'referral '
                                                                                                   'required.'},
                                                              'sputum_smear': {   'result': 'Recorded: Absent for AFB',
                                                                                  'info_gain': 0.01,
                                                                                  'suggests': [],
                                                                                  'rules_out': ['tuberculosis'],
                                                                                  'memory_note': 'Finding: '
                                                                                                 'AFB-negative sputum; '
                                                                                                 'tuberculosis ruled '
                                                                                                 'out as cause of '
                                                                                                 'respiratory '
                                                                                                 'deterioration.'}}}}},
    {   'id': 'case_09_var2',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 74, 'gender': 'female', 'location': 'Hilly terrain, Uttarakhand'},
        'hidden_diagnosis': 'copd_exacerbation',
        'budget': 16,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'bp_measurement': 1,
                          'chest_auscultation': 2,
                          'pulse_oximeter': 2,
                          'sputum_smear': 5},
        'relevant_tests': ['pulse_oximeter', 'chest_auscultation', 'sputum_smear'],
        'conclusive_test': 'pulse_oximeter',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Respiratory Ward)',
        'critical_window_days': 1,
        'penalty_events': {'hypoxia_without_referral': -0.92, 'budget_exhausted': -0.5, 'duplicate_test': -0.25},
        'daily_progression': {   '1': {   'symptoms': [   'Patient reports productive cough with green sputum',
                                                          'Patient reports inability to speak full sentences',
                                                          'Patient reports worsening breathlessness'],
                                          'vitals': {'temp': '37.4 C', 'bp': '150/81', 'hr': 112, 'spo2': '88%'},
                                          'test_results': {   'thermometer_check': {   'result': '37.6 C (Low-grade '
                                                                                                 'febrile state)',
                                                                                       'info_gain': 0.06,
                                                                                       'suggests': [   'infection',
                                                                                                       'copd_infective_exacerbation'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'mild pyrexia '
                                                                                                      '37.6C; '
                                                                                                      'infective '
                                                                                                      'trigger for '
                                                                                                      'COPD '
                                                                                                      'exacerbation '
                                                                                                      'likely.'},
                                                              'skin_examination': {   'result': 'Central cyanosis of '
                                                                                                'lips and fingernails; '
                                                                                                'barrel-shaped chest',
                                                                                      'info_gain': 0.38,
                                                                                      'suggests': [   'copd',
                                                                                                      'respiratory_failure'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Central cyanosis '
                                                                                                     'and barrel '
                                                                                                     'chest; '
                                                                                                     'persistent '
                                                                                                     'obstructive '
                                                                                                     'pulmonary '
                                                                                                     'pathology with '
                                                                                                     'acute '
                                                                                                     'decompensation '
                                                                                                     'evident.'},
                                                              'bp_measurement': {   'result': '145/85 mmHg',
                                                                                    'info_gain': 0.07,
                                                                                    'suggests': ['hypertension'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Elevated BP; '
                                                                                                   'persistent '
                                                                                                   'hypertension '
                                                                                                   'co-morbidity, not '
                                                                                                   'driving acute '
                                                                                                   'management.'},
                                                              'chest_auscultation': {   'result': 'Diffuse expiratory '
                                                                                                  'wheeze, prolonged '
                                                                                                  'expiration, '
                                                                                                  'bilateral coarse '
                                                                                                  'rales',
                                                                                        'info_gain': 0.47,
                                                                                        'suggests': [   'copd_exacerbation',
                                                                                                        'copd'],
                                                                                        'rules_out': ['pneumothorax'],
                                                                                        'memory_note': 'Expiratory '
                                                                                                       'wheeze with '
                                                                                                       'prolonged '
                                                                                                       'expiration — '
                                                                                                       'obstructive '
                                                                                                       'pattern '
                                                                                                       'consistent '
                                                                                                       'with COPD '
                                                                                                       'exacerbation. '
                                                                                                       'Pneumothorax '
                                                                                                       'excluded.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 88% on room air',
                                                                                    'info_gain': 1.0,
                                                                                    'suggests': [   'copd_exacerbation',
                                                                                                    'respiratory_failure'],
                                                                                    'rules_out': ['mild_bronchitis'],
                                                                                    'memory_note': 'SpO2 88% on room '
                                                                                                   'air — '
                                                                                                   'life-threatening '
                                                                                                   'hypoxia '
                                                                                                   'diagnostically '
                                                                                                   'verified. COPD '
                                                                                                   'exacerbation with '
                                                                                                   'type 1 respiratory '
                                                                                                   'failure. '
                                                                                                   'time-sensitive '
                                                                                                   'referral '
                                                                                                   'required.'},
                                                              'sputum_smear': {   'result': 'Negative for AFB',
                                                                                  'info_gain': 0.0,
                                                                                  'suggests': [],
                                                                                  'rules_out': ['tuberculosis'],
                                                                                  'memory_note': 'AFB-negative sputum; '
                                                                                                 'tuberculosis removed '
                                                                                                 'from consideration '
                                                                                                 'as cause of '
                                                                                                 'respiratory '
                                                                                                 'deterioration.'}}}}},
    {   'id': 'case_10_var1',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 36, 'gender': 'female', 'location': 'Rural Village, UP'},
        'hidden_diagnosis': 'typhoid_fever',
        'budget': 23,
        'test_costs': {   'thermometer_check': 1,
                          'abdominal_exam': 1,
                          'urine_dipstick': 3,
                          'rapid_malaria_test': 4,
                          'blood_panel': 4,
                          'widal_test': 6},
        'relevant_tests': ['thermometer_check', 'abdominal_exam', 'widal_test'],
        'conclusive_test': 'widal_test',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 4,
        'penalty_events': {   'intestinal_perforation_without_referral': -0.92,
                              'budget_exhausted': -0.43,
                              'duplicate_test': -0.11},
        'daily_progression': {   '1-2': {   'symptoms': [   'Patient reports abdominal discomfort',
                                                            'Patient reports fever for 8 days gradually increasing',
                                                            'Patient reports constipation',
                                                            'Patient reports dull headache'],
                                            'vitals': {'temp': '39.3 C', 'bp': '113/73', 'hr': 75, 'spo2': '99%'},
                                            'test_results': {   'thermometer_check': {   'result': '39.0 C (Relative '
                                                                                                   'bradycardia noted)',
                                                                                         'info_gain': 0.21,
                                                                                         'suggests': [   'typhoid',
                                                                                                         'malaria',
                                                                                                         'dengue'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Provider '
                                                                                                        'note: '
                                                                                                        'Sustained '
                                                                                                        '39.0C fever '
                                                                                                        'with '
                                                                                                        'pulse-temperature '
                                                                                                        'dissociation; '
                                                                                                        'relative '
                                                                                                        'bradycardia '
                                                                                                        'raises '
                                                                                                        'clinical '
                                                                                                        'suspicion for '
                                                                                                        'typhoid.'},
                                                                'abdominal_exam': {   'result': 'Minor splenomegaly, '
                                                                                                'diffuse tenderness',
                                                                                      'info_gain': 0.3,
                                                                                      'suggests': [   'typhoid',
                                                                                                      'hepatitis_a',
                                                                                                      'kala_azar'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Status: Minor '
                                                                                                     'splenomegaly on '
                                                                                                     'palpation; '
                                                                                                     'narrows '
                                                                                                     'differential '
                                                                                                     'toward typhoid '
                                                                                                     'or viral '
                                                                                                     'hepatitis.'},
                                                                'widal_test': {   'result': 'Status: Positive (TO '
                                                                                            '1:320, TH 1:160)',
                                                                                  'info_gain': 1.0,
                                                                                  'suggests': ['typhoid'],
                                                                                  'rules_out': [   'malaria',
                                                                                                   'dengue',
                                                                                                   'hepatitis_a'],
                                                                                  'memory_note': 'Widal TO 1:320 meets '
                                                                                                 'diagnostic '
                                                                                                 'threshold; typhoid '
                                                                                                 'febrile state '
                                                                                                 'established — begin '
                                                                                                 'ciprofloxacin or '
                                                                                                 'azithromycin.'},
                                                                'blood_panel': {   'result': 'Status: WBC 3,400/mcL '
                                                                                             '(leukopenia), Hb 11.2 '
                                                                                             'g/dL, Platelets '
                                                                                             '180,000/mcL',
                                                                                   'info_gain': 0.26,
                                                                                   'suggests': ['typhoid', 'dengue'],
                                                                                   'rules_out': [   'bacterial_pyogenic_infection'],
                                                                                   'memory_note': 'Leukopenia '
                                                                                                  'characteristic of '
                                                                                                  'Salmonella typhi; '
                                                                                                  'helps exclude '
                                                                                                  'pyogenic bacterial '
                                                                                                  'sepsis from '
                                                                                                  'differential.'},
                                                                'urine_dipstick': {   'result': 'Trace protein, '
                                                                                                'Glucose Absent, '
                                                                                                'Bilirubin Absent',
                                                                                      'info_gain': 0.06,
                                                                                      'suggests': [],
                                                                                      'rules_out': [   'diabetes',
                                                                                                       'uti',
                                                                                                       'hepatitis'],
                                                                                      'memory_note': 'Urine '
                                                                                                     'unremarkable; '
                                                                                                     'UTI, diabetes, '
                                                                                                     'and significant '
                                                                                                     'hepatic jaundice '
                                                                                                     'removed from '
                                                                                                     'consideration.'},
                                                                'rapid_malaria_test': {   'result': 'Status: Negative',
                                                                                          'info_gain': 0.01,
                                                                                          'suggests': [],
                                                                                          'rules_out': ['malaria'],
                                                                                          'memory_note': 'Malaria '
                                                                                                         'removed from '
                                                                                                         'consideration '
                                                                                                         'by RDT; '
                                                                                                         'febrile '
                                                                                                         'illness is '
                                                                                                         'non-malarial.'}}},
                                 '3-4': {   'symptoms': [   'pea-soup diarrhea',
                                                            'high step-ladder fever',
                                                            'delirium/confusion',
                                                            'rose spots on trunk'],
                                            'vitals': {'temp': '39.6 C', 'bp': '102/68', 'hr': 90, 'spo2': '96%'},
                                            'test_results': {   'thermometer_check': {   'result': '39.8 C '
                                                                                                   '(Step-ladder '
                                                                                                   'pattern)',
                                                                                         'info_gain': 0.31,
                                                                                         'suggests': [   'typhoid',
                                                                                                         'typhoid_complication'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Escalating '
                                                                                                        'step-ladder '
                                                                                                        'pyrexia to '
                                                                                                        '39.8C; '
                                                                                                        'delirium and '
                                                                                                        'rose spots on '
                                                                                                        'trunk — '
                                                                                                        'escalating '
                                                                                                        'typhoid '
                                                                                                        'progression.'},
                                                                'abdominal_exam': {   'result': 'Significant '
                                                                                                'distension, tender '
                                                                                                'hepatosplenomegaly',
                                                                                      'info_gain': 0.4,
                                                                                      'suggests': [   'typhoid',
                                                                                                      'intestinal_perforation'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'URGENT: Marked '
                                                                                                     'hepatosplenomegaly '
                                                                                                     'with abdominal '
                                                                                                     'distension; '
                                                                                                     'intestinal '
                                                                                                     'perforation risk '
                                                                                                     '— consider '
                                                                                                     'immediate action '
                                                                                                     'needed '
                                                                                                     'referral.'},
                                                                'widal_test': {   'result': 'Clinical observation: '
                                                                                            'Reactive (TO 1:640, TH '
                                                                                            '1:320)',
                                                                                  'info_gain': 1.0,
                                                                                  'suggests': ['typhoid'],
                                                                                  'rules_out': ['malaria', 'dengue'],
                                                                                  'memory_note': 'URGENT: Widal titre '
                                                                                                 'doubled to TO 1:640; '
                                                                                                 'escalating active '
                                                                                                 'typhoid with '
                                                                                                 'impending '
                                                                                                 'complications '
                                                                                                 'proven.'},
                                                                'blood_panel': {   'result': 'WBC 2,800/mcL '
                                                                                             '(progressing '
                                                                                             'leukopenia), Hb 10.5 '
                                                                                             'g/dL',
                                                                                   'info_gain': 0.34,
                                                                                   'suggests': [   'typhoid',
                                                                                                   'typhoid_complication'],
                                                                                   'rules_out': [],
                                                                                   'memory_note': 'Clinical '
                                                                                                  'observation: '
                                                                                                  'Progressing '
                                                                                                  'leukopenia and '
                                                                                                  'anaemia; escalating '
                                                                                                  'systemic typhoid '
                                                                                                  'involvement with '
                                                                                                  'rising complication '
                                                                                                  'risk.'},
                                                                'urine_dipstick': {   'result': 'Finding: Trace '
                                                                                                'protein, Glucose '
                                                                                                'Non-Reactive',
                                                                                      'info_gain': 0.17,
                                                                                      'suggests': [],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Persistent trace '
                                                                                                     'proteinuria; '
                                                                                                     'minor renal '
                                                                                                     'irritation, '
                                                                                                     'non-diagnostic '
                                                                                                     'and not driving '
                                                                                                     'management.'},
                                                                'rapid_malaria_test': {   'result': 'Not Detected',
                                                                                          'info_gain': 0.09,
                                                                                          'suggests': [],
                                                                                          'rules_out': ['malaria'],
                                                                                          'memory_note': 'Malaria '
                                                                                                         'definitively '
                                                                                                         'removed from '
                                                                                                         'consideration; '
                                                                                                         'fever '
                                                                                                         'entirely '
                                                                                                         'explained by '
                                                                                                         'progressing '
                                                                                                         'diagnostically '
                                                                                                         'verified '
                                                                                                         'typhoid.'}}}}},
    {   'id': 'case_10_var2',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 25, 'gender': 'male', 'location': 'Rural Village, UP'},
        'hidden_diagnosis': 'typhoid_fever',
        'budget': 21,
        'test_costs': {   'thermometer_check': 2,
                          'abdominal_exam': 1,
                          'urine_dipstick': 1,
                          'rapid_malaria_test': 3,
                          'blood_panel': 5,
                          'widal_test': 5},
        'relevant_tests': ['thermometer_check', 'abdominal_exam', 'widal_test'],
        'conclusive_test': 'widal_test',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 4,
        'penalty_events': {   'intestinal_perforation_without_referral': -0.99,
                              'budget_exhausted': -0.5,
                              'duplicate_test': -0.19},
        'daily_progression': {   '1-2': {   'symptoms': [   'dull headache',
                                                            'abdominal discomfort',
                                                            'constipation',
                                                            'fever for 8 days gradually increasing'],
                                            'vitals': {'temp': '38.8 C', 'bp': '118/73', 'hr': 75, 'spo2': '97%'},
                                            'test_results': {   'thermometer_check': {   'result': '39.0 C (Relative '
                                                                                                   'bradycardia noted)',
                                                                                         'info_gain': 0.23,
                                                                                         'suggests': [   'typhoid',
                                                                                                         'malaria',
                                                                                                         'dengue'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Sustained '
                                                                                                        '39.0C fever '
                                                                                                        'with '
                                                                                                        'pulse-temperature '
                                                                                                        'dissociation; '
                                                                                                        'relative '
                                                                                                        'bradycardia '
                                                                                                        'raises '
                                                                                                        'clinical '
                                                                                                        'suspicion for '
                                                                                                        'typhoid.'},
                                                                'abdominal_exam': {   'result': 'Slight splenomegaly, '
                                                                                                'diffuse tenderness',
                                                                                      'info_gain': 0.29,
                                                                                      'suggests': [   'typhoid',
                                                                                                      'hepatitis_a',
                                                                                                      'kala_azar'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Mild '
                                                                                                     'splenomegaly on '
                                                                                                     'palpation; '
                                                                                                     'narrows '
                                                                                                     'differential '
                                                                                                     'toward typhoid '
                                                                                                     'or viral '
                                                                                                     'hepatitis.'},
                                                                'widal_test': {   'result': 'Positive (TO 1:320, TH '
                                                                                            '1:160)',
                                                                                  'info_gain': 1.0,
                                                                                  'suggests': ['typhoid'],
                                                                                  'rules_out': [   'malaria',
                                                                                                   'dengue',
                                                                                                   'hepatitis_a'],
                                                                                  'memory_note': 'Widal TO 1:320 meets '
                                                                                                 'diagnostic '
                                                                                                 'threshold; typhoid '
                                                                                                 'elevated temp '
                                                                                                 'diagnostically '
                                                                                                 'verified — begin '
                                                                                                 'ciprofloxacin or '
                                                                                                 'azithromycin.'},
                                                                'blood_panel': {   'result': 'WBC 3,400/mcL '
                                                                                             '(leukopenia), Hb 11.2 '
                                                                                             'g/dL, Platelets '
                                                                                             '180,000/mcL',
                                                                                   'info_gain': 0.31,
                                                                                   'suggests': ['typhoid', 'dengue'],
                                                                                   'rules_out': [   'bacterial_pyogenic_infection'],
                                                                                   'memory_note': 'Leukopenia '
                                                                                                  'characteristic of '
                                                                                                  'Salmonella typhi; '
                                                                                                  'helps exclude '
                                                                                                  'pyogenic bacterial '
                                                                                                  'sepsis from '
                                                                                                  'differential.'},
                                                                'urine_dipstick': {   'result': 'Trace protein, '
                                                                                                'Glucose Absent, '
                                                                                                'Bilirubin '
                                                                                                'Non-Reactive',
                                                                                      'info_gain': 0.1,
                                                                                      'suggests': [],
                                                                                      'rules_out': [   'diabetes',
                                                                                                       'uti',
                                                                                                       'hepatitis'],
                                                                                      'memory_note': 'Urine '
                                                                                                     'unremarkable; '
                                                                                                     'UTI, diabetes, '
                                                                                                     'and significant '
                                                                                                     'hepatic jaundice '
                                                                                                     'excluded.'},
                                                                'rapid_malaria_test': {   'result': 'Non-Reactive',
                                                                                          'info_gain': 0.04,
                                                                                          'suggests': [],
                                                                                          'rules_out': ['malaria'],
                                                                                          'memory_note': 'Malaria '
                                                                                                         'eliminated '
                                                                                                         'by RDT; '
                                                                                                         'febrile '
                                                                                                         'illness is '
                                                                                                         'non-malarial.'}}},
                                 '3-4': {   'symptoms': [   'Patient reports pea-soup diarrhea',
                                                            'Patient reports delirium/confusion',
                                                            'Patient reports rose spots on trunk',
                                                            'Patient reports high step-ladder fever'],
                                            'vitals': {'temp': '40.1 C', 'bp': '106/66', 'hr': 90, 'spo2': '96%'},
                                            'test_results': {   'thermometer_check': {   'result': '39.8 C '
                                                                                                   '(Step-ladder '
                                                                                                   'pattern)',
                                                                                         'info_gain': 0.3,
                                                                                         'suggests': [   'typhoid',
                                                                                                         'typhoid_complication'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Escalating '
                                                                                                        'step-ladder '
                                                                                                        'pyrexia to '
                                                                                                        '39.8C; '
                                                                                                        'delirium and '
                                                                                                        'rose spots on '
                                                                                                        'trunk — '
                                                                                                        'worsening '
                                                                                                        'typhoid '
                                                                                                        'progression.'},
                                                                'abdominal_exam': {   'result': 'Significant '
                                                                                                'distension, tender '
                                                                                                'hepatosplenomegaly',
                                                                                      'info_gain': 0.36,
                                                                                      'suggests': [   'typhoid',
                                                                                                      'intestinal_perforation'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'URGENT: Marked '
                                                                                                     'hepatosplenomegaly '
                                                                                                     'with abdominal '
                                                                                                     'distension; '
                                                                                                     'intestinal '
                                                                                                     'perforation risk '
                                                                                                     '— consider '
                                                                                                     'urgent '
                                                                                                     'referral.'},
                                                                'widal_test': {   'result': 'Reactive (TO 1:640, TH '
                                                                                            '1:320)',
                                                                                  'info_gain': 1.0,
                                                                                  'suggests': ['typhoid'],
                                                                                  'rules_out': ['malaria', 'dengue'],
                                                                                  'memory_note': 'URGENT: Widal titre '
                                                                                                 'doubled to TO 1:640; '
                                                                                                 'escalating active '
                                                                                                 'typhoid with '
                                                                                                 'impending '
                                                                                                 'complications '
                                                                                                 'diagnostically '
                                                                                                 'verified.'},
                                                                'blood_panel': {   'result': 'WBC 2,800/mcL '
                                                                                             '(deteriorating '
                                                                                             'leukopenia), Hb 10.5 '
                                                                                             'g/dL',
                                                                                   'info_gain': 0.44,
                                                                                   'suggests': [   'typhoid',
                                                                                                   'typhoid_complication'],
                                                                                   'rules_out': [],
                                                                                   'memory_note': 'Deteriorating '
                                                                                                  'leukopenia and '
                                                                                                  'anaemia; escalating '
                                                                                                  'systemic typhoid '
                                                                                                  'involvement with '
                                                                                                  'rising complication '
                                                                                                  'risk.'},
                                                                'urine_dipstick': {   'result': 'Trace protein, '
                                                                                                'Glucose Negative',
                                                                                      'info_gain': 0.17,
                                                                                      'suggests': [],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Persistent trace '
                                                                                                     'proteinuria; '
                                                                                                     'minor renal '
                                                                                                     'irritation, '
                                                                                                     'non-diagnostic '
                                                                                                     'and not driving '
                                                                                                     'management.'},
                                                                'rapid_malaria_test': {   'result': 'Non-Reactive',
                                                                                          'info_gain': 0.16,
                                                                                          'suggests': [],
                                                                                          'rules_out': ['malaria'],
                                                                                          'memory_note': 'Malaria '
                                                                                                         'definitively '
                                                                                                         'eliminated; '
                                                                                                         'febrile '
                                                                                                         'state '
                                                                                                         'entirely '
                                                                                                         'explained by '
                                                                                                         'deteriorating '
                                                                                                         'established '
                                                                                                         'typhoid.'}}}}},
    {   'id': 'case_11_var1',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 71, 'gender': 'male', 'location': 'Suburban area, Karnataka'},
        'hidden_diagnosis': 'stroke',
        'budget': 11,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 2,
                          'chest_auscultation': 1,
                          'bp_measurement': 1,
                          'pulse_oximeter': 2},
        'relevant_tests': ['bp_measurement', 'skin_examination'],
        'conclusive_test': 'skin_examination',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Stroke Unit)',
        'critical_window_days': 1,
        'penalty_events': {   'delayed_referral_beyond_thrombolysis_window': -1.03,
                              'budget_exhausted': -0.48,
                              'duplicate_test': -0.11},
        'daily_progression': {   '1': {   'symptoms': [   'Patient reports confusion',
                                                          'Patient reports sudden weakness in right arm and leg',
                                                          'Patient reports slurred speech',
                                                          'Patient reports facial droop on right side'],
                                          'vitals': {'temp': '37.0 C', 'bp': '182/112', 'hr': 84, 'spo2': '95%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.9 C (Afebrile)',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'febrile_seizure',
                                                                                                        'meningitis'],
                                                                                       'memory_note': 'Afebrile 36.9C; '
                                                                                                      'infective '
                                                                                                      'neurological '
                                                                                                      'cause such as '
                                                                                                      'meningitis or '
                                                                                                      'febrile seizure '
                                                                                                      'excluded.'},
                                                              'skin_examination': {   'result': 'Finding: Right-sided '
                                                                                                'facial paralysis, 0/5 '
                                                                                                'motor strength right '
                                                                                                'extremities',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'stroke',
                                                                                                      'ischaemic_stroke'],
                                                                                      'rules_out': [   'bell_palsy',
                                                                                                       'hypoglycemia_seizure'],
                                                                                      'memory_note': 'URGENT: Complete '
                                                                                                     'right hemiplegia '
                                                                                                     'with upper motor '
                                                                                                     'neuron facial '
                                                                                                     'droop — stroke '
                                                                                                     'pattern '
                                                                                                     'diagnostically '
                                                                                                     'verified. Within '
                                                                                                     'thrombolysis '
                                                                                                     'window — '
                                                                                                     'immediate '
                                                                                                     'referral '
                                                                                                     'required.'},
                                                              'chest_auscultation': {   'result': 'Clinical '
                                                                                                  'observation: Within '
                                                                                                  'Expected Limits '
                                                                                                  'heart sounds; no '
                                                                                                  'added sounds',
                                                                                        'info_gain': 0.0,
                                                                                        'suggests': [],
                                                                                        'rules_out': [   'pneumonia',
                                                                                                         'pulmonary_oedema'],
                                                                                        'memory_note': 'Assessment '
                                                                                                       'notes: Chest '
                                                                                                       'clear; '
                                                                                                       'pulmonary '
                                                                                                       'complication '
                                                                                                       'and aspiration '
                                                                                                       'pneumonia not '
                                                                                                       'yet present.'},
                                                              'bp_measurement': {   'result': 'Status: 185/110 mmHg '
                                                                                              '(Hypertensive '
                                                                                              'Emergency)',
                                                                                    'info_gain': 0.36,
                                                                                    'suggests': [   'stroke',
                                                                                                    'hypertensive_emergency'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Finding: '
                                                                                                   'Hypertensive '
                                                                                                   'emergency 185/110; '
                                                                                                   'raised BP '
                                                                                                   'consistent with '
                                                                                                   'haemorrhagic or '
                                                                                                   'ischaemic stroke '
                                                                                                   'aetiology.'},
                                                              'pulse_oximeter': {   'result': 'Clinical observation: '
                                                                                              'SpO2 97%, PR 88 bpm',
                                                                                    'info_gain': 0.12,
                                                                                    'suggests': [],
                                                                                    'rules_out': [   'respiratory_failure'],
                                                                                    'memory_note': 'Finding: SpO2 97%; '
                                                                                                   'no respiratory '
                                                                                                   'compromise from '
                                                                                                   'aspiration at this '
                                                                                                   'stage.'}}}}},
    {   'id': 'case_12_var1',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 29, 'gender': 'female', 'location': 'Hilly terrain, Uttarakhand'},
        'hidden_diagnosis': 'hepatitis_a_or_e',
        'budget': 13,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'abdominal_exam': 1,
                          'urine_dipstick': 1,
                          'blood_panel': 6},
        'relevant_tests': ['skin_examination', 'abdominal_exam', 'urine_dipstick'],
        'conclusive_test': 'skin_examination',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Gastroenterology)',
        'critical_window_days': 7,
        'penalty_events': {   'acute_liver_failure_without_referral': -0.93,
                              'budget_exhausted': -0.45,
                              'duplicate_test': -0.19},
        'daily_progression': {   '1-3': {   'symptoms': [   'mild right upper abdomen pain',
                                                            'dark urine',
                                                            'yellowish discoloration of eyes',
                                                            'nausea',
                                                            'loss of appetite'],
                                            'vitals': {'temp': '37.5 C', 'bp': '114/72', 'hr': 81, 'spo2': '98%'},
                                            'test_results': {   'thermometer_check': {   'result': '37.5 C (Low-grade '
                                                                                                   'fever)',
                                                                                         'info_gain': 0.12,
                                                                                         'suggests': [   'hepatitis',
                                                                                                         'viral_infection'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Finding: '
                                                                                                        'slight '
                                                                                                        'elevated temp '
                                                                                                        '37.5C; viral '
                                                                                                        'hepatitis '
                                                                                                        'prodromal '
                                                                                                        'elevated temp '
                                                                                                        'pattern.'},
                                                                'skin_examination': {   'result': 'Recorded: '
                                                                                                  'Pronounced icterus '
                                                                                                  '(yellow sclera) and '
                                                                                                  'mild generalised '
                                                                                                  'jaundice',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': [   'hepatitis_a',
                                                                                                        'hepatitis_e',
                                                                                                        'hepatitis_b'],
                                                                                        'rules_out': [   'malaria',
                                                                                                         'dengue'],
                                                                                        'memory_note': 'Status: '
                                                                                                       'Icteric '
                                                                                                       'sclerae and '
                                                                                                       'jaundice '
                                                                                                       'established — '
                                                                                                       'viral '
                                                                                                       'hepatitis '
                                                                                                       'established. '
                                                                                                       'Post-flood '
                                                                                                       'context '
                                                                                                       'indicates '
                                                                                                       'Hepatitis A or '
                                                                                                       'E. Referral '
                                                                                                       'indicated.'},
                                                                'abdominal_exam': {   'result': 'Tender hepatomegaly',
                                                                                      'info_gain': 0.35,
                                                                                      'suggests': [   'hepatitis',
                                                                                                      'hepatitis_a_or_e'],
                                                                                      'rules_out': ['cirrhosis'],
                                                                                      'memory_note': 'Tender '
                                                                                                     'hepatomegaly '
                                                                                                     'consistent with '
                                                                                                     'acute viral '
                                                                                                     'hepatitis; '
                                                                                                     'non-cirrhotic '
                                                                                                     'pattern.'},
                                                                'urine_dipstick': {   'result': 'Bilirubin +++, '
                                                                                                'Urobilinogen Normal',
                                                                                      'info_gain': 0.33,
                                                                                      'suggests': [   'hepatitis',
                                                                                                      'hepatocellular_jaundice'],
                                                                                      'rules_out': [   'obstructive_jaundice',
                                                                                                       'pre_hepatic_jaundice'],
                                                                                      'memory_note': 'Bilirubinuria '
                                                                                                     'with '
                                                                                                     'unremarkable '
                                                                                                     'urobilinogen; '
                                                                                                     'pre-hepatic '
                                                                                                     'jaundice ruled '
                                                                                                     'out, '
                                                                                                     'hepatocellular '
                                                                                                     'pattern '
                                                                                                     'consistent with '
                                                                                                     'hepatitis.'},
                                                                'blood_panel': {   'result': 'WBC 5,200/mcL (normal), '
                                                                                             'Hb 12.1 g/dL, raised '
                                                                                             'transaminases (clinical '
                                                                                             'estimate)',
                                                                                   'info_gain': 0.31,
                                                                                   'suggests': ['viral_hepatitis'],
                                                                                   'rules_out': ['bacterial_sepsis'],
                                                                                   'memory_note': 'Clinical '
                                                                                                  'observation: Benign '
                                                                                                  'leukocyte count; '
                                                                                                  'bacterial sepsis '
                                                                                                  'ruled out. Clinical '
                                                                                                  'picture supports '
                                                                                                  'acute viral '
                                                                                                  'hepatitis.'}}},
                                 '4-7': {   'symptoms': [   'Patient reports clay-colored stools',
                                                            'Patient reports deepening jaundice',
                                                            'Patient reports intense itching (pruritus)',
                                                            'Patient reports severe fatigue'],
                                            'vitals': {'temp': '36.9 C', 'bp': '108/63', 'hr': 72, 'spo2': '99%'},
                                            'test_results': {   'thermometer_check': {   'result': 'Assessment notes: '
                                                                                                   '37.2 C (Subsiding '
                                                                                                   'febrile state)',
                                                                                         'info_gain': 0.22,
                                                                                         'suggests': ['hepatitis'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Recorded: '
                                                                                                        'Subsiding '
                                                                                                        'pyrexia; '
                                                                                                        'typical viral '
                                                                                                        'hepatitis '
                                                                                                        'pattern — '
                                                                                                        'progressing '
                                                                                                        'jaundice '
                                                                                                        'despite '
                                                                                                        'improving '
                                                                                                        'pyrexia.'},
                                                                'skin_examination': {   'result': 'Finding: Deep '
                                                                                                  'icterus, scratch '
                                                                                                  'marks from pruritus',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': [   'hepatitis_a_or_e',
                                                                                                        'cholestatic_component'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'URGENT: '
                                                                                                       'Deepening '
                                                                                                       'jaundice with '
                                                                                                       'pruritic '
                                                                                                       'scratch marks '
                                                                                                       '— escalating '
                                                                                                       'cholestatic '
                                                                                                       'component. '
                                                                                                       'Refer for LFT '
                                                                                                       'monitoring and '
                                                                                                       'IV support.'},
                                                                'abdominal_exam': {   'result': 'Marked tender '
                                                                                                'hepatomegaly',
                                                                                      'info_gain': 0.46,
                                                                                      'suggests': [   'hepatitis_worsening',
                                                                                                      'hepatitis_a_or_e'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Deteriorating '
                                                                                                     'hepatomegaly and '
                                                                                                     'tenderness; '
                                                                                                     'escalating '
                                                                                                     'hepatic '
                                                                                                     'inflammation — '
                                                                                                     'acute liver '
                                                                                                     'failure risk '
                                                                                                     'rising.'},
                                                                'urine_dipstick': {   'result': 'Bilirubin +++, '
                                                                                                'Urobilinogen Absent',
                                                                                      'info_gain': 0.46,
                                                                                      'suggests': [   'obstructive_hepatitis',
                                                                                                      'cholestasis'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'URGENT: Absent '
                                                                                                     'urobilinogen '
                                                                                                     'with persistent '
                                                                                                     'bilirubinuria — '
                                                                                                     'cholestatic '
                                                                                                     'jaundice '
                                                                                                     'emerging, '
                                                                                                     'worsening '
                                                                                                     'hepatocellular '
                                                                                                     'damage.'},
                                                                'blood_panel': {   'result': 'Hb 10.5 g/dL (falling), '
                                                                                             'WBC 4,800/mcL, '
                                                                                             'deteriorating '
                                                                                             'transaminases',
                                                                                   'info_gain': 0.39,
                                                                                   'suggests': [   'hepatitis_worsening',
                                                                                                   'acute_liver_failure_risk'],
                                                                                   'rules_out': [],
                                                                                   'memory_note': 'Worsening anaemia '
                                                                                                  'and escalating '
                                                                                                  'hepatic markers — '
                                                                                                  'progressive liver '
                                                                                                  'disease. critical '
                                                                                                  'referral for '
                                                                                                  'specialist '
                                                                                                  'management.'}}}}},
    {   'id': 'case_13_var1',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 15, 'gender': 'female', 'location': 'Coastal village, Kerala'},
        'hidden_diagnosis': 'asthma',
        'budget': 8,
        'test_costs': {   'thermometer_check': 2,
                          'skin_examination': 1,
                          'bp_measurement': 1,
                          'chest_auscultation': 1,
                          'pulse_oximeter': 2},
        'relevant_tests': ['chest_auscultation', 'pulse_oximeter'],
        'conclusive_test': 'chest_auscultation',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 2,
        'penalty_events': {'silent_chest_without_referral': -0.93, 'budget_exhausted': -0.48, 'duplicate_test': -0.25},
        'daily_progression': {   '1': {   'symptoms': [   'Patient reports episodic shortness of breath',
                                                          'Patient reports chest tightness',
                                                          'Patient reports dry cough worse at night'],
                                          'vitals': {'temp': '36.8 C', 'bp': '120/78', 'hr': 91, 'spo2': '95%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.8 C (Afebrile)',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'infective_bronchitis',
                                                                                                        'pneumonia'],
                                                                                       'memory_note': 'Afebrile; '
                                                                                                      'infective '
                                                                                                      'bronchitis and '
                                                                                                      'pneumonia as '
                                                                                                      'primary cause '
                                                                                                      'less likely.'},
                                                              'skin_examination': {   'result': 'Assessment notes: '
                                                                                                'Mild eczematous '
                                                                                                'changes on forearm; '
                                                                                                'no rash',
                                                                                      'info_gain': 0.19,
                                                                                      'suggests': [   'asthma',
                                                                                                      'atopic_disease'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Eczematous skin '
                                                                                                     'changes; atopic '
                                                                                                     'triad '
                                                                                                     '(asthma/eczema/rhinitis) '
                                                                                                     'noted — supports '
                                                                                                     'allergic asthma '
                                                                                                     'assessment.'},
                                                              'bp_measurement': {   'result': 'Assessment notes: '
                                                                                              '115/75 mmHg (Within '
                                                                                              'Expected Limits)',
                                                                                    'info_gain': 0.0,
                                                                                    'suggests': [],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Provider note: BP '
                                                                                                   'normal; '
                                                                                                   'cardiovascular '
                                                                                                   'cause of '
                                                                                                   'breathlessness '
                                                                                                   'unlikely.'},
                                                              'chest_auscultation': {   'result': 'Provider note: '
                                                                                                  'Bilateral '
                                                                                                  'widespread '
                                                                                                  'polyphonic wheeze '
                                                                                                  'on expiration',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': ['asthma'],
                                                                                        'rules_out': [   'copd',
                                                                                                         'cardiac_failure'],
                                                                                        'memory_note': 'Polyphonic '
                                                                                                       'expiratory '
                                                                                                       'wheeze '
                                                                                                       'bilaterally — '
                                                                                                       'bronchospasm '
                                                                                                       'confirmed; '
                                                                                                       'asthma '
                                                                                                       'assessment '
                                                                                                       'established. '
                                                                                                       'Initiate '
                                                                                                       'salbutamol '
                                                                                                       'inhaler.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 95%, PR 95 bpm',
                                                                                    'info_gain': 0.31,
                                                                                    'suggests': [   'asthma',
                                                                                                    'moderate_asthma'],
                                                                                    'rules_out': ['severe_attack'],
                                                                                    'memory_note': 'SpO2 95% with '
                                                                                                   'low-intensity '
                                                                                                   'tachycardia; '
                                                                                                   'moderate asthma '
                                                                                                   'attack, not yet '
                                                                                                   'life-threatening.'}}},
                                 '2': {   'symptoms': [   'severe breathlessness',
                                                          'use of accessory muscles to breathe',
                                                          'silent chest',
                                                          'inability to complete sentences'],
                                          'vitals': {'temp': '37.2 C', 'bp': '124/88', 'hr': 115, 'spo2': '90%'},
                                          'test_results': {   'thermometer_check': {   'result': '36.9 C (Afebrile)',
                                                                                       'info_gain': 0.15,
                                                                                       'suggests': [],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Clinical '
                                                                                                      'observation: '
                                                                                                      'Persistently '
                                                                                                      'afebrile; no '
                                                                                                      'infective '
                                                                                                      'exacerbation '
                                                                                                      'trigger '
                                                                                                      'identified.'},
                                                              'skin_examination': {   'result': 'Eczema unchanged; '
                                                                                                'accessory muscle use '
                                                                                                'visible',
                                                                                      'info_gain': 0.31,
                                                                                      'suggests': ['asthma'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Atopic '
                                                                                                     'background '
                                                                                                     'unchanged; '
                                                                                                     'visible '
                                                                                                     'accessory muscle '
                                                                                                     'use confirms '
                                                                                                     'intense '
                                                                                                     'respiratory '
                                                                                                     'effort.'},
                                                              'bp_measurement': {   'result': 'Status: 125/85 mmHg '
                                                                                              '(Mildly elevated)',
                                                                                    'info_gain': 0.11,
                                                                                    'suggests': [],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Provider note: '
                                                                                                   'Mildly elevated '
                                                                                                   'BP; likely anxiety '
                                                                                                   'and respiratory '
                                                                                                   'distress response, '
                                                                                                   'non-diagnostic.'},
                                                              'chest_auscultation': {   'result': 'Assessment notes: '
                                                                                                  'Decreased air entry '
                                                                                                  'globally; absent '
                                                                                                  'wheeze (silent '
                                                                                                  'chest — medical '
                                                                                                  'emergency)',
                                                                                        'info_gain': 1.0,
                                                                                        'suggests': [   'severe_asthma',
                                                                                                        'life_threatening_asthma'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'URGENT: Silent '
                                                                                                       'chest — absent '
                                                                                                       'wheeze '
                                                                                                       'indicates '
                                                                                                       'near-complete '
                                                                                                       'airway '
                                                                                                       'obstruction. '
                                                                                                       'Life-threatening '
                                                                                                       'asthma attack. '
                                                                                                       'Immediate '
                                                                                                       'referral '
                                                                                                       'mandatory.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 89%, PR 120 bpm',
                                                                                    'info_gain': 0.4,
                                                                                    'suggests': [   'severe_asthma',
                                                                                                    'respiratory_failure'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'URGENT: SpO2 '
                                                                                                   'fallen to 89% with '
                                                                                                   'escalating rapid '
                                                                                                   'pulse — impending '
                                                                                                   'respiratory '
                                                                                                   'failure. Immediate '
                                                                                                   'oxygen and '
                                                                                                   'referral.'}}}}},
    {   'id': 'case_14_var1',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 39, 'gender': 'male', 'location': 'Forest fringes, Chhattisgarh'},
        'hidden_diagnosis': 'lymphatic_filariasis',
        'budget': 18,
        'test_costs': {   'thermometer_check': 2,
                          'bp_measurement': 1,
                          'urine_dipstick': 3,
                          'skin_examination': 2,
                          'blood_panel': 6},
        'relevant_tests': ['skin_examination', 'blood_panel'],
        'conclusive_test': 'skin_examination',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Filariae Control Programme)',
        'critical_window_days': 30,
        'penalty_events': {   'missed_referral_for_dec_therapy': -0.97,
                              'budget_exhausted': -0.57,
                              'duplicate_test': -0.23},
        'daily_progression': {   '1-30': {   'symptoms': [   'Patient reports heaviness while walking',
                                                             'Patient reports thickening of skin on leg',
                                                             'Patient reports massive painless swelling of left leg'],
                                             'vitals': {'temp': '36.9 C', 'bp': '121/82', 'hr': 77, 'spo2': '99%'},
                                             'test_results': {   'thermometer_check': {   'result': 'Finding: 37.1 C '
                                                                                                    '(Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'cellulitis',
                                                                                                           'acute_infection'],
                                                                                          'memory_note': 'Afebrile; '
                                                                                                         'acute '
                                                                                                         'infective '
                                                                                                         'cellulitis '
                                                                                                         'eliminated '
                                                                                                         'as sole '
                                                                                                         'cause of '
                                                                                                         'limb '
                                                                                                         'swelling.'},
                                                                 'bp_measurement': {   'result': 'Clinical '
                                                                                                 'observation: 125/80 '
                                                                                                 'mmHg (Within '
                                                                                                 'Expected Limits)',
                                                                                       'info_gain': 0.0,
                                                                                       'suggests': [],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Recorded: BP '
                                                                                                      'benign; '
                                                                                                      'cardiovascular '
                                                                                                      'cause of oedema '
                                                                                                      'less likely.'},
                                                                 'urine_dipstick': {   'result': 'Unremarkable; '
                                                                                                 'Protein Not '
                                                                                                 'Detected, Glucose '
                                                                                                 'Non-Reactive',
                                                                                       'info_gain': 0.02,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'nephrotic_syndrome',
                                                                                                        'renal_disease'],
                                                                                       'memory_note': 'Status: '
                                                                                                      'Urinalysis '
                                                                                                      'benign; renal '
                                                                                                      'causes of '
                                                                                                      'oedema such as '
                                                                                                      'nephrotic '
                                                                                                      'syndrome ruled '
                                                                                                      'out.'},
                                                                 'skin_examination': {   'result': 'Non-pitting edema '
                                                                                                   'of left lower '
                                                                                                   'extremity, '
                                                                                                   'hyperkeratosis '
                                                                                                   '(elephantiasis)',
                                                                                         'info_gain': 1.0,
                                                                                         'suggests': [   'lymphatic_filariasis',
                                                                                                         'elephantiasis'],
                                                                                         'rules_out': [   'deep_vein_thrombosis',
                                                                                                          'cardiac_oedema'],
                                                                                         'memory_note': 'Status: '
                                                                                                        'Non-pitting '
                                                                                                        'elephantiasis '
                                                                                                        'with '
                                                                                                        'hyperkeratosis '
                                                                                                        '— '
                                                                                                        'pathognomonic '
                                                                                                        'of advanced '
                                                                                                        'lymphatic '
                                                                                                        'filariasis. '
                                                                                                        'Refer for DEC '
                                                                                                        'therapy.'},
                                                                 'blood_panel': {   'result': 'Assessment notes: '
                                                                                              'Eosinophilia 12%, Hb '
                                                                                              '11.5 g/dL, WBC '
                                                                                              '7,800/mcL',
                                                                                    'info_gain': 0.37,
                                                                                    'suggests': [   'filariasis',
                                                                                                    'parasitic_infection'],
                                                                                    'rules_out': [   'bacterial_infection'],
                                                                                    'memory_note': 'Finding: '
                                                                                                   'Eosinophilia 12% '
                                                                                                   'supports '
                                                                                                   'helminthic/parasitic '
                                                                                                   'infection; '
                                                                                                   'consistent with '
                                                                                                   'lymphatic '
                                                                                                   'filariasis in '
                                                                                                   'endemic zone.'}}}}},
    {   'id': 'case_15_var1',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 28, 'gender': 'female', 'location': 'Rural Village, UP'},
        'hidden_diagnosis': 'leprosy',
        'budget': 13,
        'test_costs': {'thermometer_check': 1, 'urine_dipstick': 3, 'skin_examination': 2, 'blood_panel': 5},
        'relevant_tests': ['skin_examination'],
        'conclusive_test': 'skin_examination',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Leprosy Control Unit)',
        'critical_window_days': 45,
        'penalty_events': {'missed_mdt_initiation': -0.95, 'budget_exhausted': -0.43, 'duplicate_test': -0.18},
        'daily_progression': {   '1-45': {   'symptoms': [   'Patient reports painless ulcers on feet',
                                                             'Patient reports loss of sensation over the patches',
                                                             'Patient reports light colored patches on back',
                                                             'Patient reports weakness in gripping objects'],
                                             'vitals': {'temp': '36.9 C', 'bp': '123/79', 'hr': 85, 'spo2': '99%'},
                                             'test_results': {   'thermometer_check': {   'result': '37.0 C (Afebrile)',
                                                                                          'info_gain': 0.0,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'acute_infection'],
                                                                                          'memory_note': 'Finding: '
                                                                                                         'Afebrile; '
                                                                                                         'acute '
                                                                                                         'febrile '
                                                                                                         'illness '
                                                                                                         'ruled out. '
                                                                                                         'Chronic '
                                                                                                         'insidious '
                                                                                                         'onset '
                                                                                                         'diagnostically '
                                                                                                         'verified.'},
                                                                 'urine_dipstick': {   'result': 'Provider note: '
                                                                                                 'Unremarkable; '
                                                                                                 'Glucose Negative, '
                                                                                                 'Protein Absent',
                                                                                       'info_gain': 0.02,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'renal_disease',
                                                                                                        'diabetes'],
                                                                                       'memory_note': 'Assessment '
                                                                                                      'notes: '
                                                                                                      'Urinalysis '
                                                                                                      'benign; renal '
                                                                                                      'and diabetic '
                                                                                                      'neuropathy as '
                                                                                                      'alternative '
                                                                                                      'cause ruled '
                                                                                                      'out.'},
                                                                 'skin_examination': {   'result': 'Assessment notes: '
                                                                                                   'Multiple '
                                                                                                   'hypopigmented '
                                                                                                   'macules on trunk '
                                                                                                   'with complete '
                                                                                                   'anesthesia to '
                                                                                                   'touch and '
                                                                                                   'pinprick; '
                                                                                                   'thickened ulnar '
                                                                                                   'nerve palpated',
                                                                                         'info_gain': 1.0,
                                                                                         'suggests': [   'leprosy',
                                                                                                         'borderline_leprosy'],
                                                                                         'rules_out': [   'tinea_versicolor',
                                                                                                          'vitiligo'],
                                                                                         'memory_note': 'Hypopigmented '
                                                                                                        'anaesthetic '
                                                                                                        'macules with '
                                                                                                        'thickened '
                                                                                                        'peripheral '
                                                                                                        'nerve — '
                                                                                                        'pathognomonic '
                                                                                                        'triad of '
                                                                                                        'leprosy. MDT '
                                                                                                        'regimen and '
                                                                                                        'referral '
                                                                                                        'required.'},
                                                                 'blood_panel': {   'result': 'Minor eosinophilia 8%, '
                                                                                              'Hb 11.8 g/dL, WBC '
                                                                                              '6,500/mcL',
                                                                                    'info_gain': 0.14,
                                                                                    'suggests': [   'parasitic_or_granulomatous_infection'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Mild eosinophilia; '
                                                                                                   'non-specific for '
                                                                                                   'leprosy but '
                                                                                                   'consistent with '
                                                                                                   'long-standing '
                                                                                                   'granulomatous '
                                                                                                   'infectious '
                                                                                                   'process.'}}}}},
    {   'id': 'case_16_var1',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 57, 'gender': 'female', 'location': 'Remote hamlet, Odisha'},
        'hidden_diagnosis': 'cervical_cancer',
        'budget': 12,
        'test_costs': {   'thermometer_check': 1,
                          'bp_measurement': 1,
                          'urine_dipstick': 3,
                          'abdominal_exam': 2,
                          'hemoglobin_strip': 4},
        'relevant_tests': ['abdominal_exam', 'hemoglobin_strip'],
        'conclusive_test': 'abdominal_exam',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Gynaecological Oncology)',
        'critical_window_days': 14,
        'penalty_events': {'missed_malignancy_referral': -1.03, 'budget_exhausted': -0.43, 'duplicate_test': -0.11},
        'daily_progression': {   '1-14': {   'symptoms': [   'severe fatigue',
                                                             'irregular vaginal bleeding',
                                                             'foul-smelling vaginal discharge',
                                                             'pelvic pain',
                                                             'weight loss'],
                                             'vitals': {'temp': '37.0 C', 'bp': '107/66', 'hr': 94, 'spo2': '96%'},
                                             'test_results': {   'thermometer_check': {   'result': '37.2 C (mild '
                                                                                                    'pyrexia)',
                                                                                          'info_gain': 0.04,
                                                                                          'suggests': [   'infection',
                                                                                                          'cancer_associated_fever'],
                                                                                          'rules_out': [],
                                                                                          'memory_note': 'slight '
                                                                                                         'pyrexia; may '
                                                                                                         'indicate '
                                                                                                         'associated '
                                                                                                         'pelvic '
                                                                                                         'infection or '
                                                                                                         'tumour '
                                                                                                         'necrosis.'},
                                                                 'bp_measurement': {   'result': '105/65 mmHg '
                                                                                                 '(Reduced)',
                                                                                       'info_gain': 0.08,
                                                                                       'suggests': [   'anaemia',
                                                                                                       'haemorrhage'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Clinical '
                                                                                                      'observation: '
                                                                                                      'Low BP '
                                                                                                      'consistent with '
                                                                                                      'significant '
                                                                                                      'haematic fluid '
                                                                                                      'loss from '
                                                                                                      'chronic vaginal '
                                                                                                      'bleeding.'},
                                                                 'urine_dipstick': {   'result': 'Provider note: Blood '
                                                                                                 'Trace, Protein Trace',
                                                                                       'info_gain': 0.22,
                                                                                       'suggests': [   'cervical_cancer',
                                                                                                       'bladder_involvement'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Trace '
                                                                                                      'haematuria may '
                                                                                                      'indicate tumour '
                                                                                                      'invasion to '
                                                                                                      'bladder — '
                                                                                                      'cervical cancer '
                                                                                                      'local extension '
                                                                                                      'suspected.'},
                                                                 'abdominal_exam': {   'result': 'Hard, fixed, '
                                                                                                 'irregular suprapubic '
                                                                                                 'mass palpated',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': [   'cervical_cancer',
                                                                                                       'pelvic_malignancy'],
                                                                                       'rules_out': [   'fibroid',
                                                                                                        'ovarian_cyst_benign'],
                                                                                       'memory_note': 'Hard, fixed, '
                                                                                                      'irregular '
                                                                                                      'suprapubic mass '
                                                                                                      '— highly '
                                                                                                      'suspicious for '
                                                                                                      'advanced pelvic '
                                                                                                      'malignancy. '
                                                                                                      'critical '
                                                                                                      'referral to '
                                                                                                      'gynaecological '
                                                                                                      'oncology.'},
                                                                 'hemoglobin_strip': {   'result': 'Provider note: 8.5 '
                                                                                                   'g/dL (Significant '
                                                                                                   'Anaemia)',
                                                                                         'info_gain': 0.28,
                                                                                         'suggests': [   'anaemia_of_chronic_disease',
                                                                                                         'haemorrhagic_anaemia'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Haemoglobin '
                                                                                                        '8.5 g/dL; '
                                                                                                        'significant '
                                                                                                        'anaemia from '
                                                                                                        'persistent '
                                                                                                        'haematic '
                                                                                                        'fluid loss '
                                                                                                        'consistent '
                                                                                                        'with cervical '
                                                                                                        'malignancy.'}}}}},
    {   'id': 'case_17_var1',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 64, 'gender': 'female', 'location': 'River island, Majuli'},
        'hidden_diagnosis': 'chronic_kidney_disease',
        'budget': 17,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 1,
                          'bp_measurement': 2,
                          'pulse_oximeter': 1,
                          'urine_dipstick': 3,
                          'blood_panel': 5},
        'relevant_tests': ['bp_measurement', 'urine_dipstick', 'skin_examination'],
        'conclusive_test': 'urine_dipstick',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Nephrology)',
        'critical_window_days': 10,
        'penalty_events': {   'uraemia_without_dialysis_referral': -0.96,
                              'budget_exhausted': -0.49,
                              'duplicate_test': -0.11},
        'daily_progression': {   '1-5': {   'symptoms': [   'nausea',
                                                            'decreased urine output',
                                                            'swelling in legs and face',
                                                            'fatigue'],
                                            'vitals': {'temp': '36.8 C', 'bp': '163/98', 'hr': 83, 'spo2': '95%'},
                                            'test_results': {   'thermometer_check': {   'result': 'Recorded: 36.8 C '
                                                                                                   '(Afebrile)',
                                                                                         'info_gain': 0.0,
                                                                                         'suggests': [],
                                                                                         'rules_out': ['infection'],
                                                                                         'memory_note': 'Afebrile; '
                                                                                                        'infective '
                                                                                                        'cause of '
                                                                                                        'oedema '
                                                                                                        'removed from '
                                                                                                        'consideration.'},
                                                                'skin_examination': {   'result': 'Bilateral pitting '
                                                                                                  'edema up to knees, '
                                                                                                  'periorbital '
                                                                                                  'puffiness',
                                                                                        'info_gain': 0.44,
                                                                                        'suggests': [   'chronic_kidney_disease',
                                                                                                        'nephrotic_syndrome',
                                                                                                        'cardiac_failure'],
                                                                                        'rules_out': [],
                                                                                        'memory_note': 'Bilateral '
                                                                                                       'pitting oedema '
                                                                                                       'with '
                                                                                                       'periorbital '
                                                                                                       'puffiness; '
                                                                                                       'nephrotic/renal '
                                                                                                       'syndrome '
                                                                                                       'pattern — CKD '
                                                                                                       'workup '
                                                                                                       'indicated.'},
                                                                'bp_measurement': {   'result': '165/100 mmHg',
                                                                                      'info_gain': 0.34,
                                                                                      'suggests': [   'chronic_kidney_disease',
                                                                                                      'renal_hypertension'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Hypertension '
                                                                                                     '165/100; renal '
                                                                                                     'hypertension '
                                                                                                     'pattern in '
                                                                                                     'context of '
                                                                                                     'oedema and '
                                                                                                     'proteinuria.'},
                                                                'pulse_oximeter': {   'result': 'Finding: SpO2 97%, PR '
                                                                                                '85 bpm',
                                                                                      'info_gain': 0.0,
                                                                                      'suggests': [],
                                                                                      'rules_out': [   'severe_cardiac_failure',
                                                                                                       'respiratory_failure'],
                                                                                      'memory_note': 'Status: SpO2 '
                                                                                                     '97%; no '
                                                                                                     'significant '
                                                                                                     'respiratory '
                                                                                                     'compromise at '
                                                                                                     'this stage.'},
                                                                'urine_dipstick': {   'result': 'Protein +++, Vascular '
                                                                                                'Trace',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'chronic_kidney_disease',
                                                                                                      'nephrotic_syndrome'],
                                                                                      'rules_out': [   'cardiac_oedema',
                                                                                                       'hepatic_oedema'],
                                                                                      'memory_note': 'Provider note: '
                                                                                                     'Massive '
                                                                                                     'proteinuria '
                                                                                                     '(Protein +++) — '
                                                                                                     'renal origin of '
                                                                                                     'oedema proven. '
                                                                                                     'CKD likely. '
                                                                                                     'Immediate '
                                                                                                     'referral to '
                                                                                                     'District '
                                                                                                     'Hospital '
                                                                                                     'required.'},
                                                                'blood_panel': {   'result': 'Hb 9.5 g/dL, WBC '
                                                                                             '6,200/mcL, elevated '
                                                                                             'creatinine (clinical '
                                                                                             'estimate)',
                                                                                   'info_gain': 0.44,
                                                                                   'suggests': [   'chronic_kidney_disease',
                                                                                                   'renal_anaemia'],
                                                                                   'rules_out': [],
                                                                                   'memory_note': 'Finding: Normocytic '
                                                                                                  'anaemia consistent '
                                                                                                  'with CKD-associated '
                                                                                                  'erythropoietin '
                                                                                                  'deficiency; renal '
                                                                                                  'origin '
                                                                                                  'confirmed.'}}},
                                 '6-10': {   'symptoms': [   'Patient reports vomiting',
                                                             'Patient reports muscle twitches',
                                                             'Patient reports confusion (uremia)',
                                                             'Patient reports severe shortness of breath (fluid '
                                                             'overload)'],
                                             'vitals': {'temp': '36.2 C', 'bp': '180/113', 'hr': 99, 'spo2': '91%'},
                                             'test_results': {   'thermometer_check': {   'result': 'Recorded: 36.5 C '
                                                                                                    '(Subnormal)',
                                                                                          'info_gain': 0.13,
                                                                                          'suggests': [],
                                                                                          'rules_out': [],
                                                                                          'memory_note': 'Subnormal '
                                                                                                         'temperature; '
                                                                                                         'uraemia '
                                                                                                         'causing '
                                                                                                         'temperature '
                                                                                                         'dysregulation '
                                                                                                         '— escalating '
                                                                                                         'CKD '
                                                                                                         'progression.'},
                                                                 'skin_examination': {   'result': 'Provider note: '
                                                                                                   'Massive anasarca '
                                                                                                   '(generalised '
                                                                                                   'edema), uremic '
                                                                                                   'frost visible',
                                                                                         'info_gain': 0.57,
                                                                                         'suggests': [   'end_stage_renal_disease',
                                                                                                         'uraemia'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'URGENT: '
                                                                                                        'Uremic frost '
                                                                                                        'and anasarca '
                                                                                                        '— end-stage '
                                                                                                        'renal '
                                                                                                        'failure. '
                                                                                                        'Immediate '
                                                                                                        'dialysis-capable '
                                                                                                        'referral '
                                                                                                        'mandatory.'},
                                                                 'bp_measurement': {   'result': '180/110 mmHg '
                                                                                                 '(Hypertensive '
                                                                                                 'Emergency)',
                                                                                       'info_gain': 0.39,
                                                                                       'suggests': [   'hypertensive_emergency',
                                                                                                       'ckd_progression'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'URGENT: '
                                                                                                      'Escalating BP '
                                                                                                      'to 180/110 — '
                                                                                                      'hypertensive '
                                                                                                      'emergency from '
                                                                                                      'progressing '
                                                                                                      'CKD. Risk of '
                                                                                                      'hypertensive '
                                                                                                      'encephalopathy.'},
                                                                 'pulse_oximeter': {   'result': 'SpO2 92%, PR 95 bpm',
                                                                                       'info_gain': 0.12,
                                                                                       'suggests': [   'fluid_overload',
                                                                                                       'pulmonary_oedema'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'Escalating SpO2 '
                                                                                                      '92%; pulmonary '
                                                                                                      'oedema from '
                                                                                                      'fluid overload '
                                                                                                      'escalating — '
                                                                                                      'respiratory '
                                                                                                      'compromise now '
                                                                                                      'present.'},
                                                                 'urine_dipstick': {   'result': 'Clinical '
                                                                                                 'observation: Protein '
                                                                                                 '+++, Vascular Trace '
                                                                                                 '(unchanged)',
                                                                                       'info_gain': 1.0,
                                                                                       'suggests': [   'chronic_kidney_disease'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'URGENT: '
                                                                                                      'Persistent '
                                                                                                      'massive '
                                                                                                      'proteinuria — '
                                                                                                      'established CKD '
                                                                                                      'with end-organ '
                                                                                                      'failure '
                                                                                                      'escalating. '
                                                                                                      'Dialysis '
                                                                                                      'referral '
                                                                                                      'critical.'},
                                                                 'blood_panel': {   'result': 'Hb 7.8 g/dL, markedly '
                                                                                              'elevated creatinine, '
                                                                                              'raised potassium '
                                                                                              '(clinical)',
                                                                                    'info_gain': 0.51,
                                                                                    'suggests': [   'end_stage_renal_disease',
                                                                                                    'hyperkalaemia_risk'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'URGENT: '
                                                                                                   'Progressing '
                                                                                                   'anaemia with '
                                                                                                   'rising creatinine '
                                                                                                   'and potassium — '
                                                                                                   'life-threatening '
                                                                                                   'uraemia and '
                                                                                                   'hyperkalaemia '
                                                                                                   'risk.'}}}}},
    {   'id': 'case_18_var1',
        'difficulty_tier': 'hard',
        'patient_demographics': {'age': 28, 'gender': 'male', 'location': 'Rural Village, UP'},
        'hidden_diagnosis': 'kala_azar',
        'budget': 15,
        'test_costs': {   'thermometer_check': 2,
                          'skin_examination': 1,
                          'urine_dipstick': 1,
                          'rapid_malaria_test': 2,
                          'abdominal_exam': 1,
                          'blood_panel': 5},
        'relevant_tests': ['abdominal_exam', 'blood_panel', 'skin_examination'],
        'conclusive_test': 'abdominal_exam',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Kala-Azar Elimination Programme)',
        'critical_window_days': 7,
        'penalty_events': {'missed_referral_for_amb_therapy': -1.05, 'budget_exhausted': -0.59, 'duplicate_test': -0.3},
        'daily_progression': {   '1-7': {   'symptoms': [   'massive swelling in abdomen',
                                                            'fever for 2 months',
                                                            'progressive extreme weight loss',
                                                            'bleeding gums',
                                                            'darkening of skin'],
                                            'vitals': {'temp': '38.3 C', 'bp': '97/56', 'hr': 109, 'spo2': '97%'},
                                            'test_results': {   'thermometer_check': {   'result': 'Clinical '
                                                                                                   'observation: 38.5 '
                                                                                                   'C (Prolonged '
                                                                                                   'pyrexia over 2 '
                                                                                                   'months)',
                                                                                         'info_gain': 0.19,
                                                                                         'suggests': [   'kala_azar',
                                                                                                         'malaria',
                                                                                                         'typhoid'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Finding: '
                                                                                                        'Prolonged '
                                                                                                        'pyrexia 38.5C '
                                                                                                        'over 2 '
                                                                                                        'months; '
                                                                                                        'long-standing '
                                                                                                        'febrile '
                                                                                                        'illness '
                                                                                                        'requiring '
                                                                                                        'systematic '
                                                                                                        'evaluation.'},
                                                                'skin_examination': {   'result': 'Status: '
                                                                                                  'Hyperpigmentation '
                                                                                                  'on hands, feet, '
                                                                                                  'abdomen, and face',
                                                                                        'info_gain': 0.47,
                                                                                        'suggests': [   'kala_azar',
                                                                                                        'visceral_leishmaniasis'],
                                                                                        'rules_out': ['malaria'],
                                                                                        'memory_note': 'Clinical '
                                                                                                       'observation: '
                                                                                                       'Generalised '
                                                                                                       'hyperpigmentation '
                                                                                                       '(kala-azar = '
                                                                                                       'black fever); '
                                                                                                       'highly '
                                                                                                       'characteristic '
                                                                                                       'of visceral '
                                                                                                       'leishmaniasis '
                                                                                                       'in Bihar '
                                                                                                       'endemic zone.'},
                                                                'urine_dipstick': {   'result': 'Protein Trace, '
                                                                                                'Glucose Negative',
                                                                                      'info_gain': 0.0,
                                                                                      'suggests': [],
                                                                                      'rules_out': ['diabetes', 'uti'],
                                                                                      'memory_note': 'Recorded: Trace '
                                                                                                     'proteinuria; '
                                                                                                     'minor renal '
                                                                                                     'irritation. No '
                                                                                                     'alternative '
                                                                                                     'clinical '
                                                                                                     'impression '
                                                                                                     'suggested.'},
                                                                'rapid_malaria_test': {   'result': 'Not Detected',
                                                                                          'info_gain': 0.01,
                                                                                          'suggests': [],
                                                                                          'rules_out': ['malaria'],
                                                                                          'memory_note': 'Malaria '
                                                                                                         'excluded by '
                                                                                                         'RDT; '
                                                                                                         'prolonged '
                                                                                                         'fever with '
                                                                                                         'splenomegaly '
                                                                                                         'is '
                                                                                                         'non-malarial.'},
                                                                'abdominal_exam': {   'result': 'Recorded: Massive '
                                                                                                'splenomegaly crossing '
                                                                                                'umbilicus, firm and '
                                                                                                'non-tender. '
                                                                                                'Hepatomegaly present.',
                                                                                      'info_gain': 1.0,
                                                                                      'suggests': [   'kala_azar',
                                                                                                      'visceral_leishmaniasis'],
                                                                                      'rules_out': [   'malaria',
                                                                                                       'typhoid',
                                                                                                       'lymphoma'],
                                                                                      'memory_note': 'Massive '
                                                                                                     'crossing-umbilicus '
                                                                                                     'splenomegaly — '
                                                                                                     'pathognomonic of '
                                                                                                     'kala-azar in '
                                                                                                     'Bihar endemic '
                                                                                                     'context. '
                                                                                                     'Immediate '
                                                                                                     'referral for '
                                                                                                     'rK39 test and '
                                                                                                     'AmBisome '
                                                                                                     'therapy.'},
                                                                'blood_panel': {   'result': 'Assessment notes: Marked '
                                                                                             'Pancytopenia: Hb 5.5 '
                                                                                             'g/dL, WBC 1,500/mcL, '
                                                                                             'Platelets 45,000/mcL',
                                                                                   'info_gain': 0.48,
                                                                                   'suggests': [   'kala_azar',
                                                                                                   'visceral_leishmaniasis'],
                                                                                   'rules_out': ['dengue_alone'],
                                                                                   'memory_note': 'Marked pancytopenia '
                                                                                                  'with bone marrow '
                                                                                                  'suppression; '
                                                                                                  'strongly supports '
                                                                                                  'visceral '
                                                                                                  'leishmaniasis over '
                                                                                                  'other '
                                                                                                  'diagnoses.'}}}}},
    {   'id': 'case_19_var1',
        'difficulty_tier': 'medium',
        'patient_demographics': {'age': 1, 'gender': 'female', 'location': 'Coastal village, Kerala'},
        'hidden_diagnosis': 'severe_pneumonia_under_5',
        'budget': 12,
        'test_costs': {   'thermometer_check': 1,
                          'skin_examination': 2,
                          'bp_measurement': 2,
                          'chest_auscultation': 1,
                          'pulse_oximeter': 3},
        'relevant_tests': ['pulse_oximeter', 'chest_auscultation', 'thermometer_check'],
        'conclusive_test': 'pulse_oximeter',
        'requires_referral': True,
        'referral_destination': 'District Hospital (Paediatric Ward)',
        'critical_window_days': 1,
        'penalty_events': {'hypoxia_without_referral_child': -1.06, 'budget_exhausted': -0.54, 'duplicate_test': -0.26},
        'daily_progression': {   '1': {   'symptoms': [   'grunting',
                                                          'high fever',
                                                          'lower chest wall indrawing',
                                                          'inability to drink',
                                                          'fast breathing'],
                                          'vitals': {'temp': '39.3 C', 'bp': '91/63', 'hr': 146, 'spo2': '88%'},
                                          'test_results': {   'thermometer_check': {   'result': '39.4 C (Elevated '
                                                                                                 'pyrexia)',
                                                                                       'info_gain': 0.23,
                                                                                       'suggests': [   'pneumonia',
                                                                                                       'malaria',
                                                                                                       'sepsis'],
                                                                                       'rules_out': [],
                                                                                       'memory_note': 'High fever '
                                                                                                      '39.4C in a '
                                                                                                      '2-year-old; '
                                                                                                      'serious '
                                                                                                      'bacterial '
                                                                                                      'infectious '
                                                                                                      'process and '
                                                                                                      'pneumonia in '
                                                                                                      'differential.'},
                                                              'skin_examination': {   'result': 'Status: Central '
                                                                                                'cyanosis of lips; '
                                                                                                'intercostal '
                                                                                                'retractions visible',
                                                                                      'info_gain': 0.44,
                                                                                      'suggests': [   'severe_pneumonia',
                                                                                                      'respiratory_failure'],
                                                                                      'rules_out': [],
                                                                                      'memory_note': 'Status: Central '
                                                                                                     'cyanosis and '
                                                                                                     'chest '
                                                                                                     'retractions — '
                                                                                                     'severe '
                                                                                                     'respiratory '
                                                                                                     'distress in a '
                                                                                                     'child. Pneumonia '
                                                                                                     'with reduced '
                                                                                                     'oxygenation '
                                                                                                     'highly likely.'},
                                                              'bp_measurement': {   'result': '90/60 mmHg (Low for '
                                                                                              'age)',
                                                                                    'info_gain': 0.16,
                                                                                    'suggests': [   'sepsis',
                                                                                                    'severe_illness'],
                                                                                    'rules_out': [],
                                                                                    'memory_note': 'Decreased BP for '
                                                                                                   'age; haemodynamic '
                                                                                                   'compromise '
                                                                                                   'consistent with '
                                                                                                   'severe pneumonia '
                                                                                                   'or sepsis.'},
                                                              'chest_auscultation': {   'result': 'Assessment notes: '
                                                                                                  'Bronchial breath '
                                                                                                  'sounds and rales '
                                                                                                  'over right mid and '
                                                                                                  'lower zones',
                                                                                        'info_gain': 0.51,
                                                                                        'suggests': [   'pneumonia',
                                                                                                        'severe_pneumonia'],
                                                                                        'rules_out': [   'asthma',
                                                                                                         'bronchiolitis'],
                                                                                        'memory_note': 'Right-sided '
                                                                                                       'bronchial '
                                                                                                       'breathing with '
                                                                                                       'crepitations; '
                                                                                                       'lobar '
                                                                                                       'consolidation '
                                                                                                       'consistent '
                                                                                                       'with bacterial '
                                                                                                       'pneumonia '
                                                                                                       'proven.'},
                                                              'pulse_oximeter': {   'result': 'SpO2 89%, PR 150 bpm',
                                                                                    'info_gain': 1.0,
                                                                                    'suggests': [   'severe_pneumonia',
                                                                                                    'hypoxia'],
                                                                                    'rules_out': ['mild_rti'],
                                                                                    'memory_note': 'Status: SpO2 89% '
                                                                                                   'in a child — WHO '
                                                                                                   'marked pneumonia '
                                                                                                   'criteria met. '
                                                                                                   'immediate action '
                                                                                                   'needed referral '
                                                                                                   'for oxygen and IV '
                                                                                                   'antibiotics. '
                                                                                                   'Life-threatening.'}}}}},
    {   'id': 'case_20_var1',
        'difficulty_tier': 'easy',
        'patient_demographics': {'age': 11, 'gender': 'female', 'location': 'Urban slum, Delhi'},
        'hidden_diagnosis': 'intestinal_worms',
        'budget': 15,
        'test_costs': {   'thermometer_check': 1,
                          'urine_dipstick': 2,
                          'skin_examination': 1,
                          'abdominal_exam': 2,
                          'hemoglobin_strip': 5},
        'relevant_tests': ['abdominal_exam', 'hemoglobin_strip'],
        'conclusive_test': 'hemoglobin_strip',
        'requires_referral': False,
        'referral_destination': None,
        'critical_window_days': 14,
        'penalty_events': {'untreated_worm_burden_anaemia': -0.95, 'budget_exhausted': -0.44, 'duplicate_test': -0.17},
        'daily_progression': {   '1-14': {   'symptoms': [   'Patient reports vague abdominal pain',
                                                             'Patient reports fatigue',
                                                             'Patient reports teeth grinding at night',
                                                             "Patient reports passing 'long white worms' in stool",
                                                             'Patient reports poor appetite'],
                                             'vitals': {'temp': '36.9 C', 'bp': '98/69', 'hr': 91, 'spo2': '97%'},
                                             'test_results': {   'thermometer_check': {   'result': 'Recorded: 37.0 C '
                                                                                                    '(Afebrile)',
                                                                                          'info_gain': 0.04,
                                                                                          'suggests': [],
                                                                                          'rules_out': [   'malaria',
                                                                                                           'infection'],
                                                                                          'memory_note': 'Afebrile; '
                                                                                                         'febrile '
                                                                                                         'illness '
                                                                                                         'removed from '
                                                                                                         'consideration. '
                                                                                                         'Helminthic '
                                                                                                         'infestation '
                                                                                                         'is typically '
                                                                                                         'non-pyrexial.'},
                                                                 'urine_dipstick': {   'result': 'Benign; Glucose '
                                                                                                 'Absent, Protein '
                                                                                                 'Negative',
                                                                                       'info_gain': 0.02,
                                                                                       'suggests': [],
                                                                                       'rules_out': [   'uti',
                                                                                                        'diabetes',
                                                                                                        'renal_disease'],
                                                                                       'memory_note': 'Urinalysis '
                                                                                                      'normal; UTI and '
                                                                                                      'renal causes '
                                                                                                      'eliminated.'},
                                                                 'skin_examination': {   'result': 'Status: Mild '
                                                                                                   'pallor in '
                                                                                                   'conjunctiva; no '
                                                                                                   'rash; no oedema',
                                                                                         'info_gain': 0.2,
                                                                                         'suggests': [   'nutritional_anemia',
                                                                                                         'intestinal_worms'],
                                                                                         'rules_out': [],
                                                                                         'memory_note': 'Minor '
                                                                                                        'conjunctival '
                                                                                                        'pallor; '
                                                                                                        'anaemia from '
                                                                                                        'worm-related '
                                                                                                        'malabsorption '
                                                                                                        'and vascular '
                                                                                                        'loss likely.'},
                                                                 'abdominal_exam': {   'result': 'Soft, non-tender, '
                                                                                                 'slight distension',
                                                                                       'info_gain': 0.3,
                                                                                       'suggests': [   'intestinal_worms',
                                                                                                       'malnutrition'],
                                                                                       'rules_out': [   'appendicitis',
                                                                                                        'organomegaly'],
                                                                                       'memory_note': 'Status: '
                                                                                                      'Low-Intensity '
                                                                                                      'abdominal '
                                                                                                      'distension '
                                                                                                      'without '
                                                                                                      'tenderness; '
                                                                                                      'consistent with '
                                                                                                      'intestinal '
                                                                                                      'helminthiasis. '
                                                                                                      'No acute '
                                                                                                      'abdomen.'},
                                                                 'hemoglobin_strip': {   'result': '9.5 g/dL (Moderate '
                                                                                                   'Anaemia)',
                                                                                         'info_gain': 1.0,
                                                                                         'suggests': [   'intestinal_worms',
                                                                                                         'nutritional_deficiency'],
                                                                                         'rules_out': [   'normal_hemoglobin'],
                                                                                         'memory_note': 'Hb 9.5 g/dL — '
                                                                                                        'moderate '
                                                                                                        'anaemia in a '
                                                                                                        'school-age '
                                                                                                        'child with '
                                                                                                        'visible worms '
                                                                                                        'in stool. '
                                                                                                        'Helminthiasis '
                                                                                                        'proven. '
                                                                                                        'Administer '
                                                                                                        'albendazole '
                                                                                                        'and iron '
                                                                                                        'supplementation.'}}}}}]

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
