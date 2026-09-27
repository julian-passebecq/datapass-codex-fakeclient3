# Variant B: optional Linux container VM simulation

`docker compose -f docker/docker-compose.yml run --rm vm` runs the same local Python pipeline in a Linux container, with outputs in a named volume also mounted by the `storage` service. This is not a real VM, Blob API, Azurite or cloud environment. Images must already exist locally or be pulled explicitly by the person. No ports are exposed. Native pytest never starts Docker; the container route is declarative and was not run in this delivery. Inspect the named volume before removing it; no cleanup is automatic.
