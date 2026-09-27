import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest
from runner.run_pipeline import ROOT, run_pipeline, ordered_activities
from runner.io import sha256
from jobs.study_notebook import run as study_job
PIPELINE = ROOT / "pipelines/blade_study_pipeline.json"


def test_end_to_end_manifest_and_checksums(tmp_path):
    result = run_pipeline(PIPELINE, tmp_path)
    assert result["status"] == "succeeded" and len(result["activities"]) == 4
    manifest_path = Path(result["manifest"])
    manifest = json.loads(manifest_path.read_text())
    assert manifest["status"] == "complete" and manifest["synthetic"] is True
    assert len(manifest["artifacts"]) == 3
    for item in manifest["artifacts"]:
        p = manifest_path.parent / item["path"]
        assert sha256(p) == item["sha256"] and p.stat().st_size == item["bytes"]
    study = json.loads((manifest_path.parent / "study_result.json").read_text())
    assert study["sample_count"] == 24 and study["annual_energy_kwh_estimate"] > 0


def test_run_isolation(tmp_path):
    first = run_pipeline(PIPELINE, tmp_path)
    before = Path(first["manifest"]).read_bytes()
    second = run_pipeline(PIPELINE, tmp_path)
    assert first["run_id"] != second["run_id"]
    assert Path(first["manifest"]).read_bytes() == before


def test_dependency_order_not_array_order():
    pipeline = json.loads(PIPELINE.read_text())
    pipeline["properties"]["activities"].reverse()
    assert [a["name"] for a in ordered_activities(pipeline)] == ["copy_raw", "study_job", "publish", "write_manifest"]


def test_invalid_graphs_fail_before_writes(tmp_path):
    original = json.loads(PIPELINE.read_text())
    invalid = [[], {"properties": []}, {"properties": {"activities": [1]}}]
    p = copy.deepcopy(original); p["properties"]["activities"][0]["type"] = "Shell"; invalid.append(p)
    p = copy.deepcopy(original); p["properties"]["activities"][0]["dependsOn"] = [{"activity":"publish","dependencyConditions":["Succeeded"]}]; invalid.append(p)
    p = copy.deepcopy(original); p["properties"]["activities"][1]["dependsOn"][0]["activity"] = "missing"; invalid.append(p)
    p = copy.deepcopy(original); p["properties"]["activities"][1]["dependsOn"] = []; invalid.append(p)
    for p in invalid:
        f = tmp_path / "invalid.json"; f.write_text(json.dumps(p))
        with pytest.raises(ValueError): run_pipeline(f, tmp_path / "runs")
        assert not (tmp_path / "runs").exists()


def test_failed_job_logs_and_no_manifest(tmp_path):
    bad = tmp_path / "bad.csv"; bad.write_text("hour,wind_speed_mps\n0,NaN\n")
    with pytest.raises(ValueError): run_pipeline(PIPELINE, tmp_path / "runs", bad)
    logs = list((tmp_path / "runs").glob("*.json"))
    assert len(logs) == 1
    log = json.loads(logs[0].read_text())
    assert log["status"] == "failed" and log["activities"][-1]["status"] == "failed"
    assert not list((tmp_path / "runs").rglob("manifest.json"))


def test_plain_function_and_pipeline_cli(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "functions/publish/local_run.py"), "--out", str(tmp_path / "published.json")], check=True, capture_output=True, cwd=tmp_path)
    assert json.loads((tmp_path / "published.json").read_text())["state"] == "published-locally"
    subprocess.run([sys.executable, str(ROOT / "runner/run_pipeline.py"), "--runs", str(tmp_path / "runs")], check=True, capture_output=True, cwd=tmp_path)
    assert not (ROOT / ".datapass").exists()


def test_external_study_and_blade_exchange(tmp_path):
    site = ROOT / "fixtures/site_a_wind.csv"
    external = tmp_path / "study.json"; study_job(site, external)
    blade = tmp_path / "blade.obj"; blade.write_text("# Synthetic exchange fixture\nv 0 0 0\n")
    result = run_pipeline(PIPELINE, tmp_path / "runs", site, external, blade)
    manifest = json.loads(Path(result["manifest"]).read_text())
    assert any(a["path"] == "blade.obj" and a["sha256"] == sha256(blade) for a in manifest["artifacts"])
    wrong = json.loads(external.read_text()); wrong["source_sha256"] = "0" * 64
    external.write_text(json.dumps(wrong))
    with pytest.raises(ValueError, match="checksum"):
        run_pipeline(PIPELINE, tmp_path / "bad-runs", site, external)
    assert not list((tmp_path / "bad-runs").rglob("manifest.json"))


def test_default_site_cannot_escape_repository(tmp_path):
    pipeline = json.loads(PIPELINE.read_text())
    pipeline["properties"]["parameters"]["siteCsv"]["defaultValue"] = "../outside.csv"
    f = tmp_path / "bad.json"; f.write_text(json.dumps(pipeline))
    with pytest.raises(ValueError, match="inside"):
        run_pipeline(f, tmp_path / "runs")
    assert not (tmp_path / "runs").exists()
