variable url {
  type = string
}

variable refresh_token {
  type = string
}

variable insecure {
  type = bool
}

variable project {
  type = string
}

variable blueprint {
  type = string
}

variable deployment_name {
  type = string
}

variable "nsx_manager" {}

variable "nsx_username" {
    default = "admin"
}

variable "nsx_password" {}

variable "nsx_project" {
    default = "default"
}