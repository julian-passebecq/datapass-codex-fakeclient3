"""Allowlisted local interpretation of four ADF-shaped activities.

No expression evaluator, subprocess, network, cloud sign-in or deployment.
A manifest is written only after all preceding activities succeed.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import shutil
import sys
import uuid
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from runner.io import sha256, write_json
from jobs.study_notebook import run as study_job
from functions.publish.function_app import publish, validate_study

TYPES = ("Copy", "DatabricksNotebook", "AzureFunctionActivity", "SetVariable")


def ordered_activities(pipeline: dict) -> list[dict]:
    if not isinstance(pipeline, dict) or not isinstance(pipeline.get("properties"), dict):
        raise ValueError("pipeline and properties must be objects")
    activities = pipeline["properties"].get("activities", [])
    if not isinstance(activities, list) or not all(isinstance(a, dict) for a in activities):
        raise ValueError("activities must be an array of objects")
    if len(activities) != 4 or sorted(a.get("type", "") for a in activities) != sorted(TYPES):
        raise ValueError("exactly one activity of each supported type is required")
    by_name = {a.get("name"): a for a in activities}
    if len(by_name) != 4 or any(not isinstance(n, str) or not n for n in by_name):
        raise ValueError("activity names must be unique nonempty strings")
    dependencies = {}
    for name, activity in by_name.items():
        deps = activity.get("dependsOn", [])
        if not isinstance(deps, list) or any(not isinstance(d, dict) or d.get("dependencyConditions") != ["Succeeded"] for d in deps):
            raise ValueError("only Succeeded dependency conditions are supported")
        dependencies[name] = {d.get("activity") for d in deps}
        if not dependencies[name] <= by_name.keys():
            raise ValueError("unknown dependency")
    completed, ordered = set(), []
    while len(ordered) < 4:
        ready = [n for n in by_name if n not in completed and dependencies[n] <= completed]
        if not ready:
            raise ValueError("cyclic dependency")
        for name in ready:
            ordered.append(by_name[name]); completed.add(name)
    if tuple(a["type"] for a in ordered) != TYPES:
        raise ValueError("the data flow must be copy -> study -> publish -> manifest")
    for prev, current in zip(ordered, ordered[1:]):
        if prev["name"] not in dependencies[current["name"]]:
            raise ValueError("each activity must depend on the previous stage")
    return ordered


def run_pipeline(pipeline_path: Path, output_root: Path, site: Path | None = None,
                 study_result: Path | None = None, blade: Path | None = None) -> dict:
    pipeline_bytes = pipeline_path.read_bytes()
    pipeline = json.loads(pipeline_bytes)
    activities = ordered_activities(pipeline)
    if site is None:
        relative = Path(pipeline["properties"]["parameters"]["siteCsv"]["defaultValue"])
        site = (ROOT / relative).resolve()
        if relative.is_absolute() or not site.is_relative_to(ROOT):
            raise ValueError("default site must remain inside this repository")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    log_path = output_root / (run_id + ".json")
    log = {"version": "1.0", "synthetic": True, "run_id": run_id, "status": "running",
           "runtime": "local-python-simulator", "pipeline_sha256": hashlib.sha256(pipeline_bytes).hexdigest(), "activities": []}
    manifest = None
    try:
        for activity in activities:
            record = {"name": activity["name"], "type": activity["type"], "status": "running"}
            log["activities"].append(record)
            write_json(log_path, log)
            kind = activity["type"]
            if kind == "Copy":
                (run_dir / "raw").mkdir()
                shutil.copyfile(site, run_dir / "raw/site.csv")
            elif kind == "DatabricksNotebook":
                if study_result is None:
                    study_job(run_dir / "raw/site.csv", run_dir / "study_result.json")
                else:
                    external = validate_study(json.loads(study_result.read_text(encoding="utf-8")))
                    if external.get("source_sha256") != sha256(run_dir / "raw/site.csv"):
                        raise ValueError("external study source checksum does not match the copied CSV")
                    write_json(run_dir / "study_result.json", external)
            elif kind == "AzureFunctionActivity":
                publish(json.loads((run_dir / "study_result.json").read_text(encoding="utf-8")), run_dir / "published.json")
                if blade is not None:
                    if blade.suffix.lower() != ".obj" or blade.stat().st_size > 10_000_000:
                        raise ValueError("optional blade must be an OBJ no larger than 10 MB")
                    shutil.copyfile(blade, run_dir / "blade.obj")
            else:
                artifacts = [{"path": str(p.relative_to(run_dir)).replace("\\", "/"),
                              "sha256": sha256(p), "bytes": p.stat().st_size}
                             for p in sorted(run_dir.rglob("*")) if p.is_file()]
                manifest = {"version": "1.0", "synthetic": True, "status": "complete", "run_id": run_id,
                            "pipeline_sha256": log["pipeline_sha256"], "artifacts": artifacts,
                            "note": "Local artifacts only. Optional OBJ is linked, not physically validated."}
                write_json(run_dir / "manifest.json", manifest)
            record["status"] = "succeeded"
        log["status"] = "succeeded"
        log["manifest"] = str(run_dir / "manifest.json")
        return log
    except Exception as exc:
        if log["activities"]:
            log["activities"][-1]["status"] = "failed"
        log["status"] = "failed"
        log["error"] = f"{type(exc).__name__}: {exc}"
        (run_dir / "manifest.json").unlink(missing_ok=True)
        raise
    finally:
        write_json(log_path, log)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pipeline", type=Path, default=ROOT / "pipelines/blade_study_pipeline.json")
    p.add_argument("--runs", type=Path, default=ROOT / "runs")
    p.add_argument("--site", type=Path)
    p.add_argument("--study-result", type=Path)
    p.add_argument("--blade", type=Path)
    a = p.parse_args(argv)
    try:
        print(json.dumps(run_pipeline(a.pipeline, a.runs, a.site, a.study_result, a.blade), indent=2))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        p.exit(1, f"Pipeline failed: {exc}\n")


if __name__ == "__main__":
    main()
