data "vcfa_role" "org_admin" {
  org_id = vcfa_org.this.id
  name   = "Organization Administrator"
}

data "vcfa_role" "org_user" {
  org_id = vcfa_org.this.id
  name   = "Organization User"
}

resource "vcfa_org" "this" {
  name              = var.org.name
  display_name      = var.org.display_name
  description       = var.org.description
  is_enabled        = true
  is_classic_tenant = false
}

resource "vcfa_org_local_user" "admin" {
  org_id   = vcfa_org.this.id
  role_ids = [data.vcfa_role.org_admin.id, data.vcfa_role.org_user.id]
  username = var.org.admin_name
  password = var.org.admin_password
}

resource "vcfa_org_networking" "this" {
  org_id   = vcfa_org.this.id
  log_name = var.org.log_name
}

data "vcfa_region" "regions" {
  for_each = var.regions
  name     = each.key
}

data "vcfa_vcenter" "vcenter" {
  for_each = var.regions
  name     = each.value.vcenter
}

data "vcfa_supervisor" "supervisors" {
  for_each   = var.regions
  name       = each.value.supervisor
  vcenter_id = data.vcfa_vcenter.vcenter[each.key].id
}

data "vcfa_provider_gateway" "provider_gateway" {
  for_each  = var.regions
  name      = each.value.provider_gateway
  region_id = data.vcfa_region.regions[each.key].id
}

data "vcfa_edge_cluster" "edge_cluster" {
  for_each  = var.regions
  name      = each.value.edge_cluster
  region_id = data.vcfa_region.regions[each.key].id
}

locals {
  vm_classes = merge([
    for region, config in var.regions : {
      for class in config.vm_classes :
      "${region}-${class}" => {
        region = region
        class  = class
      }
    }
  ]...)

  storage_policies = merge([
    for region, config in var.regions : {
      for policy in config.storage_policies :
      "${region}-${policy}" => {
        region = region
        policy = policy
      }
    }
  ]...)

  region_zones = merge([
    for region, config in var.regions : {
      for zone in config.zones :
      "${region}-${zone.name}" => {
        region = region
        zone   = zone
      }
    }
  ]...)

  region_vm_class_ids = {
    for region in keys(var.regions) :
    region => [
      for k, v in data.vcfa_region_vm_class.vm_classes :
      v.id if startswith(k, "${region}-")
    ]
  }

  region_storage_policy_ids = {
    for region in keys(var.regions) :
    region => [
      for k, v in data.vcfa_region_storage_policy.storage_policies :
      v.id if startswith(k, "${region}-")
    ]
  }
}

data "vcfa_region_zone" "zones" {
  for_each  = local.region_zones
  region_id = data.vcfa_region.regions[each.value.region].id
  name      = each.value.zone.name
}

data "vcfa_region_vm_class" "vm_classes" {
  for_each  = local.vm_classes
  region_id = data.vcfa_region.regions[each.value.region].id
  name      = each.value.class
}

data "vcfa_region_storage_policy" "storage_policies" {
  for_each  = local.storage_policies
  region_id = data.vcfa_region.regions[each.value.region].id
  name      = each.value.policy
}

resource "vcfa_org_regional_networking" "regional_networking" {
  for_each            = var.regions
  name                = each.key
  org_id              = vcfa_org_networking.this.id
  region_id           = data.vcfa_region.regions[each.key].id
  provider_gateway_id = data.vcfa_provider_gateway.provider_gateway[each.key].id
  edge_cluster_id     = data.vcfa_edge_cluster.edge_cluster[each.key].id
  depends_on          = [vcfa_org_networking.this]
}

resource "vcfa_org_region_quota" "region_quotas" {
  for_each = var.regions

  org_id    = vcfa_org.this.id
  region_id = data.vcfa_region.regions[each.key].id

  supervisor_ids      = [data.vcfa_supervisor.supervisors[each.key].id]
  region_vm_class_ids = local.region_vm_class_ids[each.key]

  dynamic "zone_resource_allocations" {
    for_each = {
      for k, v in local.region_zones :
      k => v if v.region == each.key
    }

    content {
      region_zone_id         = data.vcfa_region_zone.zones[zone_resource_allocations.key].id
      cpu_limit_mhz          = zone_resource_allocations.value.zone.cpu_limit_mhz
      cpu_reservation_mhz    = zone_resource_allocations.value.zone.cpu_reservation_mhz
      memory_limit_mib       = zone_resource_allocations.value.zone.memory_limit_mib
      memory_reservation_mib = zone_resource_allocations.value.zone.memory_reservation_mib
    }
  }

  dynamic "region_storage_policy" {
    for_each = local.region_storage_policy_ids[each.key]

    content {
      region_storage_policy_id = region_storage_policy.value
      storage_limit_mib        = 1024
    }
  }
}
