variable "org" {
  description = "Organization configuration"
  type = object({
    name           = string
    display_name   = string
    description    = string
    admin_name     = string
    admin_password = string
    log_name       = string
  })
}

variable "regions" {
  description = "Map of regions and their resource configurations"
  type = map(object({
    vcenter          = string
    supervisor       = string
    vm_classes       = list(string)
    storage_policies = list(string)
    provider_gateway = string
    edge_cluster     = string

    zones = list(object({
      name                   = string
      cpu_limit_mhz          = number
      cpu_reservation_mhz    = number
      memory_limit_mib       = number
      memory_reservation_mib = number
    }))
  }))
}
