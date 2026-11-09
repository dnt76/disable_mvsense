#!/usr/bin/env python3
"""
Disable MV Sense on every camera in a Meraki organization.

Disabling Sense on a camera releases its MV Sense license so it can be
reused elsewhere. Uses:
  - organizations.getOrganizationDevices
  - camera.getDeviceCameraSense
  - camera.updateDeviceCameraSense  (PUT /devices/{serial}/camera/sense)

Usage:
  export MERAKI_DASHBOARD_API_KEY=your_key
  pip install meraki

  python disable_mv_sense.py --org-id 123456            # dry run (default)
  python disable_mv_sense.py --org-id 123456 --apply    # make changes
"""

import argparse
import os
import sys

import meraki


def main():
    parser = argparse.ArgumentParser(description="Disable MV Sense on all cameras in an org.")
    parser.add_argument("--org-id", required=True, help="Meraki organization ID")
    parser.add_argument("--apply", action="store_true",
                        help="Actually make changes (default is a dry run)")
    args = parser.parse_args()

    api_key = os.environ.get("MERAKI_DASHBOARD_API_KEY")
    if not api_key:
        sys.exit("Set the MERAKI_DASHBOARD_API_KEY environment variable.")

    dashboard = meraki.DashboardAPI(
        api_key,
        output_log=False,
        print_console=False,
        suppress_logging=True,
        maximum_retries=5,        # retries on 429 rate limiting
        wait_on_rate_limit=True,
    )

    # Fetch all cameras in the org (handles pagination)
    cameras = dashboard.organizations.getOrganizationDevices(
        args.org_id, total_pages="all", productTypes=["camera"]
    )
    print(f"Found {len(cameras)} camera(s) in organization {args.org_id}")
    if not args.apply:
        print("DRY RUN: no changes will be made. Use --apply to disable Sense.\n")

    changed, skipped, failed = 0, 0, 0

    for cam in cameras:
        serial = cam["serial"]
        label = f"{cam.get('name') or '(unnamed)'} [{serial}] {cam.get('model', '')}"

        try:
            sense = dashboard.camera.getDeviceCameraSense(serial)
        except meraki.APIError as e:
            print(f"  FAIL  {label}: could not read Sense settings ({e.status} {e.message})")
            failed += 1
            continue

        if not sense.get("senseEnabled"):
            print(f"  SKIP  {label}: Sense already disabled")
            skipped += 1
            continue

        if not args.apply:
            print(f"  WOULD DISABLE  {label}")
            changed += 1
            continue

        try:
            dashboard.camera.updateDeviceCameraSense(serial, senseEnabled=False)
            print(f"  OK    {label}: Sense disabled")
            changed += 1
        except meraki.APIError as e:
            print(f"  FAIL  {label}: {e.status} {e.message}")
            failed += 1

    verb = "Disabled" if args.apply else "Would disable"
    print(f"\n{verb}: {changed} | Already disabled: {skipped} | Failed: {failed}")


if __name__ == "__main__":
    main()
