"""Reproducibility gate: same seed -> byte-identical artifact.

Stdlib only. Run: python3 tests/test_determinism.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapter import ReferenceAdapter

ROOT = Path(__file__).parent.parent


def load(name: str):
    raw = json.loads((ROOT / "params" / name).read_text())
    return raw, int(raw.pop("seed"))


def main() -> int:
    adapter = ReferenceAdapter()
    base_params, seed = load("baseline.json")

    a = json.dumps(adapter.run(base_params, seed), sort_keys=True)
    b = json.dumps(adapter.run(base_params, seed), sort_keys=True)
    assert a == b, "same seed diverged: solver is not deterministic"
    c = json.dumps(adapter.run(base_params, seed + 1), sort_keys=True)
    assert a != c, "different seed produced identical output (suspicious)"

    art = json.loads(a)
    assert art["meta"]["engine_id"] == "reference-2cell", "wrong engine id"
    assert len(art["frames"]) > 100, "too few frames"
    assert len(art["frames"][0]["cells"]) == 2, "expected exactly 2 cells"

    high_params, _ = load("high-adhesion.json")
    base_contact = art["summary"]["contact_duration_min"]
    high_contact = adapter.run(high_params, seed)["summary"]["contact_duration_min"]
    assert high_contact >= base_contact, (
        f"adhesion effect inverted: high={high_contact} < base={base_contact}"
    )

    print(
        f"PASS determinism seed={seed} frames={len(art['frames'])} "
        f"contact baseline={base_contact}min high={high_contact}min"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
