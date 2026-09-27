# Wind platform - synthetic local pilot

A Python 3.11+ platform around the teaching study. No cloud account, paid service, Docker or DataPass is needed to run it. All fixtures are synthetic; no values describe a real machine.

```sh
python runner/run_pipeline.py
python functions/publish/local_run.py
python -m pip install 'pytest>=8,<9'
python -m pytest -q
```

The pipeline reads `pipelines/blade_study_pipeline.json`: four activities, their names/types and `dependsOn`. The allowlisted local adapters copy the CSV, call the exported Python notebook job, call the pure publish handler, and write a checksummed manifest. Each run has an isolated artifact directory and a UTC timestamp/unique-suffix log in `runs/`. Failure is logged and never leaves a success manifest. Reordering declarations works; cycles, unknown dependencies/types and missing stage dependencies fail before execution. No expression from JSON is evaluated and no command, network or deployment is launched.

## Actual versus simulated

`jobs/study_notebook.py` is an independently implemented **local notebook-job stand-in**, not an executed Databricks or Fabric runtime. Its toy curve matches the documented teaching parameters (3/12/25 m/s, 10 kW), but it does not import or silently replace the 2D package. Its producer label distinguishes its outputs. The sample has 24 synthetic consecutive hours; annualization is not measured AEP.

The ADF-shaped JSON is intentionally a local subset, **not deployable ADF JSON**: linked services and datasets are absent, and the final SetVariable maps locally to manifest writing. Databricks bundle and Fabric item folders are navigation/declaration fixtures; actual runtime/widget wiring and provider validation are not claimed. The report folder is the explicitly allowed stub. Infrastructure is never applied; read `infra/README.md`. Docker is an optional VM simulation, not a requirement or a verified deployment.

## Explicit 2D -> 3D -> platform file exchange

After independently generating the study JSON and blade OBJ, supply paths explicitly:

```sh
python runner/run_pipeline.py --site /path/to/site_a_wind.csv --study-result /path/to/study_result.json --blade /path/to/blade_v1.obj
```

The notebook-stage adapter accepts the versioned synthetic external result only if its source SHA-256 matches the copied CSV. The publish stage optionally copies the OBJ and the manifest hashes it. Linking does **not** assert geometric or physical consistency. There is no cross-repository import or hidden sibling-folder lookup. Without external inputs, everything runs from this repository's fixtures.

## Evidence

Eight native tests cover the end-to-end run, checksums, unique runs, ordering, invalid graphs, failure logging/no success manifest, the independent function CLI and external-result source matching. GitHub Actions runs them on Python 3.11/3.12/3.13. These do not establish browser, extension, Docker, IaC or cloud runtime evidence.
