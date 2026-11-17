#!/usr/bin/env python3
"""
Disable MV Sense on cameras in a Meraki organization (or a single network).

Disabling Sense on a camera releases its MV Sense license so it can be
reused elsewhere. Uses:
  - organizations.getOrganizationNetworks
  - organizations.getOrganizationDevices
  - camera.getDeviceCameraSense
  - camera.updateDeviceCameraSense  (PUT /devices/{serial}/camera/sense)

A CSV report of every camera processed (serial, status, etc.) is always written.

Usage:
  export MERAKI_DASHBOARD_API_KEY=your_key
  pip install meraki

  python disable_mv_sense.py --org-id 123456                          # dry run, whole org
  python disable_mv_sense.py --org-id 123456 --network-id N_123       # dry run, one network
  python disable_mv_sense.py --org-id 123456 --apply                  # make changes
  python disable_mv_sense.py --org-id 123456 --csv-out cameras.csv    # custom CSV path
"""

import argparse
import csv
import os
import sys
from datetime import datetime

import meraki

CSV_FIELDS = ["serial", "name", "model", "network_id", "network_name", "status", "detail"]


def main():
    parser = argparse.ArgumentParser(description="Disable MV Sense on cameras in a Meraki org.")
    parser.add_argument("--org-id", required=True, help="Meraki organization ID")
    parser.add_argument("--network-id",
                        help="Only process cameras in this network (default: whole organization)")
    parser.add_argument("--csv-out",
                        help="Path for the CSV report (default: mv_sense_<timestamp>.csv)")
    parser.add_argument("--apply", action="store_true",
                        help="Actually make changes (default is a dry run)")
    args = parser.parse_args()

    api_key = os.environ.get("MERAKI_DASHBOARD_API_KEY")
    if not api_key:
        sys.exit("Set the MERAKI_DASHBOARD_API_KEY environment variable.")

    csv_path = args.csv_out or f"mv_sense_{datetime.now():%Y%m%d_%H%M%S}.csv"

    dashboard = meraki.DashboardAPI(
        api_key,
        output_log=False,
        print_console=False,
        suppress_logging=True,
        maximum_retries=5,        # retries on 429 rate limiting
        wait_on_rate_limit=True,
    )

    # Map network IDs to names for the report
    networks = dashboard.organizations.getOrganizationNetworks(args.org_id, total_pages="all")
    network_names = {n["id"]: n["name"] for n in networks}

    if args.network_id and args.network_id not in network_names:
        sys.exit(f"Network {args.network_id} was not found in organization {args.org_id}.")

    # Fetch cameras (optionally limited to one network; handles pagination)
    device_kwargs = {"total_pages": "all", "productTypes": ["camera"]}
    if args.network_id:
        device_kwargs["networkIds"] = [args.network_id]
    cameras = dashboard.organizations.getOrganizationDevices(args.org_id, **device_kwargs)

    scope = (f"network {args.network_id} ({network_names[args.network_id]})"
             if args.network_id else f"organization {args.org_id}")
    print(f"Found {len(cameras)} camera(s) in {scope}")
    if not args.apply:
        print("DRY RUN: no changes will be made. Use --apply to disable Sense.\n")

    rows = []
    changed, skipped, failed = 0, 0, 0

    try:
        for cam in cameras:
            serial = cam["serial"]
            net_id = cam.get("networkId") or ""
            row = {
                "serial": serial,
                "name": cam.get("name") or "",
                "model": cam.get("model") or "",
                "network_id": net_id,
                "network_name": network_names.get(net_id, ""),
                "status": "",
                "detail": "",
            }
            label = f"{row['name'] or '(unnamed)'} [{serial}] {row['model']}"

            try:
                sense = dashboard.camera.getDeviceCameraSense(serial)
            except meraki.APIError as e:
                print(f"  FAIL  {label}: could not read Sense settings ({e.status} {e.message})")
                row.update(status="failed", detail=f"read error: {e.status} {e.message}")
                rows.append(row)
                failed += 1
                continue

            if not sense.get("senseEnabled"):
                print(f"  SKIP  {label}: Sense already disabled")
                row["status"] = "skipped_already_disabled"
                rows.append(row)
                skipped += 1
                continue

            if not args.apply:
                print(f"  WOULD DISABLE  {label}")
                row["status"] = "would_disable"
                rows.append(row)
                changed += 1
                continue

            try:
                dashboard.camera.updateDeviceCameraSense(serial, senseEnabled=False)
                print(f"  OK    {label}: Sense disabled")
                row["status"] = "disabled"
                changed += 1
            except meraki.APIError as e:
                print(f"  FAIL  {label}: {e.status} {e.message}")
                row.update(status="failed", detail=f"update error: {e.status} {e.message}")
                failed += 1
            rows.append(row)
    finally:
        # Write the report even if the run is interrupted partway through
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nCSV report written to {csv_path} ({len(rows)} row(s))")

    verb = "Disabled" if args.apply else "Would disable"
    print(f"{verb}: {changed} | Already disabled: {skipped} | Failed: {failed}")


if __name__ == "__main__":
    main()
