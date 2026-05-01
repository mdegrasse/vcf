output "org_id" {
  description = "The ID of the created organization"
  value       = vcfa_org.this.id
}

output "org_networking_id" {
  description = "The ID of the org-level networking resource"
  value       = vcfa_org_networking.this.id
}

output "regional_networking_ids" {
  description = "Map of region name to regional networking resource ID"
  value       = { for k, v in vcfa_org_regional_networking.regional_networking : k => v.id }
}

output "region_quota_ids" {
  description = "Map of region name to region quota resource ID"
  value       = { for k, v in vcfa_org_region_quota.region_quotas : k => v.id }
}
