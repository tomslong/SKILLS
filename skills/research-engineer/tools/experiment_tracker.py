"""Lightweight experiment tracking with SQLite + JSON backing.

Usage:
    python experiment_tracker.py start --config '{"model":"resnet50","lr":0.001}'
    python experiment_tracker.py log --run-id <id> --epoch 1 --metrics '{"loss":0.5}'
    python experiment_tracker.py end --run-id <id> --metrics '{"loss":0.3}' --artifact model.pt
    python experiment_tracker.py list
    python experiment_tracker.py compare --run-ids id1,id2

Stores: SQLite database for structured queries, JSON file for full metric history.
"""

import argparse
import json
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path
from typing import Optional


class ExperimentTracker:
    """Tracks ML experiments with SQLite + JSON backing."""

    def __init__(self, db_path: str = "experiments.db"):
        self.db_path = Path(db_path)
        self.json_path = self.db_path.with_suffix(".json")
        self._init_db()
        self._load_json()

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                config TEXT,
                status TEXT DEFAULT 'running',
                created_at TEXT,
                final_metrics TEXT,
                artifact_path TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                epoch INTEGER,
                metrics TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        conn.commit()
        conn.close()

    def _load_json(self):
        """Load JSON history file."""
        if self.json_path.exists():
            with open(self.json_path) as f:
                self._json_data = json.load(f)
        else:
            self._json_data = {}

    def _save_json(self):
        """Persist JSON history file."""
        with open(self.json_path, "w") as f:
            json.dump(self._json_data, f, indent=2)

    def start_run(self, config: dict) -> str:
        """Start a new run. Returns run_id."""
        run_id = uuid.uuid4().hex[:12]
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO runs (run_id, config, status, created_at) VALUES (?, ?, ?, ?)",
            (run_id, json.dumps(config), "running", now))
        conn.commit()
        conn.close()
        self._json_data[run_id] = {
            "config": config,
            "created_at": now,
            "epochs": [],
            "final_metrics": None,
            "artifact_path": None,
        }
        self._save_json()
        return run_id

    def log_metrics(self, run_id: str, epoch: int, metrics: dict):
        """Log metrics for a specific epoch."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO metrics (run_id, epoch, metrics) VALUES (?, ?, ?)",
            (run_id, epoch, json.dumps(metrics)))
        conn.commit()
        conn.close()
        if run_id in self._json_data:
            self._json_data[run_id]["epochs"].append({"epoch": epoch, "metrics": metrics})
            self._save_json()

    def end_run(self, run_id: str, final_metrics: dict, artifact_path: str = ""):
        """Mark a run as completed with final metrics."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "UPDATE runs SET status = 'completed', final_metrics = ?, artifact_path = ? WHERE run_id = ?",
            (json.dumps(final_metrics), artifact_path, run_id))
        conn.commit()
        conn.close()
        if run_id in self._json_data:
            self._json_data[run_id]["final_metrics"] = final_metrics
            self._json_data[run_id]["artifact_path"] = artifact_path
            self._save_json()

    def list_runs(self) -> list[dict]:
        """List all runs with summary info."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT run_id, config, status, created_at, final_metrics, artifact_path FROM runs ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            d["config"] = json.loads(d["config"]) if d["config"] else {}
            d["final_metrics"] = json.loads(d["final_metrics"]) if d["final_metrics"] else {}
            # Flatten final_metrics for easy comparison
            if d["final_metrics"]:
                for k, v in d["final_metrics"].items():
                    d[f"final_{k}"] = v
            result.append(d)
        return result

    def compare_runs(self, run_ids: list[str]) -> dict:
        """Compare multiple runs side by side."""
        conn = sqlite3.connect(str(self.db_path))
        runs = []
        for rid in run_ids:
            row = conn.execute(
                "SELECT run_id, config, final_metrics FROM runs WHERE run_id = ?",
                (rid,)).fetchone()
            if row:
                config = json.loads(row[1]) if row[1] else {}
                metrics = json.loads(row[2]) if row[2] else {}
                runs.append({"run_id": row[0], "config": config, "final_metrics": metrics})
        conn.close()
        return {"runs": runs, "count": len(runs)}


def main():
    parser = argparse.ArgumentParser(description="Lightweight ML experiment tracker")
    parser.add_argument("--db", default="experiments.db", help="SQLite database path")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # start
    p_start = subparsers.add_parser("start", help="Start a new run")
    p_start.add_argument("--config", required=True, help="JSON config dict")

    # log
    p_log = subparsers.add_parser("log", help="Log epoch metrics")
    p_log.add_argument("--run-id", required=True)
    p_log.add_argument("--epoch", type=int, required=True)
    p_log.add_argument("--metrics", required=True, help="JSON metrics dict")

    # end
    p_end = subparsers.add_parser("end", help="End a run")
    p_end.add_argument("--run-id", required=True)
    p_end.add_argument("--metrics", required=True, help="JSON final metrics dict")
    p_end.add_argument("--artifact", default="", help="Model artifact path")

    # list
    p_list = subparsers.add_parser("list", help="List all runs")

    # compare
    p_compare = subparsers.add_parser("compare", help="Compare runs")
    p_compare.add_argument("--run-ids", required=True, help="Comma-separated run IDs")

    args = parser.parse_args()
    tracker = ExperimentTracker(args.db)

    if args.action == "start":
        config = json.loads(args.config)
        run_id = tracker.start_run(config)
        print(json.dumps({"run_id": run_id}))

    elif args.action == "log":
        metrics = json.loads(args.metrics)
        tracker.log_metrics(args.run_id, args.epoch, metrics)
        print(json.dumps({"status": "ok"}))

    elif args.action == "end":
        metrics = json.loads(args.metrics)
        tracker.end_run(args.run_id, metrics, args.artifact)
        print(json.dumps({"status": "completed", "run_id": args.run_id}))

    elif args.action == "list":
        runs = tracker.list_runs()
        print(json.dumps(runs, indent=2))

    elif args.action == "compare":
        run_ids = [r.strip() for r in args.run_ids.split(",")]
        result = tracker.compare_runs(run_ids)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
