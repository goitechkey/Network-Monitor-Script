# Kill Old all task 
taskkill /F /IM python.exe
# Network Monitor

A Windows network monitoring dashboard for IP addresses and hostnames. It continuously checks reachability, displays latency history, exports PDF reports, and can send scheduled email snapshots.

## What it does

- Monitors the devices listed in `ips.txt`.
- Shows UP/DOWN status and recent latency on a live web dashboard.
- Keeps a rolling 12-hour ping-drop count.
- Exports a PDF status report from the dashboard.
- Sends scheduled email snapshots when configured.
- Starts automatically in the background after Windows sign-in.

## One-time setup

1. Keep all project files together in one folder, for example `C:\Network-Monitor-Script`.
2. Double-click `Network-Monitor.cmd`.
3. Approve the Windows administrator prompt.
4. Wait until the script reports that setup is complete.

The setup automatically installs Python if needed, installs the required Python packages, creates the Windows startup task, and starts the monitor.

After setup, do not run the script again for normal use. The monitor starts in the background after every Windows sign-in, with no command window displayed.

## Open the dashboard

On the monitoring computer, open:

```text
http://localhost:5000
```

Other devices on the same network can use the LAN address printed in `monitor-service.log`, for example:

```text
http://192.168.1.151:5000
```

## Configure monitored devices

Edit `ips.txt`. Use one device per line:

```text
Category,IP-or-hostname,Display name
```

Example:

```text
Servers,192.168.1.10,Domain Controller
Firewall,192.168.1.1,Main Firewall
Public,google.com,Google DNS Check
```

Blank lines and lines beginning with `#` are ignored. Restart the monitor after changing the device list.

## Configure email reports

Edit `email_settings.json` before enabling email reports:

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

- Use `ssl` for port `465`.
- Use `starttls` for port `587`.
- Keep `hourly_enabled` set to `false` unless hourly reports are required.
- Do not share or commit a real SMTP password.

## Reports

Use the **Export PDF Report** button in the dashboard to download an on-demand PDF status report.

Email reports include an inline PNG snapshot of the current ping status.

## Background startup

The setup creates a Windows Task Scheduler task named `Live IP Monitor`. It runs the monitor in the background using `Network-Monitor-Background.vbs`, so no command window should appear after restart.

To remove automatic startup, open Command Prompt as Administrator in the project folder and run:

```cmd
Network-Monitor.cmd --remove
```

## Troubleshooting

- Dashboard does not open: check `monitor-service.log` in the project folder.
- Email does not send: check `email_report.log` and verify the SMTP settings.
- Other LAN devices cannot connect: allow inbound TCP port `5000` in Windows Firewall.
- A device shows DOWN: confirm that it responds to ICMP/ping from the monitoring computer.
- After changing `ips.txt`, restart the `Live IP Monitor` task in Task Scheduler.

## Files

- `APP.py` — dashboard and monitoring application.
- `Network-Monitor.cmd` — one-time setup and task management script.
- `Network-Monitor-Background.vbs` — hidden launcher used by the startup task.
- `ips.txt` — monitored device list.
- `email_settings.json` — email report configuration.
- `requirements.txt` — Python package requirements.
- `monitor-service.log` — monitor startup and application log.
- `email_report.log` — email report log.
