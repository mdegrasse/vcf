"""
VCF Fleet Locker Password Viewer

Supports two backends:
  sddc - SDDC Manager API (GET /v1/credentials) — direct credential locker lookup
  lcm  - VCF Fleet Manager
         Also known as Aria Suite Lifecycle Manager locker API (GET /lcm/locker/api/v2/passwords)
         Also known as vRealize Suite Lifecycle Manager in older versions

Usage:
  python3 vcf_locker.py                           # fully interactive
  python3 vcf_locker.py --backend sddc --sddc sddc.example.com
  python3 vcf_locker.py --backend lcm --lcm lcm.example.com
  python3 vcf_locker.py --show-passwords --no-verify-ssl
"""

__author__ = "Marc De Grasse"
__version__ = "0.1.1"

import argparse
import getpass
import json
import sys
import urllib.request
import urllib.error
import ssl
from typing import Optional


# ── SDDC Manager constants ────────────────────────────────────────────────────

SDDC_RESOURCE_TYPES = [
    "VCENTER",
    "PSC",
    "ESXI",
    "NSXT_MANAGER",
    "SDDC_MANAGER",
    "BACKUP",
    "NSX_ALB",
]

SDDC_ACCOUNT_TYPES = [
    "USER",
    "SERVICE",
    "SYSTEM",
]

SDDC_CREDENTIAL_TYPES = [
    "SSH",
    "API",
    "AUDIT",
    "FTP",
    "SSO",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_ssl_ctx(verify: bool) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def http_json(
    url: str,
    headers: dict,
    body: Optional[str | bytes] = None,
    method: str = "GET",
    ctx: ssl.SSLContext = None,
) -> dict | list:
    if isinstance(body, str):
        body = body.encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read())


def prompt_choice(label: str, choices: list[str]) -> Optional[str]:
    print(f"\n{label}:")
    print("  0. All")
    for i, c in enumerate(choices, 1):
        print(f"  {i}. {c}")
    while True:
        raw = input("Enter number (or press Enter for All): ").strip()
        if not raw:
            return None
        try:
            n = int(raw)
        except ValueError:
            print("Invalid input.")
            continue
        if n == 0:
            return None
        if 1 <= n <= len(choices):
            return choices[n - 1]
        print("Invalid selection.")


def filter_in_use(rows: list[dict], in_use_filter: Optional[str]) -> list[dict]:
    if not in_use_filter:
        return rows
    keep = in_use_filter.lower() == "yes"
    return [r for r in rows if bool(r.get("referenced")) == keep]


def print_table(rows: list[dict], cols: list[tuple[str, str, int]], show_passwords: bool) -> None:
    if not rows:
        print("No credentials found.")
        return
    header = "  ".join(f"{label:<{width}}" for label, _, width in cols)
    print(header)
    print("-" * len(header))
    for row in rows:
        parts = []
        for label, key, width in cols:
            val = row.get(key, "")
            if label == "Password":
                val = val if show_passwords else "***hidden***"
            parts.append(f"{str(val)[:width]:<{width}}")
        print("  ".join(parts))


# ── SDDC Manager backend ──────────────────────────────────────────────────────

def sddc_get_token(fqdn: str, username: str, password: str, ctx: ssl.SSLContext) -> str:
    data = http_json(
        f"https://{fqdn}/v1/tokens",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        body=json.dumps({"username": username, "password": password}),
        method="POST",
        ctx=ctx,
    )
    token = data.get("accessToken") or data.get("access_token") or data.get("token")
    if not token:
        raise ValueError(f"Could not parse token from response: {data}")
    return token


def sddc_get_credentials(
    fqdn: str,
    token: str,
    ctx: ssl.SSLContext,
    resource_type: Optional[str],
    account_type: Optional[str],
) -> list[dict]:
    params = []
    if resource_type:
        params.append(f"resourceType={resource_type}")
    if account_type:
        params.append(f"accountType={account_type}")
    qs = "&".join(params)
    url = f"https://{fqdn}/v1/credentials" + (f"?{qs}" if qs else "")
    data = http_json(url, headers={"Accept": "application/json", "Authorization": f"Bearer {token}"}, ctx=ctx)
    return data.get("elements", data) if isinstance(data, dict) else data


