"""Functions-style pure handler with no cloud SDK, network or secret."""
from pathlib import Path
import math
from runner.io import write_json


def validate_study(payload: dict) -> dict:
    if not isinstance(payload, dict) or payload.get("version") != "1.0" or payload.get("synthetic") is not True:
        raise ValueError("only version 1.0 synthetic study results are accepted")
    energy = payload.get("annual_energy_kwh_estimate")
    if isinstance(energy, bool) or not isinstance(energy, (int, float)) or not math.isfinite(energy) or energy < 0:
        raise ValueError("annual energy must be finite and nonnegative")
    return payload


def publish(payload: dict, destination: Path) -> dict:
    result = {"version": "1.0", "synthetic": True, "state": "published-locally",
              "study": validate_study(payload)}
    write_json(destination, result)
    return result
