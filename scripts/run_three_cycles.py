"""Module 08 demo: real CLI processes, isolated state, explicit policy approval.

prepare: seed once, run v1/v2, propose a correction, exit.
finish: require an explicit owner approval, run v3 without seed/import, export.
Live and handwritten replay modes use separate owned runtime/artifact directories.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from time import perf_counter
from uuid import uuid4

from promptpatch.config import load_settings
from promptpatch.errors import StoreError
from promptpatch.repository import Repository, digest, utc_now
from promptpatch.tool_support import read_snapshot

ROOT = Path(__file__).resolve().parents[1]


class DemoError(ValueError):
    pass


class DemoRun:
    def __init__(self, runtime, artifacts, mode, *, repo=None, replay_file=None):
        self.runtime, self.artifacts = Path(runtime).resolve(), Path(artifacts).resolve()
        self.settings = load_settings()
        self.mode = mode
        self.repo = Path(repo or self.settings.demo_repo).resolve()
        self.replay = Path(replay_file or ROOT / "samples/replay/module08_cycles.json").resolve()
        if self.runtime == self.artifacts or self.runtime.is_relative_to(self.repo) or self.artifacts.is_relative_to(self.repo):
            raise DemoError("Keep runtime and exports separate and outside the evaluated Git repository.")
        self.manifest_path = self.runtime / "demo_run.json"
        identity = {"runtime": str(self.runtime), "artifacts": str(self.artifacts), "mode": mode,
                    "repo": str(self.repo), "model": self.settings.gemini_model if mode == "live" else "module07-replay",
                    "replay_file": str(self.replay) if mode == "replay" else None}
        if mode == "live" and (not self.settings.gemini_api_key or not self.settings.gemini_model):
            raise DemoError("Set GEMINI_API_KEY and GEMINI_MODEL in the local process environment.")
        if self.manifest_path.exists():
            self.manifest = json.loads(self.manifest_path.read_text())
            if self.manifest["identity"] != identity:
                raise DemoError("Existing demo configuration differs; restore it or choose fresh directories.")
            marker = self.artifacts / "demo_owner.json"
            if not marker.exists() or json.loads(marker.read_text())["run_id"] != self.manifest["run_id"]:
                raise DemoError("Export directory does not belong to this demo.")
        else:
            for directory in (self.runtime, self.artifacts):
                if directory.exists() and any(directory.iterdir()):
                    raise DemoError("Refusing an unowned nonempty runtime/export directory.")
            self.runtime.mkdir(parents=True, exist_ok=True)
            self.artifacts.mkdir(parents=True, exist_ok=True)
            self.manifest = {"run_id": str(uuid4()), "identity": identity, "phase": "new", "commands": {},
                             "created_at": utc_now(), "mode": mode}
            self._save()
            self._write("demo_owner.json", {"run_id": self.manifest["run_id"], "mode": mode})
        self.db_path = self.runtime / "memory.sqlite3"
        self.checkpoint_path = self.runtime / "checkpoints.sqlite3"
        self.env = {**os.environ, "PROMPTPATCH_DB_PATH": str(self.db_path),
                    "PROMPTPATCH_CHECKPOINT_DB_PATH": str(self.checkpoint_path),
                    "PROMPTPATCH_DEMO_REPO": str(self.repo), "PROMPTPATCH_MODE": mode}
        if mode == "replay":
            self.env.pop("GEMINI_API_KEY", None)
            self.env.pop("GEMINI_MODEL", None)

    def _text(self, value):
        text = json.dumps(value, indent=2, allow_nan=False) + "\n"
        if self.settings.gemini_api_key:
            text = text.replace(self.settings.gemini_api_key.get_secret_value(), "[redacted]")
        return text

    def _save(self):
        temp = self.manifest_path.with_suffix(".tmp")
        temp.write_text(self._text(self.manifest))
        temp.replace(self.manifest_path)

    def _write(self, name, value):
        path = self.artifacts / name
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(self._text(value))
        temp.replace(path)

    def cli(self, step, args, *, review=False):
        previous = self.manifest["commands"].get(step)
        if previous and previous["exit_code"] == 0:
            if review:
                self._export_cycle(int(step[-1]), previous["output"])
            return previous["output"]
        start, clock = utc_now(), perf_counter()
        process = subprocess.Popen([sys.executable, "-m", "promptpatch.cli", *args], env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=240)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            timed_out = True
        try:
            output = json.loads(stdout)
        except ValueError:
            output = stdout.strip()
        event = {"args": args, "pid": process.pid, "parent_pid": os.getpid(), "started_at": start,
                 "exited_at": utc_now(), "exit_code": process.returncode, "confirmed_exit": process.poll() is not None,
                 "elapsed_ms": (perf_counter() - clock) * 1000, "timed_out": timed_out,
                 "output": output, "stderr": stderr.strip()}
        self.manifest["commands"][step] = event
        self._save()
        if review:
            self._export_cycle(int(step[-1]), output)
        if process.returncode != 0 or timed_out:
            raise DemoError("CLI step failed: " + step + "; persisted output/audit retained; no automatic live/replay fallback.")
        if review and (output["status"] != "completed" or output["planner_error"]):
            raise DemoError("Review did not complete; inspect its recorded error and evidence.")
        return output

    def source_identity(self):
        with read_snapshot(self.db_path) as db:
            cases = [dict(row) for row in db.execute("SELECT id,case_key,revision,input_text,expected_json,tags_json,content_hash,active "
                                                   "FROM test_cases WHERE project_id='demo' ORDER BY case_key,revision")]
            prompts = [dict(row) for row in db.execute("SELECT id,label,git_commit_sha,prompt_path,content_hash "
                                                     "FROM prompt_versions WHERE project_id='demo' ORDER BY label")]
            imports = db.execute("SELECT COUNT(*) FROM audit_events WHERE project_id='demo' AND event_type='fixture_case_imported'").fetchone()[0]
        return {"case_ids": [row["id"] for row in cases], "case_snapshot_hash": digest(cases),
                "prompt_snapshot_hash": digest(prompts), "import_events": imports}

    def memory_snapshot(self):
        with read_snapshot(self.db_path) as db:
            risks = [dict(row) for row in db.execute("SELECT * FROM failure_memories WHERE project_id='demo' ORDER BY id")]
        with Repository(self.db_path) as store:
            return {"risks": [{**{k: v for k, v in row.items() if k != "evidence_json"},
                               "evidence": json.loads(row["evidence_json"])} for row in risks],
                    "active_policy": store.get_active_policy("demo"), "human_decisions": store.get_human_decisions("demo")}

    def _export_cycle(self, number, status):
        if not isinstance(status, dict) or not status.get("cycle_id"):
            self._write(f"cycle_{number}.json", {"mode": self.mode, "error": "CLI did not return a cycle", "output": status})
            return
        with read_snapshot(self.db_path) as db:
            planner = db.execute("SELECT * FROM planner_decisions WHERE project_id='demo' AND cycle_id=?", (status["cycle_id"],)).fetchone()
            rows = db.execute("SELECT * FROM test_executions WHERE project_id='demo' AND cycle_id=? ORDER BY created_at,id", (status["cycle_id"],)).fetchall()
        with Repository(self.db_path) as store:
            version = store.get_prompt_version("demo", status["version_id"])
            policy = store.get_policy("demo", status["policy_id"])
        checkpoint_count = 0
        if self.checkpoint_path.exists():
            with sqlite3.connect(self.checkpoint_path) as checkpoints:
                checkpoint_count = checkpoints.execute("SELECT COUNT(*) FROM checkpoints WHERE thread_id=?", (f"demo:{status['cycle_id']}",)).fetchone()[0]
        self._write(f"cycle_{number}.json", {"mode": self.mode, "live_inference": self.mode == "live", "status": status,
                     "prompt_version": version, "policy": policy,
                     "planner": json.loads(planner["decision_json"]) if planner else None,
                     "executions": [{**{k: v for k, v in dict(row).items() if k not in {"response_json", "validation_json"}},
                                     "response": json.loads(row["response_json"]), "validation": json.loads(row["validation_json"])} for row in rows],
                     "checkpoint_thread_id": f"demo:{status['cycle_id']}", "checkpoint_count": checkpoint_count})

    def cycle(self, number):
        args = ["review", "start", "--project", "demo", "--version", f"v{number}", "--cycle", f"module08-c{number}"]
        if number > 1:
            args += ["--base-version", f"v{number - 1}"]
        if self.mode == "replay":
            args += ["--replay-file", str(self.replay), "--replay-scenario", f"cycle_{number}"]
        return self.cli(f"cycle_{number}", args, review=True)

    def prepare(self):
        if self.manifest["phase"] in {"prepared", "complete"}:
            return {"phase": self.manifest["phase"], "artifacts": str(self.artifacts)}
        self.cli("init", ["init"])
        self.cli("seed_once", ["demo", "seed", "--actor", "module08-fictional-bootstrap", "--approve-baseline"])
        if "source_identity" not in self.manifest:
            self.manifest["source_identity"] = self.source_identity()
            self.manifest["memory_before"] = self.memory_snapshot()
            self._save()
        self.cycle(1)
        if "memory_after_cycle1" not in self.manifest:
            self.manifest["memory_after_cycle1"] = self.memory_snapshot()
            self._save()
        self.cycle(2)
        if "memory_before_restart" not in self.manifest:
            self.manifest["memory_before_restart"] = self.memory_snapshot()
            self._save()
        self.cli("propose_policy", ["policy", "propose", "--project", "demo", "--file", str(ROOT / "samples/evaluation_policy_v2.json"),
                                    "--actor", "module08-proposal", "--reason", "Proposed demo correction: tighten absolute tolerance from 0.01 mm to 0.001 mm; awaiting explicit owner approval."])
        self.manifest["phase"] = "prepared"
        self._save()
        self._write("policy_correction_pending.json", {"mode": self.mode, "old_policy": self.manifest["memory_before_restart"]["active_policy"],
                    "proposal": self.manifest["commands"]["propose_policy"]["output"], "approval": "pending",
                    "next_command": "finish --approve-policy --actor <owner> --approval-reference <explicit approval>"})
        self._write("memory_before_after.json", {"mode": self.mode, **{k: self.manifest[k] for k in
                    ("memory_before", "memory_after_cycle1", "memory_before_restart")}})
        return {"phase": "prepared", "approval": "pending", "artifacts": str(self.artifacts)}

    def finish(self, *, approve_policy=False, actor=None, approval_reference=None):
        if self.manifest["phase"] == "complete":
            return json.loads((self.artifacts / "summary.json").read_text())
        if self.manifest["phase"] != "prepared":
            raise DemoError("Run prepare successfully before finish.")
        if not approve_policy or not actor or not actor.strip() or not approval_reference or not approval_reference.strip():
            raise DemoError("Finish requires --approve-policy, --actor and --approval-reference; no approval is inferred.")
        if self.source_identity() != self.manifest["source_identity"]:
            raise DemoError("Source/catalog identity changed before restart; refusing to reseed or silently replace it.")
        self.manifest["approval_reference"] = approval_reference
        self.manifest["approval_actor"] = actor
        self._save()
        self.cli("approve_policy", ["policy", "approve", "--project", "demo", "--revision", "2", "--actor", actor])
        self.cycle(3)
        if self.source_identity() != self.manifest["source_identity"]:
            raise DemoError("Source/import identity changed during the restarted cycle.")
        self.manifest["memory_after_cycle3"] = self.memory_snapshot()
        summary = self._final_exports()
        self.manifest["phase"] = "complete"
        self._save()
        return summary

    def _final_exports(self):
        commands = self.manifest["commands"]
        second, third = commands["cycle_2"], commands["cycle_3"]
        if not second["confirmed_exit"] or second["exit_code"] != 0 or second["exited_at"] > third["started_at"] or second["pid"] == third["pid"]:
            raise DemoError("Process restart evidence is inconsistent.")
        summary = {"mode": self.mode, "live_inference": self.mode == "live", "cycles": [], "release_approval": "pending",
                   "process_restart_verified": True, "sources_and_import_events_unchanged": True, "approximate_cost": None}
        for number in (1, 2, 3):
            export = json.loads((self.artifacts / f"cycle_{number}.json").read_text())
            status, plan = export["status"], export["planner"]
            if [r["test_id"] for r in status["results"]] != status["selected_test_ids"] or not export["checkpoint_count"]:
                raise DemoError("Execution/checkpoint evidence does not match the selected plan.")
            expected_mode = "live" if self.mode == "live" else "replay"
            if not plan or plan["response"]["mode"] != expected_mode or any(r["response"]["mode"] != expected_mode for r in export["executions"]):
                raise DemoError("Provider mode mismatch; replay cannot count as live inference.")
            history = (plan["input"]["long_term_memory"] or {}).get("risks", [])
            cited = set(plan["plan"]["memory_evidence_ids"])
            summary["cycles"].append({"cycle": number, "version": status["version"], "selected": status["selected_test_ids"],
                 "statuses": [r["status"] for r in status["results"]], "recommendation": status["next_action"],
                 "policy_revision": status["policy_revision"], "reason_summary": plan["plan"]["reason_summary"],
                 "supplied_risk_ids": [r["id"] for r in history],
                 "cited_risk_ids": [r["id"] for r in history if r["id"] in cited or "risk:" + r["id"] in cited],
                 "prior_failed_cases_retested": sorted({r["evidence"].get("test_id") for r in history if r["evidence"].get("test_id") in status["selected_test_ids"]}),
                 "approval": status["approval"]})
        with Repository(self.db_path) as store:
            policies = [store.get_policy("demo", commands["cycle_1"]["output"]["policy_id"]), store.get_active_policy("demo")]
            timeline = store.get_project_timeline("demo")
            if store.get_human_decisions("demo"):
                raise DemoError("Demo must not automatically approve a prompt version.")
        if policies[0]["status"] != "superseded" or policies[1]["revision"] != 2 or commands["cycle_3"]["output"]["policy_id"] != policies[1]["id"]:
            raise DemoError("Correction was not active for the restarted cycle.")
        self._write("policy_correction.json", {"mode": self.mode, "policies": policies, "actor": self.manifest["approval_actor"],
                    "approval_reference": self.manifest["approval_reference"], "cycle3_policy_id": policies[1]["id"]})
        self._write("memory_before_after.json", {"mode": self.mode, **{k: self.manifest[k] for k in
                    ("memory_before", "memory_after_cycle1", "memory_before_restart", "memory_after_cycle3")}})
        self._write("tool_timeline.json", {"mode": self.mode, "events": [{**{k: v for k, v in r.items() if k != "details_json"},
                     "details": json.loads(r["details_json"])} for r in timeline]})
        self._write("process_evidence.json", {"mode": self.mode, "cycle2_process": second, "cycle3_process": third,
                     "source_identity_before": self.manifest["source_identity"], "source_identity_after": self.source_identity(),
                     "seed_commands": 1, "seed_after_cycle2": False})
        text = (f"Mode: {self.mode}\nCycle 2 PID {second['pid']} exited {second['exit_code']} at {second['exited_at']}; parent reaped it.\n"
                f"Cycle 3 PID {third['pid']} started at {third['started_at']} and exited {third['exit_code']}.\n"
                "Same persistent domain/checkpoint files; same case IDs and source hashes; no seed/import after cycle 2.\n"
                "Policy revision 2 was explicitly approved before cycle 3; revision 1 remains queryable.\nPrompt release approval remains pending.\n")
        (self.artifacts / "restart_evidence.txt").write_text(text)
        self._write("summary.json", summary)
        return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "finish"])
    parser.add_argument("--runtime", type=Path, default=Path("data/module08/live"))
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts/demo"))
    parser.add_argument("--mode", choices=["live", "replay"], default="live")
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--replay-file", type=Path)
    parser.add_argument("--approve-policy", action="store_true")
    parser.add_argument("--actor")
    parser.add_argument("--approval-reference")
    args = parser.parse_args(argv)
    try:
        demo = DemoRun(args.runtime, args.artifacts, args.mode, repo=args.repo, replay_file=args.replay_file)
        result = demo.prepare() if args.stage == "prepare" else demo.finish(approve_policy=args.approve_policy, actor=args.actor, approval_reference=args.approval_reference)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, sqlite3.Error, ValueError, StoreError) as error:
        message = str(error) if isinstance(error, DemoError) else "Inspect the owned run manifest, cycle exports and CLI audit."
        print("Demo blocked: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