def sddc_flatten(creds: list[dict]) -> list[dict]:
    rows = []
    for c in creds:
        resource = c.get("resource", {})
        rows.append({
            "Domain":          resource.get("domainName", ""),
            "Resource":        resource.get("resourceName",""),
            "Resource Type":   resource.get("resourceType",""),
            "Account Type":    c.get("accountType", ""),
            "Credential Type": c.get("credentialType", ""),
            "Username":        c.get("username", ""),
            "Password":        c.get("password", ""),
        })
    return rows


def run_sddc(args: argparse.Namespace) -> None:
    fqdn = args.sddc or input("SDDC Manager FQDN/IP: ").strip()
    username = args.username or input("Username [admin@local]: ").strip() or "admin@local"
    password = args.password or getpass.getpass("Password: ")
    resource_type = args.resource_type
    account_type = args.account_type
    credential_type = args.credential_type

    ctx = make_ssl_ctx(not args.no_verify_ssl)

    print(f"\nAuthenticating to SDDC Manager ({fqdn})...")
    token = sddc_get_token(fqdn, username, password, ctx)

    print("Fetching credentials from locker...")
    raw = sddc_get_credentials(fqdn, token, ctx, resource_type, account_type)
    rows = sddc_flatten(raw)
    if credential_type:
        rows = [r for r in rows if r.get("Credential Type", "").upper() == credential_type.upper()]

    print(f"\nFound {len(rows)} credential(s)\n")
    cols = [
        ("Domain",          "Domain",          10),
        ("Resource",        "Resource",        36),
        ("Resource Type",   "Resource Type",   12),
        ("Account Type",    "Account Type",    12),
        ("Credential Type", "Credential Type", 12),
        ("Username",        "Username",        36),
        ("Password",        "Password",        40),
    ]
    print_table(rows, cols, args.show_passwords)


# ── Aria Suite Lifecycle Manager (LCM) locker backend ────────────────────────

import base64 as _base64


def lcm_basic_auth(username: str, password: str) -> str:
    token = _base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def lcm_get_passwords(fqdn: str, auth_header: str, ctx: ssl.SSLContext) -> list[dict]:
    headers = {"Accept": "application/json", "Authorization": auth_header}
    all_passwords: list[dict] = []
    start = 0
    page_size = 100

    while True:
        data = http_json(
            f"https://{fqdn}/lcm/locker/api/v2/passwords?from={start}&size={page_size}",
            headers=headers,
            ctx=ctx,
        )
        if isinstance(data, list):
            return data
        page_passwords = data.get("passwords", "")
        all_passwords.extend(page_passwords)
        total = data.get("total","")
        if len(all_passwords) >= int(total) or not page_passwords:
            break
        start += page_size

    return all_passwords


def lcm_get_decrypted_password(
    fqdn: str, vmid: str, auth_header: str, root_password: str, ctx: ssl.SSLContext
) -> str:
    data = http_json(
        f"https://{fqdn}/lcm/locker/api/v2/passwords/{vmid}/decrypted",
        headers={"Accept": "application/json", "Content-Type": "application/json", "Authorization": auth_header},
        body= json.dumps({ "rootPassword": root_password }),
        method="POST",
        ctx=ctx,
    )
    #print(f"Decrypted password for VMID {vmid} {data.get("password")}")
    return data.get("password", "")


def lcm_flatten(
    passwords: list[dict],
    fqdn: str,
    auth_header: str,
    root_password: Optional[str],
    ctx: ssl.SSLContext,
    show_passwords: bool,
) -> list[dict]:
    rows = []
    for p in passwords:

        if show_passwords and root_password:
            vmid = p.get("vmid", "")
            try:
                clear = lcm_get_decrypted_password(fqdn, vmid, auth_header, root_password, ctx)
            except Exception:
                clear = "<decryption failed>"
        else:
            clear = p.get("password", "")

        rows.append({
            "VMID":            p.get("vmid", ""),
            "Alias":           p.get("alias", ""),
            "Username":        p.get("userName", ""),
            "Description":     p.get("passwordDescription", ""),
            "referenced":      p.get("referenced", False),
            "In Use":          p.get("referenced", False),
            "Password":        clear,
        })
    return rows


