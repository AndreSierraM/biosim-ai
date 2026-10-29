"""Unit tests: planner logic with fake model clients. Run: python3 services/api/tests/test_planner.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.planner import ModelResponse, plan_prompt

FIXTURES = Path(__file__).parent / "fixtures"


class FakeClient:
    def __init__(self, texts: list[str]):
        self.texts = list(texts)
        self.calls = 0

    def complete(self, system: str, user: str) -> ModelResponse:
        self.calls += 1
        return ModelResponse(text=self.texts.pop(0), model="fake-test-model",
                             tokens_in=10, tokens_out=20, latency_s=0.01)


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_compare_builds_two_validated_arms():
    plan = plan_prompt("how does oxygen availability affect tumor spheroid growth",
                       FakeClient([_fixture("compare.json")]),
                       ["physicell", "reference-2cell"])
    assert plan["validated"] is True, plan
    assert plan["runs_created"] == []
    assert [a["name"] for a in plan["arms"]] == ["normal-oxygen", "low-oxygen"]
    values = []
    for arm in plan["arms"]:
        assert arm["spec"]["engine"] == "physicell"
        q = arm["spec"]["parameters"]["oxygen"]
        assert q["unit"] == "mmHg", "oxygen lacks units"
        values.append(q["value"])
    assert values == [38.0, 12.0], values
    assert plan["model_version"] == "fake-test-model"


def test_unsupported_refuses_without_runs():
    plan = plan_prompt("show me atom-level detail of a whole living cell",
                       FakeClient([_fixture("unsupported.json")]),
                       ["physicell"])
    assert plan["validated"] is False
    assert plan["runs_created"] == []
    assert plan["refusal"]["reason"]


def test_repair_recovers_from_bad_json():
    plan = plan_prompt("compare oxygen",
                       FakeClient(["not json at all", _fixture("compare.json")]),
                       ["physicell"])
    assert plan["validated"] is True
    assert len(plan["arms"]) == 2


def test_swapped_oxygen_normalizes_with_warning():
    text = json.dumps({"kind": "spheroid_oxygen_compare", "engine": "physicell",
                       "oxygen_high": 12.0, "oxygen_low": 38.0})
    plan = plan_prompt("compare oxygen", FakeClient([text]), ["physicell"])
    assert plan["validated"] is True
    vals = [a["spec"]["parameters"]["oxygen"]["value"] for a in plan["arms"]]
    assert vals == [38.0, 12.0], vals
    assert plan["warnings"], "expected normalization warning"


def test_missing_physicell_refuses():
    plan = plan_prompt("compare oxygen",
                       FakeClient([_fixture("compare.json")]),
                       ["reference-2cell"])
    assert plan["validated"] is False
    assert "PhysiCell" in plan["refusal"]["reason"]


def test_drug_compare_builds_control_treated_arms():
    plan = plan_prompt("how does drug dose affect spheroid survival",
                       FakeClient([_fixture("drug.json")]),
                       ["physicell"])
    assert plan["validated"] is True, plan
    assert plan["runs_created"] == []
    assert [a["name"] for a in plan["arms"]] == ["control", "treated"]
    doses = []
    for arm in plan["arms"]:
        assert arm["spec"]["engine"] == "physicell"
        q = arm["spec"]["parameters"]["drug_dose"]
        assert q["unit"] == "uM", "drug dose lacks units"
        doses.append(q["value"])
        assert arm["spec"]["parameters"]["oxygen"]["value"] == 38.0
    assert doses == [0.0, 10.0], doses


def test_bad_dose_refuses():
    text = json.dumps({"kind": "spheroid_drug_compare", "engine": "physicell",
                       "drug_dose": -3.0})
    plan = plan_prompt("drug test", FakeClient([text, text]), ["physicell"])
    assert plan["validated"] is False
    assert "drug_dose" in plan["refusal"]["reason"]
    assert plan["runs_created"] == []


def main() -> int:
    test_compare_builds_two_validated_arms()
    test_unsupported_refuses_without_runs()
    test_repair_recovers_from_bad_json()
    test_swapped_oxygen_normalizes_with_warning()
    test_missing_physicell_refuses()
    test_drug_compare_builds_control_treated_arms()
    test_bad_dose_refuses()
    print("PASS test_planner (7 tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
