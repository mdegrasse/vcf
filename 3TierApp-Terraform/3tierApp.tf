data "vra_blueprint" "this" {
  name = var.blueprint
}

data "vra_project" "this" {
  name = var.project
}

resource "vra_deployment" "this" {
  name        = var.deployment_name
  description = "Deployed from VCFA provider for Terraform."

  blueprint_id      = data.vra_blueprint.this.id
  project_id        = data.vra_project.this.id

  inputs = {
    instances = 2
  }

  timeouts {
    create = "60m"
    delete = "30m"
    update = "60m"
  }
}