def run_lcm(args: argparse.Namespace) -> None:
    fqdn = args.lcm or input("Aria LCM FQDN/IP: ").strip()
    username = args.username or input("Username [admin@local]: ").strip() or "admin@local"
    password = args.password or getpass.getpass("Password: ")

    root_password: Optional[str] = None
    if args.show_passwords:
        root_password = args.lcm_root_password or getpass.getpass("LCM appliance root password (for decryption): ")

    ctx = make_ssl_ctx(not args.no_verify_ssl)
    auth_header = lcm_basic_auth(username, password)

    print(f"\nFetching passwords from Aria Suite Lifecycle Manager ({fqdn})...")
    raw = lcm_get_passwords(fqdn, auth_header, ctx)

    if args.show_passwords and root_password:
        print(f"Decrypting {len(raw)} password(s)...")
    rows = lcm_flatten(raw, fqdn, auth_header, root_password, ctx, args.show_passwords)
    rows = filter_in_use(rows, args.in_use)

    print(f"\nFound {len(rows)} password(s)\n")
    cols = [
      #  ("VMID",        "VMID",        36),
        ("Alias",       "Alias",       50),
        ("Username",    "Username",    16),
        ("Description", "Description", 40),
        ("In Use",          "In Use",          6),
        ("Password",        "Password",        30),
    ]
    print_table(rows, cols, args.show_passwords)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Display VCF fleet locker passwords",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--backend", choices=["sddc", "lcm"],
        help="API backend: sddc (SDDC Manager) or lcm (VCF Fleet Manager / Aria LCM)",
    )

    # SDDC Manager options
    sddc_grp = parser.add_argument_group("SDDC Manager backend (--backend sddc)")
    sddc_grp.add_argument("--sddc", metavar="FQDN", help="SDDC Manager FQDN or IP")
    sddc_grp.add_argument("--resource-type", choices=SDDC_RESOURCE_TYPES, help="Filter by resource type")
    sddc_grp.add_argument("--account-type", choices=SDDC_ACCOUNT_TYPES, help="Filter by account type")
    sddc_grp.add_argument("--credential-type", choices=SDDC_CREDENTIAL_TYPES, help="Filter by credential type (e.g. SSH, SSO, API)")

    # Aria LCM options
    lcm_grp = parser.add_argument_group("VCF Fleet Manager / Aria LCM backend (--backend lcm)")
    lcm_grp.add_argument("--lcm", metavar="FQDN", help="VCF Fleet Manager / Aria LCM FQDN or IP")
    lcm_grp.add_argument("--lcm-root-password", metavar="PASS", help="LCM appliance root password for decrypting locker passwords")

    # Shared options
    parser.add_argument("--username", metavar="USER", help="Username")
    parser.add_argument("--password", metavar="PASS", help="Password")
    parser.add_argument("--show-passwords", action="store_true", help="Display passwords in plaintext")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Skip TLS certificate verification")
    parser.add_argument("--in-use", choices=["yes", "no"], help="Show only credentials that are (yes) or are not (no) in use")

    args = parser.parse_args()

    backend = args.backend
    if not backend:
        print("Select backend:")
        print("  1. SDDC Manager API (GET /v1/credentials)")
        print("  2. VCF Fleet Manager / Aria Suite Lifecycle Manager locker (LCM / vRSLCM)")
        raw = input("Enter number [1]: ").strip() or "1"
        backend = {"1": "sddc", "2": "lcm"}.get(raw, "sddc")

    if not args.no_verify_ssl:
        confirm = input("Trust unsigned/self-signed certificates? [y/N]: ").strip().lower()
        args.no_verify_ssl = confirm == "y"

    if not args.show_passwords:
        confirm = input("Show passwords in plaintext? [y/N]: ").strip().lower()
        args.show_passwords = confirm == "y"

    try:
        if backend == "sddc":
            run_sddc(args)
        else:
            run_lcm(args)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"\nHTTP {e.code} {e.reason}: {body}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
