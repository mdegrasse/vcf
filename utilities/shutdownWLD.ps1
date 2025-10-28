Connect-VIServer -Server vcf-m02-w01-vc01.mdgvlabs.com -User "administrator@vsphere.local" -Password "VMware1!VMware1!"

Get-VM | Select Name,VMHost

Disconnect-VIServer -Server vcf-m02-w01-vc01.mdgvlabs.com -Confirm:$false


pywinrm
requests==2.28.1
urllib3==1.26.15
requests-credssp

pywinrm
requests
urllib3
pykerberos