"""
mailer.py — Envio de correos SMTP para reportes SRE.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import settings


def send_email(subject, body, html=False, to=None):
    """
    Envia un correo via SMTP.

    Args:
        subject: Asunto del correo
        body: Cuerpo del correo (texto plano o HTML)
        html: Si True, el body es HTML
        to: Destinatario (default: el del .env)
    """
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
        return False, "Error de autenticacion. Revisa SMTP_USER y SMTP_PASSWORD (usa App Password)."
    except smtplib.SMTPException as e:
        return False, f"Error SMTP: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def test_smtp():
    """Envia un correo de prueba para validar configuracion SMTP."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"[Test] Zabbix SRE Assistant — {timestamp}"
    body = f"""Este es un correo de prueba del Zabbix SRE Assistant.

Configuracion validada:
  Servidor:     {settings.smtp_server}:{settings.smtp_port}
  Remitente:    {settings.smtp_from}
  Destinatario: {settings.smtp_to}
  Timestamp:    {timestamp}

Si recibiste este correo, SMTP esta funcionando correctamente.
"""

    print(f"\nEnviando correo de prueba a {settings.smtp_to}...")
    ok, message = send_email(subject, body)

    if ok:
        print(f"  {message}")
        print(f"  Asunto: {subject}")
    else:
        print(f"  FALLO: {message}")

    return ok


def capture_report_output(report_function):
    """
    Captura la salida de cualquier funcion print_* a un string.
    Util para enviar el reporte por correo.
    """
    import io
    import sys

    buffer = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = buffer
    try:
        report_function()
    finally:
        sys.stdout = original_stdout

    return buffer.getvalue()


def send_report_email(report_type):
    """
    Genera un reporte y lo envia por correo.

    report_type: 'noc', 'sre', 'ejecutivo', 'admin'
    """
    from signals import (
        print_noc_report,
        print_sre_report,
        print_executive_summary,
        print_monitoring_quality_report,
    )

    report_map = {
        "noc": (print_noc_report, "Reporte NOC operativo"),
        "sre": (print_sre_report, "Reporte SRE completo"),
        "ejecutivo": (print_executive_summary, "Resumen ejecutivo"),
        "admin": (print_monitoring_quality_report, "Calidad del monitoreo"),
    }

    if report_type not in report_map:
        return False, f"Tipo de reporte invalido: {report_type}"

    func, label = report_map[report_type]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"\nGenerando {label}...")
    content = capture_report_output(func)

    subject = f"[Zabbix SRE] {label} — {timestamp}"
    body = content + "\n\n---\nGenerado automaticamente por Zabbix SRE Assistant.\n"

    print(f"Enviando a {settings.smtp_to}...")
    ok, message = send_email(subject, body)

    if ok:
        print(f"  {message}")
    else:
        print(f"  FALLO: {message}")

    return ok
