# vcfa_org Module

Creates a VMware Cloud Foundation Automation (VCFA) organization and all of its associated components:

- Organization and local admin user
- Org-level networking
- Regional networking (one per region)
- Region quotas (VM classes, storage policies, zone resource allocations)

## Requirements

| Provider | Version |
|----------|---------|
| vmware/vcfa | ~> 1.0.0 |

## Usage

```hcl
module "vcfa_org" {
  source  = "../modules/vcfa_org"
  org     = var.org
  regions = var.regions
}
```

### Minimal example (`terraform.tfvars`)

```hcl
org = {
  name           = "my-org"
  display_name   = "My Organization"
  description    = "Created with Terraform"
  admin_name     = "admin"
  admin_password = "ChangeMe1!"
  log_name       = "my-org"
}

regions = {
  ca-east-1 = {
    vcenter          = "vcenter.example.com (as identified in VCFA connections)"
    supervisor       = "supervisor-name"
    vm_classes       = ["best-effort-small", "best-effort-medium"]
    storage_policies = ["ca-east-1-az1-gold01"]
    provider_gateway = "pg-ca-east-1-az1"
    edge_cluster     = "edge-cluster-name"
    zones = [
      {
        name                   = "ca-east-1-az1"
        cpu_limit_mhz          = 1000000
        cpu_reservation_mhz    = 0
        memory_limit_mib       = 1024000
        memory_reservation_mib = 0
      }
    ]
  }
}
```

### Multi-region example

```hcl
regions = {
  ca-east-1 = {
    vcenter          = "vcenter-east1.example.com (Sciences)"
    supervisor       = "m02-w01-cl01-sup01"
    vm_classes       = ["best-effort-small", "best-effort-medium", "best-effort-large"]
    storage_policies = ["ca-east-1-az1-gold01"]
    provider_gateway = "pg-ca-east-1-az1"
    edge_cluster     = "vcf-m02-w01-ec01"
    zones = [
      {
        name                   = "ca-east-1-az1"
        cpu_limit_mhz          = 1000000
        cpu_reservation_mhz    = 0
        memory_limit_mib       = 1024000
        memory_reservation_mib = 0
      }
    ]
  }

  ca-east-2 = {
    vcenter          = "vcenter-east2.example.com (Culture)"
    supervisor       = "m02-w02-cl01-sup01"
    vm_classes       = ["best-effort-small", "best-effort-medium", "best-effort-large"]
    storage_policies = ["ca-east-2-az1-gold01"]
    provider_gateway = "pg-ca-east-2-az1"
    edge_cluster     = "vcf-m02-w02-ec01"
    zones = [
      {
        name                   = "ca-east-2-az1"
        cpu_limit_mhz          = 1000000
        cpu_reservation_mhz    = 0
        memory_limit_mib       = 1024000
        memory_reservation_mib = 0
      }
    ]
  }
}
```

### Using outputs in the root module

```hcl
# Pass the org ID to another resource
resource "some_resource" "example" {
  org_id = module.vcfa_org.org_id
}

# Expose outputs at the root level
output "org_id" {
  value = module.vcfa_org.org_id
}

# Access a specific region's networking ID
output "east1_networking_id" {
  value = module.vcfa_org.regional_networking_ids["ca-east-1"]
}
```

## Inputs

| Name | Description | Type | Required |
|------|-------------|------|----------|
| `org` | Organization configuration | `object` | yes |
| `org.name` | Internal org name (unique identifier) | `string` | yes |
| `org.display_name` | Human-readable org name | `string` | yes |
| `org.description` | Org description | `string` | yes |
| `org.admin_name` | Local admin username | `string` | yes |
| `org.admin_password` | Local admin password | `string` | yes |
| `org.log_name` | Log identifier for org networking | `string` | yes |
| `regions` | Map of region configurations keyed by region name | `map(object)` | yes |
| `regions.<name>.vcenter` | vCenter name for this region | `string` | yes |
| `regions.<name>.supervisor` | Supervisor name for this region | `string` | yes |
| `regions.<name>.vm_classes` | List of VM class names to assign | `list(string)` | yes |
| `regions.<name>.storage_policies` | List of storage policy names to assign | `list(string)` | yes |
| `regions.<name>.provider_gateway` | Provider gateway name | `string` | yes |
| `regions.<name>.edge_cluster` | Edge cluster name | `string` | yes |
| `regions.<name>.zones` | List of availability zone configurations | `list(object)` | yes |
| `regions.<name>.zones[*].name` | Zone name | `string` | yes |
| `regions.<name>.zones[*].cpu_limit_mhz` | CPU limit in MHz (0 = unlimited) | `number` | yes |
| `regions.<name>.zones[*].cpu_reservation_mhz` | CPU reservation in MHz | `number` | yes |
| `regions.<name>.zones[*].memory_limit_mib` | Memory limit in MiB (0 = unlimited) | `number` | yes |
| `regions.<name>.zones[*].memory_reservation_mib` | Memory reservation in MiB | `number` | yes |

## Outputs

| Name | Description | Type |
|------|-------------|------|
| `org_id` | ID of the created organization | `string` |
| `org_networking_id` | ID of the org-level networking resource | `string` |
| `regional_networking_ids` | Map of region name → regional networking ID | `map(string)` |
| `region_quota_ids` | Map of region name → region quota ID | `map(string)` |

## Notes

- The `storage_limit_mib` for each storage policy quota is hardcoded to `1024 MiB`. Adjust in `main.tf` if you need per-policy limits.
- Region names used as map keys (e.g. `ca-east-1`) must match the region names registered in VCFA exactly, as they are used directly in `data "vcfa_region"` lookups.
- The provider configuration (URL, credentials) must be defined in the root module — this module inherits it automatically.
