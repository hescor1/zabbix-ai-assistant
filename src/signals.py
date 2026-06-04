"""
signals.py — Clasificacion Golden Signals para reporte SRE
============================================================
Clasifica los problemas activos de Zabbix en las 4 senales doradas:
Saturacion, Errores, Latencia y Trafico.
Agrupa por patron para escalar a 1500+ hosts.
"""

from collections import defaultdict
from datetime import datetime
from zabbix.client import zabbix_request

SIGNAL_RULES = [
    ("temperature", "saturacion"),
    ("cpu utilization", "saturacion"),
    ("cpu is ", "saturacion"),
    ("cpu load", "saturacion"),
    ("load average", "saturacion"),
    ("processor load", "saturacion"),
    ("memory utilization", "saturacion"),
    ("memory is ", "saturacion"),
    ("lack of free swap", "saturacion"),
    ("running out of swap", "saturacion"),
    ("disk space", "saturacion"),
    ("storage space", "saturacion"),
    ("space is low", "saturacion"),
    ("space is critically", "saturacion"),
    ("free inodes", "saturacion"),
    ("bandwidth usage", "saturacion"),
    ("utilization is", "saturacion"),
    ("queue", "saturacion"),
    ("connections", "saturacion"),
    ("response time", "latencia"),
    ("latency", "latencia"),
    ("high icmp ping", "latencia"),
    ("icmp ping response", "latencia"),
    ("slow", "latencia"),
    ("timeout", "latencia"),
    ("duration", "latencia"),
    ("unavailable by icmp", "errores"),
    ("unreachable", "errores"),
    ("link down", "errores"),
    ("interface down", "errores"),
    ("not available", "errores"),
    ("unavailable", "errores"),
    ("not running", "errores"),
    ("has stopped", "errores"),
    ("failed", "errores"),
    ("no snmp data", "errores"),
    ("cannot connect", "errores"),
    ("packet loss", "errores"),
    ("error", "errores"),
    ("loss", "errores"),
    ("crash", "errores"),
    ("critical", "errores"),
    ("down", "errores"),
    ("lower speed", "trafico"),
    ("speed has changed", "trafico"),
    ("firmware has changed", "trafico"),
    ("has been restarted", "trafico"),
    ("system boot", "trafico"),
    ("uptime", "trafico"),
    ("discovered", "trafico"),
    ("changed", "trafico"),
    ("version has changed", "trafico"),
]

SIGNAL_ORDER = ["saturacion", "errores", "latencia", "trafico", "sin_clasificar"]

SIGNAL_LABELS = {
    "saturacion": "SATURACION (lo que va a fallar pronto)",
    "errores": "ERRORES (lo que ya esta fallando)",
    "latencia": "LATENCIA (degradacion de servicio)",
    "trafico": "TRAFICO / INFORMATIVO",
    "sin_clasificar": "SIN CLASIFICAR (requiere regla nueva)",
}

SIGNAL_EMOJI = {
    "saturacion": ">>",
    "errores": "XX",
    "latencia": "~~",
    "trafico": "..",
    "sin_clasificar": "??",
}

SEV_NAMES = {
    0: "Info", 1: "Info", 2: "Warning",
    3: "Average", 4: "High", 5: "Disaster",
}


def classify_problem(problem_name):
    """Clasifica un problema y retorna (signal, patron_agrupador)."""
    name_lower = problem_name.lower()
    for pattern, signal in SIGNAL_RULES:
        if pattern in name_lower:
            return signal, pattern
    return "sin_clasificar", name_lower


