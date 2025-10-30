import requests
import urllib3
import base64
import argparse
import getpass
import json
import time

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

__author__ = "Marc De Grasse"
__version__ = "0.1.0"

######## Functions #########

def getCertificate(vmid):
    for entry in certificates:
        #print ("Certificate vmid: [" + entry["vmid"] + "]")
        if (entry["vmid"] == vmid):
            print ("\nCertificate Info: \nAlias: "+ entry["alias"] + "\nVMID:  [" + entry["vmid"] + "]\nReferences: " + str(entry["references"])+"\n")
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

def getCertificateReferences(vmid):
    # --- Make the GET request ---
    try:
        response = requests.get(baseUrl + "/lcm/locker/api/references/ungrouped/"+vmid, headers=headers, verify=False, params='size=1000')
        response.raise_for_status()  # Raise error for bad status codes
    except requests.exceptions.RequestException as e:
        print(f"Get certificate references failed: {e}")
        exit(1)
    references = response.json()["references"]
    return references

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
        #print (data)
    except requests.exceptions.RequestException as e:
        print(f"Authentication failed: {e}")

def listCertificates():
    for entry in certificates:
        print ("Certificate Alias: [" + entry["alias"] + "] *** VMID: " + str(entry["vmid"]) + " ***")

def findCertificateAssignedToOps():
    for entry in certificates:
        destinationNames = getCertificateReferences(entry["vmid"]) #might have multiple destinations/assignments
        for destination in destinationNames: #loop to find the vrops one
            if (destination["destinationName"] == "vrops"):
                print("\nFound VROPS reference: assigned to cert alias:[" + entry["alias"] + "] and vmid:[" + entry["vmid"]+"]\n")
                return entry["vmid"]
    return "NOTFOUND"

def createPrevalidateCertificateReplacementTask(newVmid, oldVmid, references):
    validateJson = {
        "certificateId": newVmid,
        "refRequestDTOList": references,
        "vmid": oldVmid,
        "retrustProdMeta":{"retrustVidmCertProdList":[]}
    }
    # --- Make the POST request ---
    try:
        response = requests.post(baseUrl + "/lcm/locker/api/certificates/replace/prevalidate/" + oldVmid, json=validateJson, headers=headers, verify=False)
        response.raise_for_status()  # Raise error for bad status codes
        # Parse
        data = response.json()
        #print (data)
    except requests.exceptions.RequestException as e:
        print(f"Prevalidation task creation failed: {e}")
        print(f"Are you sure you provided the correct certificate VMID to use as a replacement?")
        exit(1)
    print("Task created, request ID is " + data["requestId"])
    return data["requestId"]

def getPreValidationReport(taskId):
    #Polls for a prevalidation report and prints results.
    url = f"{baseUrl}/lcm/request/api/prevalidationreport?requestId={taskId}"
    timeout = 60

    while timeout > 0:
        try:
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve prevalidation report: {e}")
            exit(1)

        state = data.get("requestState")
        if state in ("FAILED", "COMPLETED"):
            success = (state == "COMPLETED")
            msg = "completed successfully" if success else "did not complete successfully"
            print(f"Prevalidation task {msg}. Here are the details:")
            print("-" * 60)

            for child in data.get("rootValidations", [{}])[0].get("childElements", []):
                print(f"Check Name : {child.get('checkName')}")
                print(f"Check Type : {child.get('checkType')}")
                print(f"Status     : {child.get('status')}")
                print(f"Description: {child.get('resultDescription')}")
                print("-" * 60)

            if not success:
                exit(1)
            return

        print("Waiting for task to complete... Pausing for 5 secs...")
        time.sleep(5)
        timeout -= 5

    print("Task took too long to complete. Aborting.")
    exit(1)

def replaceOpsCertificate(newVmid, oldVmid, references):
    validateJson = {
        "certificateId": newVmid,
        "refRequestDTOList": references,
        "vmid": oldVmid,
        "retrustProdMeta":{"retrustVidmCertProdList":[]}
    }
    #print(json.dumps(validateJson))
    # --- Make the POST request ---
    try:
        response = requests.post(baseUrl + "/lcm/locker/api/certificates/replace/" + oldVmid, json=validateJson, headers=headers, verify=False)
        response.raise_for_status()  # Raise error for bad status codes
    except requests.exceptions.RequestException as e:
        print(f"Replace certificate task creation failed: {e}")
        exit(1)
    print("VCF Operations Certificate [" + getCertificate(oldVmid)["alias"] + "] has successfully been replaced with certificate [" + getCertificate(newVmid)["alias"]+"]")

def isCertificateReferenced(vmid):
    cert = getCertificate(vmid)
    referenced = cert["references"]["environments"] #check if cert is currently used
    if (len(referenced) > 0): #if there are any references
        return True
    else:
        return False

def deleteCertificate(vmid):
    if isCertificateReferenced(vmid):
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
parser.add_argument('-l', '--listcerts', help='list certificate aliases', action='store_true')
parser.add_argument('-c', '--createcert', help='create new certificate. Provide path to json file that contains certificate info', type=str)
parser.add_argument('-s', '--server', type=str, help='FQDN of fleet manager')
parser.add_argument('-d', '--deletecert', type=str, help='Delete provided certificate vmid', metavar='ALIAS')
parser.add_argument('-x', '--fixops', type=str, help='Replace fresh installed VCF Operations certificate. Provide vmid of new certificate to replace with.')

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

if (args.fixops):
    #lets find if vrops has cert assigned
    opsCertVmid = findCertificateAssignedToOps()
    if opsCertVmid == "NOTFOUND":
        print("Could not find certificate assigned to VROPS. Exiting...")
        exit(1)
    if getCertificate(args.fixops): #1st, does cert to be used exist?
        #2nd, is it valid? lets check
        taskId = createPrevalidateCertificateReplacementTask(args.fixops, opsCertVmid, getCertificateReferences(opsCertVmid))
        #if we got here, the task creation was successful, now poll for results
        time.sleep(5)
        getPreValidationReport(taskId)
        #if we got here , all is good, lets make the cert swap
        replaceOpsCertificate(args.fixops, opsCertVmid, getCertificateReferences(opsCertVmid))

# list certificates aliases
if (args.listcerts):
    listCertificates()

# create certificates using json from file
if (args.createcert):
    with open(args.createcert) as f:
        d = json.load(f)
        print(d)
    createCertificate(d)
  
# delete specified alias from fleet manager
if (args.deletecert):
    deleteCertificate(args.deletecert)


