# Network-Monitor-Script
Ping Drop — Is monitoring interval mein target server/IP ne ping response nahi diya, timeout hua, ya device unreachable tha. Dashboard legend mein isse aise likh sakte hain: Green: Ping Success Yellow: Medium Latency Red: High Latency Pink/Dark Red: Ping Drop / Server Unreachable

# Live IP Monitor

Flask-based internal network monitoring dashboard. It reads monitored devices from `ips.txt`, pings them, and shows live UP/DOWN status, latency history, and rolling 12-hour success/drop counts.

## Features

- Monitors IP addresses and hostnames from `ips.txt`.
- Shows category, address, name, UP/DOWN status, and latency graph.
- Shows when monitoring started for each device.
- Shows ping success and drop counts from the last 12 hours.
- Manual PDF export from the dashboard.
- Scheduled email with an inline PNG ping snapshot and text summary.
- Optional hourly email setting, disabled by default.
- Local dependency installation in `.packages`.
- Optional Windows automatic startup through Task Scheduler.

## Requirements

- Windows 10/11
- Python 3.10 or newer
- Internet access for the first dependency installation
- ICMP/ping access to monitored devices

`install-dependencies.cmd` can install Python 3.13 through Windows `winget` if Python 3 is not already available.

## First-time setup

Open Command Prompt as Administrator and run:

```cmd
cd /d C:\Sev1
install-dependencies.cmd
```

This installs Flask, ping3, Pillow, and ReportLab into the local `.packages` folder.

## Run manually

```cmd
cd /d C:\Sev1
run-local.cmd
```

Open the URL printed in the terminal:

```text
http://localhost:5000
```

Other computers on the same LAN should use the displayed LAN address, for example `http://192.168.1.25:5000`.

Keep the terminal window open while running manually. Stop the application with `Ctrl+C`.

## Start automatically with Windows

After dependencies are installed, run this file once as Administrator:

```cmd
install-monitor-service.cmd
```

This creates a Task Scheduler entry named `Live IP Monitor` and starts it at Windows logon. It is a scheduled startup task rather than a native Windows Service.

To remove automatic startup:

```cmd
uninstall-monitor-service.cmd
```

## Configure monitored devices

Edit `ips.txt`. Each non-empty line must use this format:

```text
Category,IP-or-hostname,Display name
```

Example:

```text
General_Server,192.168.120.11,DC
Firewall,192.168.120.1,Main Firewall
Public_IP,google.com,Google
```

## Configure email reports

Edit `email_settings.json`:

```json
{
  "enabled": true,
  "smtp_host": "mail.example.com",
  "smtp_port": 465,
  "security": "ssl",
  "sender_email": "monitor@example.com",
  "password": "SMTP_PASSWORD",
  "recipients": ["it@example.com"],
  "cc": [],
  "schedule_times": ["09:00", "18:00"],
  "hourly_enabled": false,
  "hourly_interval_hours": 1,
  "hourly_minute": 0,
  "timeout_seconds": 30
}
```

- Port `465` normally uses `ssl`.
- Port `587` normally uses `starttls`.
- `hourly_enabled` is intentionally `false` by default.
- The email contains the current ping snapshot inline in the HTML body, not as a PDF attachment.
- The dashboard still provides a manual `Export PDF Report` button.
- Email success and errors are recorded in `email_report.log`.
- Keep SMTP passwords private and do not commit `email_settings.json` to source control.

## Backup and move to another computer

Copy these project files:

```text
APP.py
ips.txt
requirements.txt
email_settings.json
install-dependencies.cmd
run-local.cmd
install-monitor-service.cmd
uninstall-monitor-service.cmd
README.md
```

Do not copy `.packages`, `__pycache__`, `tmp`, or local logs. On the new computer, run `install-dependencies.cmd` and then `install-monitor-service.cmd` again.

## Logs and troubleshooting

- Email log: `email_report.log`
- `Scheduled ping snapshot emailed` means the SMTP server accepted the message.
- `SMTPAuthenticationError: 535` means SMTP username/password was rejected.
- A missing or invalid `ips.txt` row is skipped and logged as a warning.
- If LAN users cannot open the dashboard, allow inbound TCP port `5000` through Windows Firewall.
- Ping monitoring measures reachability and latency. It does not measure server bandwidth; server throughput requires a separate iperf3 or file-transfer test endpoint.


