"""
mailer.py - Envio de correos SMTP para reportes SRE en formato HTML.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import settings


def send_email(subject, body, html=False, to=None):
    to_addr = to or settings.smtp_to
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_addr
    if html:
        msg.attach(MIMEText(body, "html", "utf-8"))
    else:
        msg.attach(MIMEText(body, "plain", "utf-8"))
    try:
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True, "Correo enviado correctamente"
    except smtplib.SMTPAuthenticationError:
        return False, "Error de autenticacion."
    except smtplib.SMTPException as e:
        return False, f"Error SMTP: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def test_smtp():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"[Test] Zabbix SRE - {timestamp}"
    body = f"Prueba SMTP del Zabbix SRE Assistant.\nTimestamp: {timestamp}"
    print(f"\nEnviando correo de prueba a {settings.smtp_to}...")
    ok, message = send_email(subject, body)
    print(f"  {message}")
    return ok


HTML_STYLE = """<style>
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #ffffff; color: #1a1a1a; padding: 20px; margin: 0; }
.container { max-width: 800px; margin: 0 auto; }
h1 { color: #1a1a1a; font-size: 22px; border-bottom: 2px solid #e0e0e0;
     padding-bottom: 10px; margin-top: 30px; }
h2 { color: #333; font-size: 16px; margin-top: 24px; padding: 8px 12px;
     background: #f5f5f5; border-left: 4px solid #555; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }
th { background: #f0f0f0; padding: 8px 12px; text-align: left;
     border-bottom: 2px solid #ddd; }
td { padding: 8px 12px; border-bottom: 1px solid #eee; }
.sev-disaster { color: #c92a2a; font-weight: 600; }
.sev-high { color: #e8590c; font-weight: 600; }
.sev-average { color: #d9480f; }
.sev-warning { color: #c08c00; }
.sev-info { color: #1971c2; }
.metric { display: inline-block; margin: 4px 16px 4px 0; }
.metric-label { color: #666; font-size: 13px; }
.metric-value { color: #1a1a1a; font-size: 18px; font-weight: 600; }
.insight { background: #fff8e1; border-left: 3px solid #f59f00;
           padding: 10px 14px; margin: 8px 0; font-size: 14px; }
.ok { background: #e6f4ea; border-left: 3px solid #2f9e44;
      padding: 10px 14px; margin: 8px 0; font-size: 14px; }
.footer { color: #999; font-size: 12px; margin-top: 30px;
          padding-top: 12px; border-top: 1px solid #eee; }
.ack-pending { color: #c92a2a; font-size: 12px; }
.age { color: #666; font-size: 13px; }
</style>"""

SEV_CLASS = {0: "info", 1: "info", 2: "warning", 3: "average", 4: "high", 5: "disaster"}
SEV_LABELS = {0: "Info", 1: "Info", 2: "Warning", 3: "Average", 4: "High", 5: "Disaster"}


def html_wrap(title, body_html):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>{title}</title>"
        f"{HTML_STYLE}</head><body><div class=\"container\">{body_html}"
        f"<div class=\"footer\">Generado automaticamente por Zabbix SRE Assistant<br>{ts}</div>"
        f"</div></body></html>"
    )


def render_noc_html():
    from signals import get_noc_report, format_age
    problems = get_noc_report()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"<h1>Reporte NOC Operativo</h1><p>{ts} - Problemas accionables: <b>{len(problems)}</b></p>"
    if not problems:
        html += '<div class="ok">Sin problemas activos accionables. Operacion estable.</div>'
        return html_wrap("Reporte NOC", html)
    by_sev = {}
    for p in problems:
        by_sev.setdefault(p["severity"], []).append(p)
    for sev in sorted(by_sev.keys(), reverse=True):
        items = by_sev[sev]
        label = SEV_LABELS.get(sev, "?")
        html += f'<h2 class="sev-{SEV_CLASS[sev]}">{label.upper()} - {len(items)} problema(s)</h2>'
        html += "<table><thead><tr><th>Estado</th><th>Edad</th><th>Host</th><th>Dominio</th><th>Problema</th></tr></thead><tbody>"
        for p in items:
            ack = "RECONOCIDO" if p["acknowledged"] else '<span class="ack-pending">SIN RECONOCER</span>'
            age = format_age(p["age_seconds"])
            html += f'<tr><td>{ack}</td><td class="age">{age}</td><td>{p["host"]}</td><td>{p["responsible"]}</td><td>{p["name"]}</td></tr>'
        html += "</tbody></table>"
    no_ack = sum(1 for p in problems if not p["acknowledged"])
    if no_ack > 0:
        html += f'<div class="insight">{no_ack} de {len(problems)} problemas sin reconocer.</div>'
    return html_wrap("Reporte NOC", html)


def render_executive_html():
    from signals import get_executive_summary, format_duration
    data = get_executive_summary()
    html = f"<h1>Resumen Ejecutivo</h1><p>{data['timestamp']}</p>"
    html += "<h2>Indicadores clave</h2>"
    html += f'<div class="metric"><div class="metric-label">Problemas activos</div><div class="metric-value">{data["total_active"]}</div></div>'
    html += f'<div class="metric"><div class="metric-label">Severidad alta/critica</div><div class="metric-value sev-high">{data["high_disaster"]}</div></div>'
    html += f'<div class="metric"><div class="metric-label">Sin atender > 7 dias</div><div class="metric-value sev-disaster">{data["critical_aging"]}</div></div>'
    html += f'<div class="metric"><div class="metric-label">MTTR 24h</div><div class="metric-value">{format_duration(data["mttr_24h"])}</div></div>'
    html += f'<div class="metric"><div class="metric-label">Resueltos hoy</div><div class="metric-value">{data["resolved_24h"]}</div></div>'
    html += "<h2>Estado general</h2>"
    if data["critical_aging"] > 0:
        html += f'<div class="insight">ATENCION: {data["critical_aging"]} problema(s) sin atender por mas de 7 dias.</div>'
    elif data["high_disaster"] > 0:
        html += f'<div class="insight">Hay {data["high_disaster"]} problema(s) de severidad alta activos.</div>'
    else:
        html += '<div class="ok">Operacion estable. No hay problemas criticos activos.</div>'
    if data["mttr_24h"] is not None and data["mttr_24h"] > 3600:
        html += f'<div class="insight">MTTR ({format_duration(data["mttr_24h"])}) por encima de la meta SRE (1h).</div>'
    return html_wrap("Resumen Ejecutivo", html)


def render_sre_html():
    from signals import (get_golden_signals_report, get_mttr_and_aging,
                          format_duration, SIGNAL_ORDER, generate_insights)
    report = get_golden_signals_report()
    mttr = get_mttr_and_aging()
    html = f"<h1>Reporte SRE Completo</h1><p>{report.get('timestamp','')} - Problemas activos: <b>{report.get('total',0)}</b></p>"
    for signal in SIGNAL_ORDER:
        if signal not in report.get("signals", {}):
            continue
        s = report["signals"][signal]
        html += f'<h2>{s["label"]} - {s["total_problems"]} problema(s), {s["total_hosts"]} host(s)</h2>'
        html += "<table><thead><tr><th>Severidad</th><th>Patron</th><th>Hosts</th><th>Distribucion</th></tr></thead><tbody>"
        for p in s["patterns"]:
            sev_lbl = SEV_LABELS.get(p["severity_max"], "?")
            sev_cls = SEV_CLASS.get(p["severity_max"], "info")
            ack = f' <span class="ack-pending">[{p["not_acked"]} sin reconocer]</span>' if p["not_acked"] > 0 else ""
            html += f'<tr><td class="sev-{sev_cls}">{sev_lbl}</td><td>{p["name"]}{ack}</td><td>{p["host_count"]}</td><td>{p["groups"]}</td></tr>'
        html += "</tbody></table>"
    html += "<h2>MTTR (Tiempo Medio de Reparacion)</h2>"
    html += f'<div class="metric"><div class="metric-label">Ultimas 24h</div><div class="metric-value">{format_duration(mttr["mttr_24h"])}</div></div>'
    html += f'<div class="metric"><div class="metric-label">Ultimos 7 dias</div><div class="metric-value">{format_duration(mttr["mttr_7d"])}</div></div>'
    html += f'<div class="metric"><div class="metric-label">Resueltos 24h</div><div class="metric-value">{mttr["resolved_24h"]}</div></div>'
    html += "<h2>Aging - Problemas activos</h2>"
    html += "<table><thead><tr><th>Antiguedad</th><th>Cantidad</th><th>Porcentaje</th></tr></thead><tbody>"
    total = mttr["active_count"] or 1
    for bucket, count in mttr["aging"].items():
        pct = round(count / total * 100) if total else 0
        html += f"<tr><td>{bucket}</td><td>{count}</td><td>{pct}%</td></tr>"
    html += "</tbody></table>"
    insights = generate_insights(report)
    if insights:
        html += "<h2>Insights</h2>"
        for ins in insights:
            html += f'<div class="insight">{ins}</div>'
    return html_wrap("Reporte SRE Completo", html)


def render_admin_html():
    from signals import get_monitoring_quality_report
    from collections import defaultdict
    data = get_monitoring_quality_report()
    html = f"<h1>Calidad del Monitoreo</h1><p>{data['timestamp']} - Total hosts: <b>{data['total_hosts']}</b></p>"
    html += f'<h2>Items no soportados - {len(data["unsupported_items"])}</h2>'
    if data["unsupported_items"]:
        by_host = defaultdict(list)
        for item in data["unsupported_items"]:
            hname = item["hosts"][0]["name"] if item.get("hosts") else "?"
            by_host[hname].append(item)
        html += "<table><thead><tr><th>Host</th><th>Items afectados</th></tr></thead><tbody>"
        for host, items in sorted(by_host.items(), key=lambda x: -len(x[1])):
            html += f"<tr><td>{host}</td><td>{len(items)}</td></tr>"
        html += "</tbody></table>"
    else:
        html += '<div class="ok">Todos los items reportan correctamente.</div>'
    html += f'<h2>Triggers ruidosos (3+ veces en 24h) - {len(data["noisy_triggers"])}</h2>'
    if data["noisy_triggers"]:
        html += "<table><thead><tr><th>Veces</th><th>Host</th><th>Trigger</th></tr></thead><tbody>"
        for t in data["noisy_triggers"][:15]:
            html += f'<tr><td>{t["count"]}</td><td>{t["host"]}</td><td>{t["name"]}</td></tr>'
        html += "</tbody></table>"
    else:
        html += '<div class="ok">No hay triggers ruidosos.</div>'
    return html_wrap("Calidad del Monitoreo", html)


def send_report_email(report_type):
    report_map = {
        "noc": (render_noc_html, "Reporte NOC operativo"),
        "sre": (render_sre_html, "Reporte SRE completo"),
        "ejecutivo": (render_executive_html, "Resumen ejecutivo"),
        "admin": (render_admin_html, "Calidad del monitoreo"),
    }
    if report_type not in report_map:
        return False
    renderer, label = report_map[report_type]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\nGenerando {label}...")
    try:
        html_body = renderer()
    except Exception as e:
        print(f"  FALLO al generar reporte: {e}")
        return False
    subject = f"[Zabbix SRE] {label} - {timestamp}"
    print(f"Enviando a {settings.smtp_to}...")
    ok, message = send_email(subject, html_body, html=True)
    if ok:
        print(f"  {message}")
    else:
        print(f"  FALLO: {message}")
    return ok
