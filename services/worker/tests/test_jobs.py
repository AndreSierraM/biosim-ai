"""Unit tests: filesystem job store. Run: python3 services/worker/tests/test_jobs.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from worker.jobs import JobStore


def test_create_get_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        job = store.create("reference-2cell", {"adhesion": 6.0}, 7)
        assert job["state"] == "queued"
        assert job["params"] == {"adhesion": 6.0}
        fetched = store.get(job["id"])
        assert fetched == job


def test_update_state_and_rejects_bad_state():
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        job = store.create("reference-2cell", {}, 7)
        updated = store.update(job["id"], state="running")
        assert updated["state"] == "running"
        try:
            store.update(job["id"], state="exploding")
        except ValueError:
            pass
        else:
            raise AssertionError("bad state accepted")


def test_get_missing_raises():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            JobStore(tmp).get("nope")
        except KeyError:
            pass
        else:
            raise AssertionError("missing job did not raise")


def test_list_returns_all():
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        a = store.create("reference-2cell", {}, 1)
        b = store.create("reference-2cell", {}, 2)
        ids = {j["id"] for j in store.list()}
        assert ids == {a["id"], b["id"]}


def _assert_keyerror(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except KeyError:
        return
    raise AssertionError(f"{fn.__name__} accepted bad job_id {args[0]!r}")


def test_path_traversal_ids_raise_keyerror():
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        for bad in ("../..", "abc"):
            _assert_keyerror(store.get, bad)
            _assert_keyerror(store.update, bad, state="running")
            _assert_keyerror(store.read_trajectory, bad)
            _assert_keyerror(store.write_trajectory, bad, {})
        assert sorted(Path(tmp).iterdir()) == []


def test_valid_12hex_id_works():
    import re

    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        job = store.create("reference-2cell", {"a": 1}, 3)
        assert re.match(r"^[0-9a-f]{12}$", job["id"]), job["id"]
        assert store.get(job["id"])["id"] == job["id"]
        assert store.update(job["id"], state="running")["state"] == "running"
        store.write_trajectory(job["id"], {"steps": [1, 2]})
        assert store.read_trajectory(job["id"]) == {"steps": [1, 2]}


def test_find_for_key_returns_newest_match():
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        assert store.find_for_key("reference-2cell", {"a": 1}, 3, "k") is None
        queued = store.create("reference-2cell", {"a": 1}, 3, idempotency_key="k")
        found = store.find_for_key("reference-2cell", {"a": 1}, 3, "k")
        assert found is not None and found["id"] == queued["id"], found
        old = store.create("reference-2cell", {"a": 1}, 3, idempotency_key="k")
        store.update(old["id"], state="completed")
        new = store.create("reference-2cell", {"a": 1}, 3, idempotency_key="k")
        store.update(new["id"], state="completed")
        other = store.create("reference-2cell", {"a": 1}, 4, idempotency_key="k")
        store.update(other["id"], state="completed")
        nokey = store.create("reference-2cell", {"a": 1}, 3)
        store.update(nokey["id"], state="completed")
        assert queued["state"] == "queued"
        found = store.find_for_key("reference-2cell", {"a": 1}, 3, "k")
        assert found is not None and found["id"] == new["id"], found
        assert store.find_for_key("reference-2cell", {"a": 2}, 3, "k") is None
        assert store.find_for_key("reference-2cell", {"a": 1}, 3, "other") is None
        failed = store.create("reference-2cell", {"a": 9}, 9, idempotency_key="f")
        store.update(failed["id"], state="failed")
        assert store.find_for_key("reference-2cell", {"a": 9}, 9, "f") is None


def test_key_conflict_detects_reused_key():
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        assert store.key_conflict({"a": 1}, 3, "reference-2cell", "k") is None
        job = store.create("reference-2cell", {"a": 1}, 3, idempotency_key="k")
        assert store.key_conflict({"a": 1}, 3, "reference-2cell", "k") is None
        clash = store.key_conflict({"a": 2}, 3, "reference-2cell", "k")
        assert clash is not None and clash["id"] == job["id"], clash


def test_terminal_states_are_immutable():
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        for terminal in ("completed", "failed", "cancelled"):
            job = store.create("reference-2cell", {}, 7)
            store.update(job["id"], state="completed" if terminal == "completed"
                         else "running")
            if terminal != "completed":
                store.update(job["id"], state=terminal)
            for other in ("queued", "running", "completed"):
                if other == terminal:
                    continue
                try:
                    store.update(job["id"], state=other)
                except ValueError:
                    pass
                else:
                    raise AssertionError(
                        f"{terminal} allowed transition to {other}")
            assert store.get(job["id"])["state"] == terminal


def test_concurrent_updates_never_corrupt():
    import threading
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        job = store.create("reference-2cell", {}, 7)
        errors: list = []

        def bump(i: int):
            try:
                for _ in range(50):
                    store.update(job["id"], provenance={"i": i})
            except Exception as e:  # noqa: BLE001 - collected, asserted empty
                errors.append(e)

        threads = [threading.Thread(target=bump, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors, errors[:3]
        final = store.get(job["id"])
        assert final["state"] == "queued" and isinstance(final["provenance"], dict)


def test_create_idempotent_reserve_is_atomic():
    import threading
    from worker.jobs import KeyConflict
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        job, dedup = store.create_idempotent("e", {"a": 1}, 3, idempotency_key="k")
        assert dedup is False
        same, dedup = store.create_idempotent("e", {"a": 1}, 3, idempotency_key="k")
        assert dedup is True and same["id"] == job["id"], (same, dedup)
        try:
            store.create_idempotent("e", {"a": 2}, 3, idempotency_key="k")
        except KeyConflict:
            pass
        else:
            raise AssertionError("conflicting reuse accepted")
        results: list = []

        def reserve():
            try:
                results.append(store.create_idempotent("e", {"a": 5}, 5,
                                                       idempotency_key="race"))
            except KeyConflict as e:
                results.append(e)

        threads = [threading.Thread(target=reserve) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        made = [r for r in results if not isinstance(r, KeyConflict)]
        assert len(made) == 20 and len({r[0]["id"] for r in made}) == 1, len(made)
        assert all(r[1] in (True, False) for r in made)
        assert sum(1 for r in made if r[1] is False) == 1


def test_purge_expired_keeps_fresh():
    import os
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        fresh = store.create("reference-2cell", {}, 1)
        old = store.create("reference-2cell", {}, 2)
        ancient = Path(tmp) / old["id"] / "job.json"
        os.utime(ancient, (0, 0))
        assert store.purge_expired(max_age_days=30) == 1
        assert store.get(fresh["id"])["id"] == fresh["id"]
        try:
            store.get(old["id"])
        except KeyError:
            pass
        else:
            raise AssertionError("expired job survived")


def main() -> int:
    test_create_get_roundtrip()
    test_update_state_and_rejects_bad_state()
    test_get_missing_raises()
    test_list_returns_all()
    test_path_traversal_ids_raise_keyerror()
    test_valid_12hex_id_works()
    test_find_for_key_returns_newest_match()
    test_key_conflict_detects_reused_key()
    test_terminal_states_are_immutable()
    test_concurrent_updates_never_corrupt()
    test_create_idempotent_reserve_is_atomic()
    test_purge_expired_keeps_fresh()
    print("PASS test_jobs (12 tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
