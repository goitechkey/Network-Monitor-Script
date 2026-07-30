from flask import Flask, render_template_string, send_file
from ping3 import ping
from collections import deque
import logging
import json
import smtplib
import socket
import ssl
import threading
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "email_settings.json"
LOG_FILE = BASE_DIR / "email_report.log"

latency_history = {}
ping_started_at = {}
ping_count_history = {}
COUNT_WINDOW_HOURS = 12

MAX_POINTS = 120  # Long graph history

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Live IP Monitor</title>
    <meta http-equiv="refresh" content="1">
    <style>
        body { font-family: Arial; background: #e9ecef; margin: 0; }

        table {
            width: 98%;
            margin: 15px auto;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 0 10px #aaa;
            font-size: 12px;
        }

        th {
            background: #343a40;
            color: white;
            padding: 8px 5px;
        }

        td {
            padding: 6px 5px;
            border-bottom: 1px solid #ddd;
            text-align: center;
        }

        .badge {
            padding: 6px 14px;
            border-radius: 15px;
            color: white;
            font-weight: bold;
        }

        .up { background: #28a745; }
        .down { background: #dc3545; }

        .graph {
            display: flex;
            align-items: flex-end;
            height: 25px;
            gap: 1px;
            justify-content: center;
        }

        .bar { 
            width: 3px;
            border-radius: 2px; 
        }

        .uptime-cell {
            color: #495057;
            font-size: 11px;
            line-height: 1.45;
            white-space: nowrap;
        }

        .good { background: #28a745; }
        .medium { background: #ffc107; }
        .bad { background: #dc3545; }
        .drop { background: #8b0000; height: 4px !important; }

        .title-bar {
            width: 98%;
            margin: 10px auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        h2 {
            margin: 0;
        }

        .toolbar { width: 95%; margin: 0 auto 15px; text-align: right; }
        .pdf-button {
            display: inline-block; padding: 10px 18px; border-radius: 6px;
            background: #dc3545; color: white; text-decoration: none;
            font-weight: bold;
        }
    </style>
</head>
<body>

<div class="title-bar">
    <h2>Live IP Monitoring Dashboard</h2>
    <a class="pdf-button" href="/report.pdf">Export PDF Report</a>
</div>

<table>
    <tr>
        <th>Category</th>
        <th>IP Address</th>
        <th>Name</th>
        <th>Status</th>
        <th>Latency Graph</th>
        <th>UP Date and Time</th>
        <th>Drop Packets</th>
    </tr>

    {% for category, ip, name, st, history, started, drop_count in data %}
    <tr>
        <td><b>{{ category }}</b></td>
        <td>{{ ip }}</td>
        <td>{{ name }}</td>
        <td>
            <span class="badge {{ 'up' if st == 'UP' else 'down' }}">
                {{ st }}
            </span>
        </td>
        <td>
            <div class="graph">
                {% for bar in history %}
                    {% if bar.type == "drop" %}
                        <div class="bar drop"></div>
                    {% else %}
                        <div class="bar {{ bar.type }}" style="height: {{ bar.height }}px"></div>
                    {% endif %}
                {% endfor %}
            </div>
        </td>
        <td class="uptime-cell">
            {{ started }}
        </td>
        <td class="uptime-cell" style="color:#dc3545; font-weight:bold;">
            {{ drop_count }}
        </td>
    </tr>
    {% endfor %}

</table>

</body>
</html>
"""

def read_ips():
    entries = []
    with open("ips.txt", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [part.strip() for part in line.split(",", 2)]
            if len(parts) != 3 or not all(parts):
                logging.warning(
                    "Skipping invalid ips.txt entry on line %s: expected Category,IP,Name",
                    line_number,
                )
                continue

            entries.append(tuple(parts))
    return entries

def format_elapsed(start_time, current_time):
    total_seconds = max(0, int((current_time - start_time).total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"

@app.route("/")
def index():
    result = []

    for category, ip, name in read_ips():

        if ip not in latency_history:
            latency_history[ip] = deque(maxlen=MAX_POINTS)
            ping_started_at[ip] = datetime.now()
            ping_count_history[ip] = deque()

        res = ping(ip, timeout=1)
        now = datetime.now()

        if res is not None:
            latency_ms = int(res * 1000)

            if latency_ms <= 30:
                bar_type = "good"
                height = 22
            elif latency_ms <= 80:
                bar_type = "medium"
                height = 14
            else:
                bar_type = "bad"
                height = 8

            latency_history[ip].append({
                "type": bar_type,
                "height": height
            })

            status = "UP"
        else:
            latency_history[ip].append({
                "type": "drop",
                "height": 4
            })
            status = "DOWN"

        ping_count_history[ip].append((now, status == "UP"))
        cutoff = now - timedelta(hours=COUNT_WINDOW_HOURS)
        while ping_count_history[ip] and ping_count_history[ip][0][0] < cutoff:
            ping_count_history[ip].popleft()

        started = ping_started_at[ip]
        history = list(latency_history[ip])
        drop_count = sum(1 for _, is_success in ping_count_history[ip] if not is_success)
        result.append((
            category,
            ip,
            name,
            status,
            history,
            started.strftime("%d-%m-%Y %I:%M:%S %p"),
            drop_count,
        ))

    return render_template_string(
        HTML,
        data=result,
        max_points=MAX_POINTS,
    )

def generate_pdf_report():
    scan_time = datetime.now()
    rows = []

    # Run a fresh scan so the PDF is a snapshot of the export time.
    for category, ip, name in read_ips():
        response = ping(ip, timeout=1)
        latency_ms = int(response * 1000) if response is not None else None
        status = "UP" if response is not None else "DOWN"
        rows.append((category, ip, name, status, latency_ms))

    up_count = sum(1 for row in rows if row[3] == "UP")
    down_count = len(rows) - up_count
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=15 * mm,
        title="Network Ping Status Report",
        author="Live IP Monitor",
    )
    styles = getSampleStyleSheet()
    content = [
        Paragraph("Network Ping Status Report", styles["Title"]),
        Paragraph(
            f"Generated: {scan_time:%d %B %Y, %I:%M:%S %p}",
            styles["Normal"],
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            f"Total: {len(rows)} &nbsp;&nbsp; UP: {up_count} "
            f"&nbsp;&nbsp; DOWN: {down_count}",
            styles["Heading2"],
        ),
        Spacer(1, 3 * mm),
    ]

    table_data = [["#", "Category", "IP / Hostname", "Name", "Status", "Latency"]]
    for number, (category, ip, name, status, latency_ms) in enumerate(rows, start=1):
        latency = f"{latency_ms} ms" if latency_ms is not None else "-"
        table_data.append([number, category, ip, name, status, latency])

    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[12 * mm, 38 * mm, 55 * mm, 62 * mm, 25 * mm, 28 * mm],
    )
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#343a40")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (4, 1), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#adb5bd")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f3f5")]),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for row_number, row in enumerate(rows, start=1):
        status_color = colors.HexColor("#198754" if row[3] == "UP" else "#dc3545")
        table_style.extend([
            ("TEXTCOLOR", (4, row_number), (4, row_number), status_color),
            ("FONTNAME", (4, row_number), (4, row_number), "Helvetica-Bold"),
        ])

    table.setStyle(TableStyle(table_style))
    content.append(table)

    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6c757d"))
        canvas.drawString(12 * mm, 8 * mm, "Live IP Monitor")
        canvas.drawRightString(
            landscape(A4)[0] - 12 * mm,
            8 * mm,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    document.build(content, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)
    filename = f"ping-report-{scan_time:%Y%m%d-%H%M%S}.pdf"
    return buffer, filename, len(rows), up_count, down_count

@app.route("/report.pdf")
def export_pdf():
    buffer, filename, _, _, _ = generate_pdf_report()
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )

def load_email_settings():
    with SETTINGS_FILE.open(encoding="utf-8") as settings_file:
        return json.load(settings_file)

def generate_ping_snapshot():
    scan_time = datetime.now()
    rows = []
    for category, ip, name in read_ips():
        response = ping(ip, timeout=1)
        latency_ms = int(response * 1000) if response is not None else None
        status = "UP" if response is not None else "DOWN"
        rows.append((category, ip, name, status, latency_ms))

    up_count = sum(1 for row in rows if row[3] == "UP")
    down_count = len(rows) - up_count
    width = 1400
    header_height = 145
    table_header_height = 48
    row_height = 42
    footer_height = 45
    height = header_height + table_header_height + (len(rows) * row_height) + footer_height
    image = Image.new("RGB", (width, height), "#eef1f5")
    draw = ImageDraw.Draw(image)

    def load_font(size, bold=False):
        font_name = "arialbd.ttf" if bold else "arial.ttf"
        font_path = Path("C:/Windows/Fonts") / font_name
        try:
            return ImageFont.truetype(str(font_path), size)
        except OSError:
            return ImageFont.load_default()

    title_font = load_font(34, bold=True)
    summary_font = load_font(21, bold=True)
    normal_font = load_font(18)
    bold_font = load_font(18, bold=True)
    small_font = load_font(15)

    draw.rectangle((0, 0, width, header_height), fill="#263238")
    draw.text((35, 24), "NETWORK PING STATUS SNAPSHOT", font=title_font, fill="white")
    draw.text(
        (35, 76),
        f"Generated: {scan_time:%d %B %Y, %I:%M:%S %p}",
        font=normal_font,
        fill="#d9e2e8",
    )
    draw.text(
        (900, 76),
        f"TOTAL: {len(rows)}    UP: {up_count}    DOWN: {down_count}",
        font=summary_font,
        fill="white",
    )

    columns = [
        ("#", 25, 70),
        ("Category", 70, 290),
        ("IP / Hostname", 290, 590),
        ("Name", 590, 1000),
        ("Status", 1000, 1160),
        ("Latency", 1160, 1380),
    ]
    table_top = header_height
    draw.rectangle((20, table_top, width - 20, table_top + table_header_height), fill="#37474f")
    for label, x1, x2 in columns:
        draw.text((x1 + 10, table_top + 13), label, font=bold_font, fill="white")
        draw.line((x2, table_top, x2, height - footer_height), fill="#b0bec5", width=1)

    for index, (category, ip, name, status, latency_ms) in enumerate(rows, start=1):
        y1 = table_top + table_header_height + ((index - 1) * row_height)
        y2 = y1 + row_height
        fill = "#ffffff" if index % 2 else "#e7ecef"
        draw.rectangle((20, y1, width - 20, y2), fill=fill)
        draw.line((20, y2, width - 20, y2), fill="#b0bec5", width=1)
        values = [
            str(index),
            category[:25],
            ip[:32],
            name[:42],
            status,
            f"{latency_ms} ms" if latency_ms is not None else "-",
        ]
        for column_index, value in enumerate(values):
            x1 = columns[column_index][1]
            color = "#198754" if status == "UP" else "#dc3545"
            text_color = color if column_index == 4 else "#17212b"
            font = bold_font if column_index == 4 else normal_font
            draw.text((x1 + 10, y1 + 11), value, font=font, fill=text_color)

    footer_y = height - footer_height
    draw.rectangle((0, footer_y, width, height), fill="#263238")
    draw.text(
        (35, footer_y + 14),
        "Live IP Monitor - Automatic Email Snapshot",
        font=small_font,
        fill="#d9e2e8",
    )

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    filename = f"ping-snapshot-{scan_time:%Y%m%d-%H%M%S}.png"
    return buffer, filename, len(rows), up_count, down_count

def send_scheduled_report(settings):
    buffer, filename, total, up_count, down_count = generate_ping_snapshot()
    message = EmailMessage()
    message["From"] = settings["sender_email"]
    message["To"] = ", ".join(settings["recipients"])
    if settings.get("cc"):
        message["Cc"] = ", ".join(settings["cc"])
    message["Subject"] = (
        f"Network Ping Snapshot - {datetime.now():%d %B %Y %I:%M %p}"
    )
    message.set_content(
        "Network Ping Status Snapshot\n\n"
        f"Total: {total}\nUP: {up_count}\nDOWN: {down_count}\n\n"
        "Open this email in HTML mode to view the snapshot."
    )
    message.add_alternative(
        f"""
        <!doctype html>
        <html>
          <body style="font-family:Arial,sans-serif;color:#17212b">
            <h2 style="margin-bottom:8px">Network Ping Status Snapshot</h2>
            <p style="font-size:16px">
              <strong>Total:</strong> {total}
              &nbsp;&nbsp;
              <strong style="color:#198754">UP:</strong> {up_count}
              &nbsp;&nbsp;
              <strong style="color:#dc3545">DOWN:</strong> {down_count}
            </p>
            <p>The latest ping snapshot is shown below:</p>
            <img
              src="cid:ping_snapshot"
              alt="Network ping status snapshot"
              style="display:block;width:100%;max-width:1400px;height:auto;border:1px solid #ccd3d8"
            >
          </body>
        </html>
        """,
        subtype="html",
    )
    html_part = message.get_payload()[-1]
    html_part.add_related(
        buffer.getvalue(),
        maintype="image",
        subtype="png",
        cid="<ping_snapshot>",
        filename=filename,
        disposition="inline",
    )

    smtp_host = settings["smtp_host"]
    smtp_port = int(settings["smtp_port"])
    security = settings.get("security", "starttls").lower()
    timeout = int(settings.get("timeout_seconds", 30))

    if security == "ssl":
        with smtplib.SMTP_SSL(
            smtp_host,
            smtp_port,
            timeout=timeout,
            context=ssl.create_default_context(),
        ) as smtp:
            smtp.login(settings["sender_email"], settings["password"])
            smtp.send_message(message)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as smtp:
            smtp.ehlo()
            if security == "starttls":
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            smtp.login(settings["sender_email"], settings["password"])
            smtp.send_message(message)

def email_scheduler():
    sent_today = set()
    while True:
        try:
            settings = load_email_settings()
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")
            sent_today = {item for item in sent_today if item.startswith(today)}

            if settings.get("enabled", False):
                for scheduled_time in settings.get("schedule_times", []):
                    send_key = f"{today}|{scheduled_time}"
                    if current_time == scheduled_time and send_key not in sent_today:
                        send_scheduled_report(settings)
                        sent_today.add(send_key)
                        logging.info("Scheduled ping snapshot emailed for %s", scheduled_time)

                if settings.get("hourly_enabled", False):
                    interval = max(1, int(settings.get("hourly_interval_hours", 1)))
                    hourly_minute = int(settings.get("hourly_minute", 0))
                    if now.hour % interval == 0 and now.minute == hourly_minute:
                        send_key = f"{today}|hourly|{now.hour:02d}"
                        if send_key not in sent_today:
                            send_scheduled_report(settings)
                            sent_today.add(send_key)
                            logging.info(
                                "Hourly ping snapshot emailed at %02d:%02d",
                                now.hour,
                                hourly_minute,
                            )
        except Exception:
            logging.exception("Automatic email report failed")

        time.sleep(30)

def start_email_scheduler():
    scheduler = threading.Thread(
        target=email_scheduler,
        name="email-report-scheduler",
        daemon=True,
    )
    scheduler.start()

def get_lan_ip():
    connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        connection.connect(("8.8.8.8", 80))
        return connection.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "YOUR-COMPUTER-IP"
    finally:
        connection.close()

if __name__ == "__main__":
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    start_email_scheduler()
    lan_ip = get_lan_ip()
    print()
    print("=" * 62)
    print(" LIVE IP MONITOR IS RUNNING")
    print("=" * 62)
    print(" This computer:")
    print("   http://localhost:5000")
    print("   http://127.0.0.1:5000")
    print()
    print(" Other users on the same network:")
    print(f"   http://{lan_ip}:5000")
    print()
    print(" Keep this window open. Press Ctrl+C to stop the server.")
    print("=" * 62)
    print(flush=True)
    app.run(host="0.0.0.0", port=5000)
