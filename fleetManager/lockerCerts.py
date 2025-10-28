import requests
import urllib3
import base64
import argparse
import getpass
import json

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

__author__ = "Marc De Grasse"
__version__ = "0.1.0"

######## Functions #########

def getCertificate(vmid):
    for entry in certificates:
        #print ("Certificate vmid: [" + entry["vmid"] + "]")
        if (entry["vmid"] == vmid):
            print ("Certificate vmid: [" + entry["vmid"] + "] *** Referenced: " + str(entry["references"]) + " ***")
            return entry
    print("Certificate entry does not exist for vmid " + vmid +"! exiting")
    exit(1)

def getCertificates():
    # --- Make the GET request ---
    try:
        response = requests.get(getCertificatesURL, headers=headers, verify=False, params='size=1000')
        response.raise_for_status()  # Raise error for bad status codes
    except requests.exceptions.RequestException as e:
        print(f"Authentication failed: {e}")
        exit(1)
    certificates = response.json()["certificates"]
    return certificates

def createCertificate(certJson):
    # --- Get VMID ---
    createCertUrl = baseUrl + "/lcm/locker/api/v2/certificates" 
    print(createCertUrl)
    # --- Make the POST request ---
    try:
        response = requests.post(createCertUrl, json=certJson, headers=headers, verify=False)
        response.raise_for_status()  # Raise error for bad status codes
        # Parse and print the token (adjust key name as needed)
        data = response.json()
        print (data)
    except requests.exceptions.RequestException as e:
        print(f"Authentication failed: {e}")

def listCertificates():
    for entry in certificates:
        print ("Certificate Alias: [" + entry["alias"] + "] *** VMID: " + str(entry["vmid"]) + " ***")

def deleteCertificate(vmid):
    cert = getCertificate(vmid)
    referenced = cert["references"]["environments"] #check if cert is currently used
    if (len(referenced) > 0):
        print('Certificate vmid ' + vmid + ' is currenty in use, cannot delete.')
        exit(1)
    # --- Make the DELETE request ---
    try:
        response = requests.delete(deleteCertificatesURL+"/"+vmid, headers=headers, verify=False)
        response.raise_for_status()  # Raise error for bad status codes
    except requests.exceptions.RequestException as e:
        print(f"Delete failed for certificate with vmid {vmid}: {e}")
        print(response.json())
        exit(1)
    print(str(response))
    if (response.status_code == 200):
        print("Certificate vmid " + vmid + " was deleted successfuly.")

def getBasicAuth(username, password):
    credentials = f"{username}:{password}"
    credentials_bytes = credentials.encode("utf-8")
    base64_bytes = base64.b64encode(credentials_bytes)
    return base64_bytes.decode("utf-8")

########  Main #########

parser = argparse.ArgumentParser(description="Fleet Manager password locker management", epilog='Used to list password aliases and delete password aliases from fleet manager password locker')
parser.add_argument('-u', '--username', type=str, help='fleet manager admin username')
parser.add_argument('-p', '--password', type=str, help='fleet manager admin password')
#parser.add_argument('-r', '--rootpassword', type=str, required=False, help='fleet manager root password, required to decrypt passwords')
parser.add_argument('-l', '--listcerts', help='list certificate aliases', action='store_true')
parser.add_argument('-c', '--createcert', help='create new certificate', type=str)
#parser.add_argument('-f', '--certfile', help='json file that has certificate info', type=str)
parser.add_argument('-s', '--server', type=str, help='FQDN of fleet manager')
parser.add_argument('-d', '--deletecert', type=str, help='Delete provided certificate vmid', metavar='ALIAS')

args = parser.parse_args()

# check username
if (args.username):
    username=args.username
else:
    username=input("input lcm admin username: ")

# check password
if (args.password):
    password=args.password
else:
    password = getpass.getpass("input lcm admin password: ")

# check server
if (args.server):
    server=args.server
else:
    server = input("FQDN of fleet manager (lcm): ")

basicAuth = getBasicAuth(username, password)

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Basic ' + basicAuth
}

baseUrl = 'https://' + server
getCertificatesURL = baseUrl + '/lcm/locker/api/v3/certificates?limit=1000'
deleteCertificatesURL = baseUrl + '/lcm/locker/api/v2/certificates'

# Connect to fleet manager and collect password inventory
certificates = getCertificates()

# execute requests from cli

# list certificates aliases
if (args.listcerts):
    listCertificates()

# create certificates using json from file
if (args.createcert):
    with open(args.createcert) as f:
        d = json.load(f)
        print(d)
    createCertificate(d)
else:
    print(f"Filename must be provided for certificate")

    

# delete specified alias from fleet manager
if (args.deletecert):
    deleteCertificate(args.deletecert)


#https://fleetmgr.mdgvlabs.com/lcm/locker/api/certificates/replace/3226444a-b732-4653-9866-dc36bb2373ef

#POST