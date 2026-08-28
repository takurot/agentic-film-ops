"""Canonical Demo Scenario loader and validator (Issue #84, SPEC §2.1, §4, §9.1)."""

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SCENARIO_PATH = _REPO_ROOT / "scenario" / "v1" / "demo_scenario.json"


class ScenarioMeta(BaseModel):
    scenario_id: str
    version: str
    title: str
    description: str = ""


class ScenarioProduction(BaseModel):
    production_day_current: int
    production_day_total: int
    schedule_adherence_percent: float
    budget_spent_usd: float
    budget_total_usd: float
    scenes_completed: int
    scenes_total: int
    overall_risk: str


class ScenarioTodayScene(BaseModel):
    scene_id: str
    name: str
    status: str
    progress_percent: float = 0.0


class ScenarioCostBenefitModel(BaseModel):
    standby_day_penalty_usd: float
    option_a_variance_usd: float
    net_cost_avoided_usd: float
    formula: str
    assumptions: dict[str, Any] = Field(default_factory=dict)


class DemoScenario(BaseModel):
    meta: ScenarioMeta
    production: ScenarioProduction
    today_scenes: list[ScenarioTodayScene]
    resources: dict[str, Any]
    incident: dict[str, Any]
    external_comms: dict[str, Any] = Field(default_factory=dict)
    options: list[dict[str, Any]]
    cost_benefit_model: ScenarioCostBenefitModel
    execution: dict[str, Any]
    stream_events: list[dict[str, Any]] = Field(default_factory=list)


def get_scenario_raw_data(path: Path | str | None = None) -> dict[str, Any]:
    target_path = Path(path or os.getenv("FILMOPS_SCENARIO_PATH", _DEFAULT_SCENARIO_PATH))
    if not target_path.exists():
        # Fallback to local relative lookup if deployed without full repo root
        alt_path = Path(__file__).resolve().parent / "demo_scenario.json"
        if alt_path.exists():
            target_path = alt_path
        else:
            raise FileNotFoundError(f"Demo scenario JSON not found at {target_path}")

    with open(target_path, encoding="utf-8") as f:
        return json.load(f)


def compute_scenario_hash(data: dict[str, Any]) -> str:
    serialized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


@lru_cache(maxsize=1)
def load_demo_scenario(path: Path | str | None = None) -> DemoScenario:
    raw = get_scenario_raw_data(path)
    return DemoScenario.model_validate(raw)


@lru_cache(maxsize=1)
def get_scenario_hash(path: Path | str | None = None) -> str:
    raw = get_scenario_raw_data(path)
    return compute_scenario_hash(raw)
