# Disable MV Sense on Meraki Cameras

A Python script that uses the [Meraki Dashboard API library](https://github.com/meraki/dashboard-api-python) to disable MV Sense on cameras in a Meraki organization, or in a single network. Disabling Sense releases the MV Sense license from each camera so it returns to your license pool.

It uses the [Update Device Camera Sense](https://developer.cisco.com/meraki/api-v1/update-device-camera-sense/) endpoint (`PUT /devices/{serial}/camera/sense`).

## Features

- Processes every camera in an organization, or only one network with `--network-id`
- Writes a CSV report of every camera processed (serial, name, model, network, status)
- Skips cameras where Sense is already disabled
- Dry run by default; changes are only made with `--apply`
- Automatic pagination and rate-limit retries

## Requirements

- Python 3.8+
- The `meraki` library
- A Meraki Dashboard API key with write access to the target organization

## Installation

```bash
pip install meraki
```

## Configuration

Set your API key as an environment variable:

```bash
# Linux / macOS
export MERAKI_DASHBOARD_API_KEY=your_api_key

# Windows (PowerShell)
$env:MERAKI_DASHBOARD_API_KEY = "your_api_key"
```

You can find your organization ID in the Dashboard URL, or by calling `GET /organizations`. Network IDs look like `N_1234567890` and are available from `GET /organizations/{orgId}/networks`.

## Usage

Dry run across the whole organization (no changes are made):

```bash
python disable_mv_sense.py --org-id 123456
```

Dry run for a single network:

```bash
python disable_mv_sense.py --org-id 123456 --network-id N_1234567890
```

Apply the changes:

```bash
python disable_mv_sense.py --org-id 123456 --network-id N_1234567890 --apply
```

Save the CSV report to a specific file:

```bash
python disable_mv_sense.py --org-id 123456 --csv-out cameras.csv
```

### Options

| Option | Description |
|--------|-------------|
| `--org-id` | **Required.** The Meraki organization ID |
| `--network-id` | Only process cameras in this network. The network must belong to the organization |
| `--csv-out` | Path for the CSV report. Default: `mv_sense_<YYYYMMDD_HHMMSS>.csv` in the current directory |
| `--apply` | Actually disable Sense. Without this flag the script runs as a dry run |

## CSV report

A CSV is written on every run, including dry runs, and it is still saved if the script is interrupted partway through. Columns:

| Column | Description |
|--------|-------------|
| `serial` | Camera serial number |
| `name` | Camera name |
| `model` | Camera model |
| `network_id` | Network the camera belongs to |
| `network_name` | Network name |
| `status` | See below |
| `detail` | Error message when the status is `failed`, otherwise empty |

Status values:

| Status | Meaning |
|--------|---------|
| `would_disable` | Dry run: Sense is on and would be disabled with `--apply` |
| `disabled` | Sense was on and has been disabled |
| `skipped_already_disabled` | Sense was already off, so nothing was done |
| `failed` | The read or update call returned an error (see `detail`) |

A good workflow is to do a dry run, review the CSV, then run again with `--apply`.

### Example console output

```
Found 3 camera(s) in network N_1234567890 (Head Office)
DRY RUN: no changes will be made. Use --apply to disable Sense.

  WOULD DISABLE  Lobby [Q2XX-XXXX-XXXX] MV12
  SKIP  Warehouse [Q2YY-YYYY-YYYY] MV72: Sense already disabled
  WOULD DISABLE  Entrance [Q2ZZ-ZZZZ-ZZZZ] MV32

CSV report written to mv_sense_20261117_103000.csv (3 row(s))
Would disable: 2 | Already disabled: 1 | Failed: 0
```

## Important notes

- **No license removal call exists.** The API has no direct "remove license" action. Setting `senseEnabled` to `false` is what frees the MV Sense license on that camera. The license itself remains in your organization.
- **Features that depend on Sense will stop.** This includes people and vehicle analytics and MQTT-based detection data. Check any integrations that rely on these before running with `--apply`.
- **Always do a dry run first** and review the CSV.
- **Re-enabling is manual.** The script does not turn Sense back on. You can re-enable it per camera in the Dashboard or by calling the same endpoint with `senseEnabled=True`.

## Troubleshooting

| Problem | Likely cause |
|---------|--------------|
| `Set the MERAKI_DASHBOARD_API_KEY environment variable.` | The API key isn't set in your current shell |
| `Network ... was not found in organization ...` | Wrong network ID, or the network is in a different organization |
| `403` errors on update | The API key doesn't have write access to the organization |
| `404` errors | The device doesn't support Sense or the serial is no longer in the org |
| `429` errors | Rate limiting; the script retries automatically, but very large orgs may take a while |

## License

Use and modify freely. No warranty is provided; test on a small set of cameras before running across a production organization.
