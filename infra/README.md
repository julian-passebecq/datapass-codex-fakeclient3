# Infrastructure orientation, never applied

Bicep and OpenTofu are mutually exclusive examples of the same resource shape: storage, a Linux function app and a private Linux VM. Do not apply both. No credentials, secret values, public IP or SSH ingress are declared. Supply an SSH public key only through the native tool when deployment is separately approved.

These files are **not a deployment-ready environment**: managed-identity storage roles, policy, quotas, naming availability, network restrictions, host/code packaging and provider-specific validation remain to be completed. Subscription and tenant are intentionally absent. No cloud compiler/validator or deployment was run for this local pilot. Do not interpret the Python tests as IaC validation. Never commit state, plans, tfvars or deployment outputs; state may contain sensitive material.

References consulted 2026-09-27 (syntax and resource shape only, not proof of deployment):
- https://learn.microsoft.com/azure/azure-resource-manager/bicep/data-types
- https://learn.microsoft.com/azure/templates/microsoft.web/2023-12-01/sites
- https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/linux_function_app
