"""Run the reference solver and write a versioned trajectory artifact."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from adapter import ReferenceAdapter


def main() -> int:
    ap = argparse.ArgumentParser(description="Run reference-2cell solver")
    ap.add_argument("--params", required=True, help="Path to params JSON")
    ap.add_argument("--seed", type=int, default=None, help="Override seed")
    ap.add_argument("--out", required=True, help="Output trajectory JSON")
    args = ap.parse_args()

    raw = json.loads(Path(args.params).read_text())
    file_seed = raw.pop("seed", 7)
    seed = args.seed if args.seed is not None else int(file_seed)
    adapter = ReferenceAdapter()
    artifact = adapter.run(raw, seed)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=1) + "\n")

    meta, summary = artifact["meta"], artifact["summary"]
    print(
        f"wrote {out} engine={meta['engine_id']} v{meta['engine_version']} "
        f"seed={seed} frames={summary['n_frames']} "
        f"contact={summary['contact_duration_min']}min "
        f"min_d={summary['min_distance_um']}um "
        f"final_d={summary['final_distance_um']}um"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
