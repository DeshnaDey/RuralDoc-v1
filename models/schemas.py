"""
models/schemas.py — Pydantic types for MedicalDiagnosisEnv.

Action variants:
    OrderTestAction, DiagnoseAction, ReferAction
    MedicalAction  (discriminated union on "type")

Observation  — returned by reset() and step()["observation"]
State        — returned by state()
StepResult   — returned by step()

Helper:
    action_to_dict(action) -> dict  (plain dict for environment.py)
"""

from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, TypeAdapter


# ── Actions ───────────────────────────────────────────────────────────────────

class OrderTestAction(BaseModel):
    type: Literal["order_test"] = "order_test"
    test_name: str


class DiagnoseAction(BaseModel):
    type: Literal["diagnose"] = "diagnose"
    diagnosis: str


class ReferAction(BaseModel):
    type: Literal["refer"] = "refer"


# Discriminated union — Pydantic picks the right model from the "type" field
MedicalAction = Annotated[
    Union[OrderTestAction, DiagnoseAction, ReferAction],
    Field(discriminator="type"),
]

# TypeAdapter for validating raw dicts into MedicalAction
MedicalActionAdapter = TypeAdapter(MedicalAction)


# ── Observation ───────────────────────────────────────────────────────────────

class Observation(BaseModel):
    patient:          dict             # {age: int, gender: str, location: str}
    symptoms:         list[str]
    vitals:           dict             # {temp: str, bp: str, hr: int, spo2: str}
    available_tests:  list[str]
    status:           Literal["stable", "worsening", "critical"]
    budget_remaining: float
    day:              int
    memory:           list[str]


# ── State ─────────────────────────────────────────────────────────────────────

class State(BaseModel):
    current_day:      int
    budget_remaining: float
    tests_ordered:    list[str]
    referred:         bool
    done:             bool
    scenario_id:      str
    patient_status:   Literal["stable", "worsening", "critical"]


# ── StepResult ────────────────────────────────────────────────────────────────

class StepResult(BaseModel):
    observation: Observation
    reward:      float
    done:        bool
    info:        dict


# ── Helper ────────────────────────────────────────────────────────────────────

def action_to_dict(action: MedicalAction) -> dict:
    """
    Convert a Pydantic action object to the plain dict format
    expected by environment.py's step() method.

    Examples:
        OrderTestAction(test_name="sputum_smear")
            -> {"type": "order_test", "test_name": "sputum_smear"}

        DiagnoseAction(diagnosis="malaria")
            -> {"type": "diagnose", "diagnosis": "malaria"}

        ReferAction()
            -> {"type": "refer"}
    """
    return action.model_dump()
