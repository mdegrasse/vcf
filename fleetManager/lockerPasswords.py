import requests
import urllib3
import base64
import argparse
import getpass

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

######## Functions #########

def getPassword(alias):
    for entry in passwords:
        #print ("Password Alias: [" + entry["alias"] + "]")
        if (entry["alias"] == alias):
            print ("Password Alias: [" + entry["alias"] + "] *** Referenced: " + str(entry["referenced"]) + " ***")
            vmid = entry["vmid"]
            return vmid
    print("VMID does not exist for alias " + alias +"! exiting")
    exit(1)
    return 0

def getPasswords():
    # --- Make the GET request ---
    try:
        response = requests.get(getPasswordsURL, headers=headers, verify=False)
        response.raise_for_status()  # Raise error for bad status codes
    except requests.exceptions.RequestException as e:
        print(f"Authentication failed: {e}")
        exit(1)
    passwords = response.json()
    return passwords

def getDecryptedPassword(alias):
    # --- Get VMID ---
    vmid = getPassword(alias)
    getDecryptedPasswordURL = baseUrl + "/lcm/locker/api/v2/passwords/" + vmid + "/decrypted" 
    payload = { "rootPassword": fleetManagerRootPassword }
    # --- Make the POST request ---
    try:
        response = requests.post(getDecryptedPasswordURL, json=payload, headers=headers, verify=False)
        response.raise_for_status()  # Raise error for bad status codes
        # Parse and print the token (adjust key name as needed)
        data = response.json()
        print (data)
    except requests.exceptions.RequestException as e:
        print(f"Authentication failed: {e}")

def listPasswords():
    for entry in passwords:
        print ("Password Alias: [" + entry["alias"] + "] *** Referenced: " + str(entry["referenced"]) + " ***")

def deletePassword(alias):
    vmid = getPassword(alias)
    # --- Make the DELETE request ---
    try:
        response = requests.delete(getPasswordsURL+"/"+vmid, headers=headers, verify=False)
        response.raise_for_status()  # Raise error for bad status codes
    except requests.exceptions.RequestException as e:
        print(f"Delete failed for vmid {vmid}: {e}")
        print(response.json())
        exit(1) 
    print(str(response))

def getBasicAuth(username, password):
    credentials = f"{username}:{password}"
    credentials_bytes = credentials.encode("utf-8")
    base64_bytes = base64.b64encode(credentials_bytes)
    return base64_bytes.decode("utf-8")

########  Main #########

parser = argparse.ArgumentParser(description="Fleet Manager locker management")
parser.add_argument('--username', type=str, help='fleet manager username')
parser.add_argument('--password', type=str, help='fleet manager password')
parser.add_argument('--rootpassword', type=str, required=False, help='fleet manager root password, required to decrypt passwords')
parser.add_argument('-l', '--listpasswords', help='list password aliases', action='store_true')
parser.add_argument('-a', '--alias', type=str, help='decrypt provided password alias')
parser.add_argument('-s', '--server', type=str, help='FQDN of fleet manager')
parser.add_argument('-d', '--delete', type=str, help='Delete provided password alias')

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
getPasswordsURL = baseUrl + '/lcm/locker/api/passwords'

# Connect to fleet manager and collect password inventory
passwords = getPasswords()

# execute requests from cli

# list password aliases
if (args.listpasswords):
    listPasswords()

# display decrypted password for specified alias
if (args.alias):
    if(not args.rootpassword):
        fleetManagerRootPassword = getpass.getpass("LCM root password must be provided to decrypt passwords: ")
    else:
        fleetManagerRootPassword = args.rootpassword
    getDecryptedPassword(args.alias)

# delete specified alias from fleet manager
if (args.delete):
    deletePassword(args.delete)
