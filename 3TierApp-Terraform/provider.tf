terraform {
  required_providers {
    nsxt = {
      source = "vmware/nsxt"
      version = "3.9.0"
    }
    vra = {
      source  = "vmware/vra"
      version = ">= 0.15.0"
    }
  }
}

provider "vra" {
  url           = var.url
  refresh_token = var.refresh_token
  organization = "mdgvlabs"
  insecure      = true
}

provider "nsxt" {
  host                  = var.nsx_manager
  username              = var.nsx_username
  password              = var.nsx_password
  allow_unverified_ssl  = true
}