def get_golden_signals_report():
    """
    Obtiene problemas activos, clasifica en Golden Signals,
    agrupa por patron (no por nombre exacto) con desglose por host group.
    Escala a 1500+ hosts.
    """
    try:
        problems = zabbix_request("problem.get", {
            "output": [
                "eventid", "objectid", "name", "severity",
                "clock", "acknowledged", "cause_eventid",
            ],
            "recent": True,
            "sortfield": "eventid",
            "sortorder": "DESC",
            "suppressed": False,
        })
    except Exception:
        problems = zabbix_request("problem.get", {
            "output": [
                "eventid", "objectid", "name", "severity",
                "clock", "acknowledged",
            ],
            "recent": True,
            "sortfield": "eventid",
            "sortorder": "DESC",
            "suppressed": False,
        })

    if not problems:
        return {"total": 0, "signals": {}, "timestamp": ""}

    problems = [
        p for p in problems
        if str(p.get("cause_eventid", "0")) == "0"
    ]

    if not problems:
        return {"total": 0, "signals": {}, "timestamp": ""}

    trigger_ids = list({p["objectid"] for p in problems})
    trigger_map = {}

    for i in range(0, len(trigger_ids), 500):
        batch = trigger_ids[i:i + 500]
        triggers = zabbix_request("trigger.get", {
            "triggerids": batch,
            "output": ["triggerid"],
            "selectHosts": ["hostid", "name"],
            "selectHostGroups": ["name"],
        })
        if triggers:
            for t in triggers:
                hosts = t.get("hosts", [])
                groups = t.get("hostgroups", [])
                trigger_map[t["triggerid"]] = {
                    "host_name": hosts[0]["name"] if hosts else "?",
                    "groups": [g["name"] for g in groups] if groups else [],
                }

    signals = defaultdict(
        lambda: defaultdict(
            lambda: {
                "hosts": set(),
                "groups": defaultdict(int),
                "severity_max": 0,
                "count": 0,
                "not_acked": 0,
                "unique_names": set(),
            }
        )
    )

    for p in problems:
        signal, matched_pattern = classify_problem(p["name"])
        t_info = trigger_map.get(
            p["objectid"],
            {"host_name": "?", "groups": []}
        )
        sev = int(p["severity"])
        group = signals[signal][matched_pattern]
        group["hosts"].add(t_info["host_name"])
        group["severity_max"] = max(group["severity_max"], sev)
        group["count"] += 1
        group["unique_names"].add(p["name"])
        if p["acknowledged"] != "1":
            group["not_acked"] += 1
        for g in t_info["groups"]:
            group["groups"][g] += 1

    result = {
        "total": len(problems),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "signals": {},
    }

    for signal in SIGNAL_ORDER:
        if signal not in signals:
            continue
        patterns = signals[signal]
        sorted_patterns = sorted(
            patterns.items(),
            key=lambda x: (x[1]["severity_max"], len(x[1]["hosts"])),
            reverse=True,
        )
        total_signal = sum(v["count"] for v in patterns.values())
        total_hosts = len(set().union(*(v["hosts"] for v in patterns.values())))
        result["signals"][signal] = {
            "label": SIGNAL_LABELS[signal],
            "total_problems": total_signal,
            "total_hosts": total_hosts,
            "patterns": [],
        }
        for matched_pattern, data in sorted_patterns:
            groups_str = ", ".join(
                f"{g}: {c}"
                for g, c in sorted(
                    data["groups"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            )
            unique = sorted(data["unique_names"])
            if len(unique) == 1:
                display_name = unique[0]
            else:
                display_name = f"{unique[0][:60]}  (+{len(unique)-1} variantes)"

            result["signals"][signal]["patterns"].append({
                "name": display_name,
                "matched_pattern": matched_pattern,
                "host_count": len(data["hosts"]),
                "problem_count": data["count"],
                "variant_count": len(unique),
                "groups": groups_str,
                "severity_max": data["severity_max"],
                "not_acked": data["not_acked"],
                "hosts": sorted(data["hosts"]),
            })

    return result


def generate_insights(report):
    insights = []
    signals = report.get("signals", {})

    if "errores" in signals:
        for p in signals["errores"]["patterns"]:
            if p["host_count"] >= 3:
                insights.append(
                    f"{p['host_count']} hosts con '{p['matched_pattern']}' "
                    f"- posible problema de red o infraestructura compartida."
                )

    if "saturacion" in signals:
        total_sat = signals["saturacion"]["total_problems"]
        insights.append(
            f"{total_sat} problema(s) de saturacion. "
            f"Son predictivos: si no se atienden, habra caidas."
        )

    total_not_acked = 0
    for s in signals.values():
        for p in s["patterns"]:
            total_not_acked += p["not_acked"]
    if total_not_acked > 0:
        insights.append(
            f"{total_not_acked} problema(s) sin reconocer (acknowledge). "
            f"Nadie ha confirmado que los esta atendiendo."
        )

    if "trafico" in signals:
        total_trafico = signals["trafico"]["total_problems"]
        pct = round(total_trafico / report["total"] * 100)
        if pct >= 30:
            insights.append(
                f"{pct}% de los problemas son informativos (trafico). "
                f"Considerar bajar su severidad o deshabilitarlos."
            )

    if "latencia" not in signals:
        insights.append(
            "No hay problemas de latencia detectados. "
            "Verificar si se estan monitoreando response times."
        )

    if "sin_clasificar" in signals:
        total_sc = signals["sin_clasificar"]["total_problems"]
        insights.append(
            f"{total_sc} problema(s) sin clasificar. "
            f"Agregar reglas en SIGNAL_RULES para cubrirlos."
        )

    return insights


def print_golden_signals_report():
    print("\nConsultando problemas activos...")
    report = get_golden_signals_report()

    if report["total"] == 0:
        print("No hay problemas activos.")
        return

    print()
    print("=" * 70)
    print("REPORTE GOLDEN SIGNALS - SRE")
    print(f"Fecha: {report['timestamp']}")
    print(f"Total problemas activos: {report['total']}")
    print("=" * 70)

    for signal in SIGNAL_ORDER:
        if signal not in report["signals"]:
            continue
        s = report["signals"][signal]
        emoji = SIGNAL_EMOJI.get(signal, "")
        print(f"\n{emoji} {s['label']} - {s['total_problems']} problema(s), {s['total_hosts']} host(s)")
        print("-" * 70)
        for p in s["patterns"]:
            sev = SEV_NAMES.get(p["severity_max"], "?")
            ack_warning = ""
            if p["not_acked"] > 0:
                ack_warning = f" [!{p['not_acked']} sin reconocer]"
            # variantes ya incluidas en display_name
            # eliminado - redundante
            variant_info = ""
            if p["host_count"] == 1:
                host_info = p["hosts"][0]
            else:
                host_info = f"{p['host_count']} hosts ({p['groups']})"
            print(f"  [{sev:<8}] {p['name']}{variant_info}")
            print(f"             -> {host_info}{ack_warning}")

    print()
    print("=" * 70)
    print("RESUMEN POR SENAL")
    print("-" * 70)
    for signal in SIGNAL_ORDER:
        if signal in report["signals"]:
            s = report["signals"][signal]
            pct = round(s["total_problems"] / report["total"] * 100)
            label = SIGNAL_LABELS[signal].split("(")[0].strip()
            bar = "#" * max(1, pct // 5)
            print(f"  {label:<22} {s['total_problems']:>4} ({pct:>2}%) {bar}")
    print(f"  {'TOTAL':<22} {report['total']:>4}")
    print("=" * 70)

    insights = generate_insights(report)
    if insights:
        print()
        print("INSIGHTS")
        print("-" * 70)
        for insight in insights:
            print(f"  -> {insight}")
        print("=" * 70)
