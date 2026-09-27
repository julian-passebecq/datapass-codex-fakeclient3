# Databricks notebook source
"""Exported Python notebook job, run locally as a module in this pilot.

This independent simulator uses a teaching power curve; it is not a Databricks
runtime and does not import the 2D repository. External 2D results can instead
be supplied explicitly to the runner with source-checksum validation.
"""
from pathlib import Path
import csv
import io
import hashlib
import math
from runner.io import write_json


def run(site: Path, output: Path) -> dict:
    raw = site.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames != ["hour", "wind_speed_mps"]:
        raise ValueError("expected hour,wind_speed_mps")
    powers = []
    previous = None
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("malformed CSV row")
        hour, speed = int(row["hour"]), float(row["wind_speed_mps"])
        if hour < 0 or (previous is not None and hour != previous + 1) or not math.isfinite(speed) or speed < 0:
            raise ValueError("hours must be consecutive and speeds finite/nonnegative")
        previous = hour
        powers.append(0.0 if speed < 3 or speed >= 25 else 10 * min(1.0, (speed ** 3 - 27) / 1701))
    if not powers:
        raise ValueError("empty site")
    result = {"version": "1.0", "synthetic": True, "producer": "local-notebook-simulator-v1",
              "source_sha256": hashlib.sha256(raw).hexdigest(), "sample_count": len(powers),
              "annual_energy_kwh_estimate": math.fsum(powers) / len(powers) * 8760,
              "limitations": "Synthetic extrapolation, not measured AEP; local simulator, not a cloud job."}
    write_json(output, result)
    return result
