# Disable MV Sense on Meraki Cameras

A Python script that uses the [Meraki Dashboard API library](https://github.com/meraki/dashboard-api-python) to disable MV Sense on every camera in a Meraki organization. Disabling Sense releases the MV Sense license from each camera so it returns to your license pool.

It uses the [Update Device Camera Sense](https://developer.cisco.com/meraki/api-v1/update-device-camera-sense/) endpoint (`PUT /devices/{serial}/camera/sense`).

## Features

- Finds all cameras in an organization, with automatic pagination
- Skips cameras where Sense is already disabled
- Dry run by default; changes are only made with `--apply`
- Per-camera status output and a summary at the end
- Handles API rate limiting with automatic retries

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

You can find your organization ID in the Dashboard URL, or by calling `GET /organizations`.

## Usage

Preview which cameras would be changed (no changes are made):

```bash
python disable_mv_sense.py --org-id 123456
```

Apply the changes:

```bash
python disable_mv_sense.py --org-id 123456 --apply
```

### Options

| Option | Description |
|--------|-------------|
| `--org-id` | **Required.** The Meraki organization ID |
| `--apply` | Actually disable Sense. Without this flag the script runs as a dry run |

### Example output

```
Found 3 camera(s) in organization 123456
DRY RUN: no changes will be made. Use --apply to disable Sense.

  WOULD DISABLE  Lobby [Q2XX-XXXX-XXXX] MV12
  SKIP  Warehouse [Q2YY-YYYY-YYYY] MV72: Sense already disabled
  WOULD DISABLE  Entrance [Q2ZZ-ZZZZ-ZZZZ] MV32

Would disable: 2 | Already disabled: 1 | Failed: 0
```

## Important notes

- **No license removal call exists.** The API has no direct "remove license" action. Setting `senseEnabled` to `false` is what frees the MV Sense license on that camera. The license itself remains in your organization.
- **Features that depend on Sense will stop.** This includes people and vehicle analytics and MQTT-based detection data. Check any integrations that rely on these before running with `--apply`.
- **Always do a dry run first** to review the list of affected cameras.
- **Re-enabling is manual.** The script does not turn Sense back on. You can re-enable it per camera in the Dashboard or by calling the same endpoint with `senseEnabled=True`.

## Troubleshooting

| Problem | Likely cause |
|---------|--------------|
| `Set the MERAKI_DASHBOARD_API_KEY environment variable.` | The API key isn't set in your current shell |
| `403` errors on update | The API key doesn't have write access to the organization |
| `404` errors | The device doesn't support Sense or the serial is no longer in the org |
| `429` errors | Rate limiting; the script retries automatically, but very large orgs may take a while |

## License

Use and modify freely. No warranty is provided; test on a small set of cameras before running across a production organization.
