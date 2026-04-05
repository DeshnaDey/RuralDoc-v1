"""
models.py — Pydantic types for MedicalDiagnosisEnv.

Action variants:
    OrderTestAction, DiagnoseAction, ReferAction
    MedicalAction (discriminated union on "type")

Observation — returned by reset() and step()["observation"]
State — returned by state()
StepResult — returned by step()

Helper:
    action_to_dict(action) -> dict (plain dict for environment.py)
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
    patient: dict           # {age: int, gender: str, location: str}
    symptoms: list[str]
    vitals: dict            # {temp: str, bp: str, hr: int, spo2: str}
    available_tests: list[str]
    status: Literal["stable", "worsening", "critical"]
    budget_remaining: float
    day: int
    memory: list[str]


# ── State ─────────────────────────────────────────────────────────────────────

class State(BaseModel):
    current_day: int
    budget_remaining: float
    tests_ordered: list[str]
    referred: bool
    done: bool
    scenario_id: str
    patient_status: Literal["stable", "worsening", "critical"]


# ── StepResult ────────────────────────────────────────────────────────────────

class StepResult(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: dict


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


# ─────────────────────────────────────────────────────────────────────────────
# Display test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    SEP = "=" * 62

    # 1. Construct one of each action type
    print(f"\n{SEP}")
    print(" Action objects")
    print(SEP)

    order = OrderTestAction(test_name="sputum_smear")
    diag = DiagnoseAction(diagnosis="tuberculosis")
    refer = ReferAction()

    for action in (order, diag, refer):
        print(f"\n  {action.__class__.__name__}: {action}")

    # 2. action_to_dict conversion
    print(f"\n{SEP}")
    print(" action_to_dict -> plain dicts for environment.py")
    print(SEP)

    for action in (order, diag, refer):
        print(f"\n  {action.__class__.__name__} -> {action_to_dict(action)}")

    # 3. Discriminated union round-trip via TypeAdapter
    print(f"\n{SEP}")
    print(" TypeAdapter round-trip (dict -> MedicalAction)")
    print(SEP)

    raw_actions = [
        {"type": "order_test", "test_name": "rapid_malaria_test"},
        {"type": "diagnose", "diagnosis": "malaria"},
        {"type": "refer"},
    ]
    for raw in raw_actions:
        parsed = MedicalActionAdapter.validate_python(raw)
        print(f"\n  input: {raw}")
        print(f"  parsed: {parsed.__class__.__name__}({parsed})")

    # 4. Sample Observation (TB day-1 data)
    print(f"\n{SEP}")
    print(" Sample Observation")
    print(SEP)

    obs = Observation(
        patient={"age": 34, "gender": "male", "location": "Urban slum, Delhi"},
        symptoms=["chronic cough for 3 weeks", "night sweats", "weight loss"],
        vitals={"temp": "37.9 C", "bp": "110/75", "hr": 88, "spo2": "96%"},
        available_tests=["thermometer_check", "chest_auscultation", "sputum_smear"],
        status="stable",
        budget_remaining=24.0,
        day=1,
        memory=[],
    )
    print(f"\n  {obs}")

    # 5. Sample StepResult
    print(f"\n{SEP}")
    print(" Sample StepResult")
    print(SEP)

    result = StepResult(
        observation=obs,
        reward=0.35,
        done=False,
        info={
            "action_taken": {"type": "order_test", "test_name": "chest_auscultation"},
            "tests_ordered": ["chest_auscultation"],
            "referred": False,
            "scenario_id": "case_01",
        },
    )
    print(f"\n  reward={result.reward} done={result.done}")
    print(f"  info={result.info}")
    print(f"  observation.status={result.observation.status}")
    print(f"  observation.budget_remaining={result.observation.budget_remaining}")
    print()
