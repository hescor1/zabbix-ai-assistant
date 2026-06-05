#!/usr/bin/env python3
"""
Script para envio automatico de reportes via cron.
Uso: python3 send_report.py <tipo>
Tipos: noc, sre, ejecutivo, admin
"""
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from mailer import send_report_email

if len(sys.argv) != 2:
    print("Uso: python3 send_report.py <noc|sre|ejecutivo|admin>")
    sys.exit(1)

report_type = sys.argv[1]
ok = send_report_email(report_type)
sys.exit(0 if ok else 1)
