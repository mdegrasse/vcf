locals {
  names = {
    for i in vra_deployment.this.resources : i.name => i
  }
  #appsrv_ip     = jsondecode(local.names["Application-Server"].properties_json).address
  #dbsrv_ip      = jsondecode(local.names["Database-Server"].properties_json).address
  #websrv_ip     = jsondecode(local.names["Web-Server[0]"].properties_json).address
  
  all_resources = tolist(vra_deployment.this.resources)

  #webIds = {for r in local.all_resources : jsondecode(local.names[r.name].properties_json).resourceName => jsondecode(local.names[r.name].properties_json).externalId if strcontains(r.name, "Web-Server") }
  #appIds = {for r in local.all_resources : jsondecode(local.names[r.name].properties_json).resourceName => jsondecode(local.names[r.name].properties_json).externalId if strcontains(r.name, "Application-Server") }
  #DbIds  = {for r in local.all_resources : jsondecode(local.names[r.name].properties_json).resourceName => jsondecode(local.names[r.name].properties_json).externalId if strcontains(r.name, "Database-Server") }

  webIds = [ for r in local.all_resources : jsondecode(local.names[r.name].properties_json).externalId if strcontains(r.name, "Web-Server") ]
  appIds = [ for r in local.all_resources : jsondecode(local.names[r.name].properties_json).externalId if strcontains(r.name, "Application-Server") ]
  DbIds  = [ for r in local.all_resources : jsondecode(local.names[r.name].properties_json).externalId if strcontains(r.name, "Database-Server") ]

  webRn = [ for r in local.all_resources : jsondecode(local.names[r.name].properties_json).resourceName if strcontains(r.name, "Web-Server") ]
  appRn = [ for r in local.all_resources : jsondecode(local.names[r.name].properties_json).resourceName if strcontains(r.name, "Application-Server") ]
  DbRn  = [ for r in local.all_resources : jsondecode(local.names[r.name].properties_json).resourceName if strcontains(r.name, "Database-Server") ]
  LbRn  = [ for r in local.all_resources : jsondecode(local.names[r.name].properties_json).resourceName if strcontains(r.name, "Cloud_NSX_LoadBalancer") ]

  LbIP  = [ for r in local.all_resources : jsondecode(local.names[r.name].properties_json).address if strcontains(r.name, "Cloud_NSX_LoadBalancer") ]
}

output "webIds" {
      value = local.webIds
}
output "appIds" {
      value = local.appIds
}
output "DbIds" {
      value = local.DbIds
}

output "webIRn" {
      value = local.webRn
}
output "appRn" {
      value = local.appRn
}
output "DbRn" {
      value = local.DbRn
}
output "LbRn" {
      value = local.LbRn
}
output "LbIP" {
      value = local.LbIP
}

resource "nsxt_policy_group" "App-Server" {
  display_name = "SG-App-Server-${local.appRn[0]}"
  description  = "Terraform provisioned Group for App Servers"

  criteria {
    external_id_expression {
      member_type  = "VirtualMachine"
      external_ids = local.appIds[*]
    }
  }
}

resource "nsxt_policy_group" "Web-Server" {
  display_name = "SG-Web-Server-${local.LbRn[0]}"
  description  = "Terraform provisioned Group for Web Servers"

  criteria {
    external_id_expression {
      member_type  = "VirtualMachine"
      external_ids = local.webIds[*]
    }
  }
}

resource "nsxt_policy_group" "Database-Server" {
  display_name = "SG-Database-Server-${local.DbRn[0]}"
  description  = "Terraform provisioned Group for Database Servers"

  criteria {
    external_id_expression {
      member_type  = "VirtualMachine"
      external_ids = local.DbIds[*]
    }
  }
}

data "nsxt_policy_service" "ssh" {
  display_name = "SSH"
}

data "nsxt_policy_service" "https" {
  display_name = "HTTPS"
}

resource "nsxt_policy_security_policy" "SecureDatabase" {
  display_name = "Secure Database-${local.DbRn[0]}"
  description  = "Terraform provisioned Security Policy"
  category     = "Application"
  locked       = false
  stateful     = true
  tcp_strict   = false
  scope        = [nsxt_policy_group.Database-Server.path]

  rule {
    display_name       = "allowSSH"
    destination_groups = [nsxt_policy_group.Database-Server.path]
    action             = "ALLOW"
    services           = [data.nsxt_policy_service.ssh.path]
    logged             = true
    scope              = [nsxt_policy_group.Database-Server.path]
  }

  rule {
    display_name     = "allowTCP3306"
    source_groups    = [nsxt_policy_group.App-Server.path]
    destination_groups = [nsxt_policy_group.Database-Server.path]
    action           = "ALLOW"
    service_entries {
      l4_port_set_entry {
        display_name = "allowTCP3306"
        protocol     = "TCP"
        destination_ports = ["3306"]
      }  
    }
    logged           = true
    scope              = [nsxt_policy_group.Database-Server.path]
  }
 
  rule {
    display_name       = "dropALL"
    destination_groups = [nsxt_policy_group.Database-Server.path]
    action             = "DROP"
    logged             = true
    scope              = [nsxt_policy_group.Database-Server.path]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "nsxt_policy_security_policy" "SecureApplication" {
  display_name = "Secure Application-${local.appRn[0]}"
  description  = "Terraform provisioned Security Policy"
  category     = "Application"
  locked       = false
  stateful     = true
  tcp_strict   = false
  scope        = [nsxt_policy_group.App-Server.path]

  rule {
    display_name       = "allowSSH"
    destination_groups = [nsxt_policy_group.App-Server.path]
    action             = "ALLOW"
    services           = [data.nsxt_policy_service.ssh.path]
    logged             = true
    scope              = [nsxt_policy_group.App-Server.path]
  }

  rule {
    display_name       = "allowHTTPS"
    source_groups      = [nsxt_policy_group.Web-Server.path]
    destination_groups = [nsxt_policy_group.App-Server.path]
    action           = "ALLOW"
    service_entries {
      l4_port_set_entry {
        display_name = "allowTCP8443"
        protocol     = "TCP"
        destination_ports = ["8443"]
      }  
    }
    logged           = true
    scope            = [nsxt_policy_group.App-Server.path]
  }

    rule {
    display_name       = "dropALL"
    destination_groups = [nsxt_policy_group.App-Server.path]
    action             = "DROP"
    logged             = true
    scope              = [nsxt_policy_group.App-Server.path]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "nsxt_policy_security_policy" "SecureWeb" {
  display_name = "Secure Web-${local.LbRn[0]}"
  description  = "Terraform provisioned Security Policy"
  category     = "Application"
  locked       = false
  stateful     = true
  tcp_strict   = false
  scope        = [nsxt_policy_group.Web-Server.path]

  rule {
    display_name       = "allowSSH"
    destination_groups = [nsxt_policy_group.Web-Server.path]
    action             = "ALLOW"
    services           = [data.nsxt_policy_service.ssh.path]
    logged             = true
    scope              = [nsxt_policy_group.Web-Server.path]
  }

  rule {
    display_name       = "allowHTTPS"
    source_groups      = local.LbIP
    destination_groups = [nsxt_policy_group.Web-Server.path]
    action             = "ALLOW"
    services           = [data.nsxt_policy_service.https.path]
    logged             = true
    scope              = [nsxt_policy_group.Web-Server.path]
  }

    rule {
    display_name       = "dropALL"
    destination_groups = [nsxt_policy_group.Web-Server.path]
    action             = "DROP"
    logged             = true
    scope              = [nsxt_policy_group.Web-Server.path]
  }

  lifecycle {
    create_before_destroy = true
  }
}