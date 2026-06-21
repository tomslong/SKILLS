import json
import sqlite3
import subprocess
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).parent
DB_PATH = TOOL_DIR / "_test_experiments.db"


def cleanup():
    DB_PATH.unlink(missing_ok=True)
    (TOOL_DIR / "_test_experiments.json").unlink(missing_ok=True)


def run_tracker(*args: str) -> dict:
    """Run experiment_tracker.py with args and return parsed stdout."""
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "experiment_tracker.py"),
         "--db", str(DB_PATH)] + list(args),
        capture_output=True, text=True, cwd=str(TOOL_DIR)
    )
    if result.returncode != 0:
        raise RuntimeError(f"experiment_tracker.py failed: {result.stderr}\nstdout: {result.stdout}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout}


def test_start_and_list_run():
    """Start a run, then list shows it."""
    cleanup()
    config = json.dumps({"model": "resnet50", "lr": 0.001, "batch_size": 32})
    start_result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "experiment_tracker.py"),
         "--db", str(DB_PATH), "start", "--config", config],
        capture_output=True, text=True, cwd=str(TOOL_DIR)
    )
    assert start_result.returncode == 0
    run_data = json.loads(start_result.stdout)
    assert "run_id" in run_data

    list_result = run_tracker("list")
    assert isinstance(list_result, list)
    assert any(r["run_id"] == run_data["run_id"] for r in list_result)

    cleanup()


def test_log_and_end_run():
    """Log metrics then end the run."""
    cleanup()
    config = json.dumps({"model": "vit-base"})
    start_data = run_tracker("start", "--config", config)
    run_id = start_data["run_id"]

    # Log epoch metrics
    log_result = run_tracker(
        "log", "--run-id", run_id, "--epoch", "1",
        "--metrics", json.dumps({"loss": 0.5, "acc": 0.8}))
    assert "ok" in log_result.get("raw", "").lower() or log_result == {"status": "ok"}

    # End run
    end_result = run_tracker(
        "end", "--run-id", run_id,
        "--metrics", json.dumps({"loss": 0.3, "acc": 0.92}),
        "--artifact", "models/best.pt")
    assert isinstance(end_result, dict)

    # Verify run is marked complete
    list_result = run_tracker("list")
    run = next(r for r in list_result if r["run_id"] == run_id)
    assert run["status"] == "completed"
    assert run["final_loss"] == 0.3

    cleanup()


def test_compare_runs():
    """Compare two runs returns comparison table."""
    cleanup()
    c1 = json.dumps({"model": "resnet18", "lr": 0.01})
    c2 = json.dumps({"model": "resnet50", "lr": 0.001})

    r1 = run_tracker("start", "--config", c1)
    run_tracker("end", "--run-id", r1["run_id"],
                "--metrics", json.dumps({"loss": 0.5, "acc": 0.85}),
                "--artifact", "m1.pt")

    r2 = run_tracker("start", "--config", c2)
    run_tracker("end", "--run-id", r2["run_id"],
                "--metrics", json.dumps({"loss": 0.3, "acc": 0.92}),
                "--artifact", "m2.pt")

    compare = run_tracker("compare", "--run-ids", f"{r1['run_id']},{r2['run_id']}")
    assert "runs" in compare or isinstance(compare, list)

    cleanup()


def test_cli_help():
    """--help prints usage with available actions."""
    result = subprocess.run(
        [sys.executable, str(TOOL_DIR / "experiment_tracker.py"), "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "start" in result.stdout
    assert "log" in result.stdout
    assert "end" in result.stdout
    assert "list" in result.stdout
    assert "compare" in result.stdout
