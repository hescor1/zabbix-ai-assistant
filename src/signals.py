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



def best_group(group_names):
    """Elige el grupo mas especifico (mas niveles de ruta)."""
    if not group_names:
        return "Sin grupo"
    scored = sorted(group_names, key=lambda g: (g.count("/"), len(g)), reverse=True)
    return scored[0]


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
                "clock", "acknowledged", "cause_eventid", "r_clock",
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

    # Filtrar problemas ya resueltos
    problems = [
        p for p in problems
        if int(p.get("r_clock", "0")) == 0
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
        best = best_group(t_info["groups"])
        group["groups"][best] += 1

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


def get_mttr_and_aging():
    """
    Calcula MTTR usando event.get y aging de problemas activos.
    """
    from datetime import timedelta
    now = datetime.now()
    time_24h = int((now - timedelta(hours=24)).timestamp())
    time_7d = int((now - timedelta(days=7)).timestamp())

    # Obtener eventos PROBLEM (value=1) de ultimos 7 dias
    problem_events = zabbix_request("event.get", {
        "output": ["eventid", "clock", "name", "severity", "r_eventid"],
        "time_from": time_7d,
        "source": 0,
        "object": 0,
        "value": 1,
        "sortfield": "eventid",
        "sortorder": "DESC",
    }) or []

    # Buscar recovery times para los que tienen r_eventid
    resolved = []
    recovery_ids = [p["r_eventid"] for p in problem_events if p.get("r_eventid", "0") != "0"]

    recovery_map = {}
    if recovery_ids:
        for i in range(0, len(recovery_ids), 500):
            batch = recovery_ids[i:i+500]
            recoveries = zabbix_request("event.get", {
                "eventids": batch,
                "output": ["eventid", "clock"],
            }) or []
            for r in recoveries:
                recovery_map[r["eventid"]] = int(r["clock"])

    for p in problem_events:
        rid = p.get("r_eventid", "0")
        if rid != "0" and rid in recovery_map:
            p_clock = int(p["clock"])
            r_clock = recovery_map[rid]
            resolved.append({
                "name": p["name"],
                "clock": p_clock,
                "r_clock": r_clock,
                "duration": r_clock - p_clock,
            })

    # Separar 24h y 7d
    resolved_24h = [r for r in resolved if r["clock"] >= time_24h]
    resolved_7d = resolved

    # MTTR 24h
    mttr_24h = None
    resolved_24h_count = len(resolved_24h)
    if resolved_24h:
        mttr_24h = sum(r["duration"] for r in resolved_24h) / len(resolved_24h)

    # MTTR 7d
    mttr_7d = None
    resolved_7d_count = len(resolved_7d)
    if resolved_7d:
        mttr_7d = sum(r["duration"] for r in resolved_7d) / len(resolved_7d)

    # Problemas activos para aging
    active_raw = zabbix_request("problem.get", {
        "output": ["eventid", "objectid", "name", "severity", "clock", "r_clock", "cause_eventid"],
        "recent": True,
        "sortfield": "eventid",
        "sortorder": "DESC",
        "suppressed": False,
    }) or []
    active = [
        p for p in active_raw
        if int(p.get("r_clock", "0")) == 0
        and str(p.get("cause_eventid", "0")) == "0"
    ]

    # Calcular aging
    aging_buckets = {"< 1h": 0, "1h - 4h": 0, "4h - 24h": 0, "1d - 7d": 0, "> 7d": 0}
    now_ts = int(now.timestamp())

    if active:
        for p in active:
            age_sec = now_ts - int(p["clock"])
            age_hours = age_sec / 3600
            if age_hours < 1:
                aging_buckets["< 1h"] += 1
            elif age_hours < 4:
                aging_buckets["1h - 4h"] += 1
            elif age_hours < 24:
                aging_buckets["4h - 24h"] += 1
            elif age_hours < 168:
                aging_buckets["1d - 7d"] += 1
            else:
                aging_buckets["> 7d"] += 1

    return {
        "mttr_24h": mttr_24h,
        "mttr_7d": mttr_7d,
        "resolved_24h": resolved_24h_count,
        "resolved_7d": resolved_7d_count,
        "active_count": len(active) if active else 0,
        "aging": aging_buckets,
    }


def format_duration(seconds):
    """Convierte segundos a formato legible."""
    if seconds is None:
        return "N/A"
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds/60)}m"
    if seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    days = seconds / 86400
    return f"{days:.1f}d"


def print_mttr_and_aging():
    """Imprime MTTR y aging en terminal."""
    print("\nCalculando MTTR y aging...")
    data = get_mttr_and_aging()

    print()
    print("=" * 70)
    print("METRICAS SRE — MTTR & AGING")
    print("=" * 70)

    print()
    print("MTTR (Tiempo Medio de Reparacion)")
    print("-" * 70)
    print(f"  Ultimas 24h:  {format_duration(data['mttr_24h'])}  ({data['resolved_24h']} problemas resueltos)")
    print(f"  Ultimos 7d:   {format_duration(data['mttr_7d'])}  ({data['resolved_7d']} problemas resueltos)")

    print()
    print(f"AGING — Problemas activos: {data['active_count']}")
    print("-" * 70)
    for bucket, count in data["aging"].items():
        if data["active_count"] > 0:
            pct = round(count / data["active_count"] * 100)
        else:
            pct = 0
        bar = "#" * max(0, pct // 5)
        print(f"  {bucket:<12} {count:>4} ({pct:>2}%) {bar}")

    # Insights
    print()
    print("INSIGHTS")
    print("-" * 70)
    if data["mttr_24h"] is not None and data["mttr_24h"] > 3600:
        print(f"  -> MTTR de {format_duration(data['mttr_24h'])} en 24h. Meta SRE: < 1h para High/Disaster.")
    if data["aging"].get("> 7d", 0) > 0:
        print(f"  -> {data['aging']['> 7d']} problema(s) llevan mas de 7 dias abiertos. Requieren escalamiento.")
    if data["aging"].get("1d - 7d", 0) > 0:
        print(f"  -> {data['aging']['1d - 7d']} problema(s) entre 1 y 7 dias. Verificar si tienen responsable asignado.")
    if data["resolved_24h"] == 0:
        print("  -> No se resolvio ningun problema en las ultimas 24h.")
    print("=" * 70)


def print_sre_report():
    print_golden_signals_report()
    data = get_mttr_and_aging()

    print("=" * 70)
    print("MTTR (Tiempo Medio de Reparacion)")
    print("-" * 70)
    print(f"  Ultimas 24h:  {format_duration(data['mttr_24h'])}  ({data['resolved_24h']} problemas resueltos)")
    print(f"  Ultimos 7d:   {format_duration(data['mttr_7d'])}  ({data['resolved_7d']} problemas resueltos)")

    print()
    print(f"AGING — Problemas activos: {data['active_count']}")
    print("-" * 70)
    for bucket, count in data["aging"].items():
        if data["active_count"] > 0:
            pct = round(count / data["active_count"] * 100)
        else:
            pct = 0
        bar = "#" * max(0, pct // 5)
        print(f"  {bucket:<12} {count:>4} ({pct:>2}%) {bar}")

    print()
    print("INSIGHTS MTTR/AGING")
    print("-" * 70)
    if data["mttr_24h"] is not None and data["mttr_24h"] > 3600:
        print(f"  -> MTTR de {format_duration(data['mttr_24h'])} en 24h. Meta SRE: < 1h para High/Disaster.")
    if data["aging"].get("> 7d", 0) > 0:
        print(f"  -> {data['aging']['> 7d']} problema(s) llevan mas de 7 dias abiertos. Requieren escalamiento.")
    if data["aging"].get("1d - 7d", 0) > 0:
        print(f"  -> {data['aging']['1d - 7d']} problema(s) entre 1 y 7 dias. Verificar si tienen responsable asignado.")
    if data["resolved_24h"] == 0:
        print("  -> No se resolvio ningun problema en las ultimas 24h.")
    print("=" * 70)


def get_executive_summary():
    """
    Retorna un resumen ejecutivo: solo los numeros clave que necesita gerencia.
    """
    report = get_golden_signals_report()
    mttr_data = get_mttr_and_aging()

    # Contar problemas High/Disaster
    high_count = 0
    if report.get("signals"):
        for signal_data in report["signals"].values():
            for p in signal_data["patterns"]:
                if p["severity_max"] >= 4:
                    high_count += p["problem_count"]

    # Problemas criticos sin atender > 7 dias
    critical_aging = mttr_data["aging"].get("> 7d", 0)

    return {
        "timestamp": report.get("timestamp", ""),
        "total_active": report.get("total", 0),
        "high_disaster": high_count,
        "mttr_24h": mttr_data["mttr_24h"],
        "mttr_7d": mttr_data["mttr_7d"],
        "critical_aging": critical_aging,
        "resolved_24h": mttr_data["resolved_24h"],
        "aging": mttr_data["aging"],
    }


def print_executive_summary():
    """Vista ejecutiva para gerencia: 5-7 lineas con lo critico."""
    print("\nGenerando resumen ejecutivo...")
    data = get_executive_summary()

    print()
    print("=" * 70)
    print(f"RESUMEN EJECUTIVO — {data['timestamp']}")
    print("=" * 70)
    print()
    print(f"  Problemas activos:           {data['total_active']}")
    print(f"  Severidad alta/critica:      {data['high_disaster']}")
    print(f"  Sin atender mas de 7 dias:   {data['critical_aging']}")
    print(f"  MTTR ultimas 24h:            {format_duration(data['mttr_24h'])}")
    print(f"  Problemas resueltos hoy:     {data['resolved_24h']}")
    print()

    # Conclusion automatica
    print("ESTADO GENERAL")
    print("-" * 70)
    if data["critical_aging"] > 0:
        print(f"  ATENCION: {data['critical_aging']} problema(s) sin atender por mas de 7 dias.")
        print(f"  Requiere intervencion de los responsables de dominio.")
    elif data["high_disaster"] > 0:
        print(f"  Hay {data['high_disaster']} problema(s) de severidad alta activos.")
        print(f"  NOC esta en seguimiento.")
    else:
        print("  Operacion estable. No hay problemas criticos activos.")

    if data["mttr_24h"] is not None and data["mttr_24h"] > 3600:
        print(f"  MTTR esta por encima de la meta SRE (1h para High/Disaster).")

    print("=" * 70)


def get_report_by_responsible(responsible):
    """
    Filtra problemas por tag 'responsable'.
    Retorna report estructurado solo con los hosts de ese responsable.
    """
    try:
        problems = zabbix_request("problem.get", {
            "output": [
                "eventid", "objectid", "name", "severity",
                "clock", "acknowledged", "cause_eventid", "r_clock",
            ],
            "recent": True,
            "sortfield": "eventid",
            "sortorder": "DESC",
            "suppressed": False,
            "selectTags": "extend",
        })
    except Exception:
        problems = []

    if not problems:
        return None

    # Filtrar resueltos y sintomas
    problems = [
        p for p in problems
        if int(p.get("r_clock", "0")) == 0
        and str(p.get("cause_eventid", "0")) == "0"
    ]

    # Obtener triggers con sus hosts y tags de host
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
                host_info = {
                    "host_name": hosts[0]["name"] if hosts else "?",
                    "hostid": hosts[0]["hostid"] if hosts else None,
                    "groups": [g["name"] for g in groups] if groups else [],
                }
                trigger_map[t["triggerid"]] = host_info

    # Obtener tags de los hosts
    host_ids = list({info["hostid"] for info in trigger_map.values() if info["hostid"]})
    host_tags_map = {}

    if host_ids:
        for i in range(0, len(host_ids), 500):
            batch = host_ids[i:i + 500]
            hosts = zabbix_request("host.get", {
                "hostids": batch,
                "output": ["hostid"],
                "selectTags": "extend",
            })
            if hosts:
                for h in hosts:
                    responsible_value = None
                    for t in h.get("tags", []):
                        if t["tag"] == "responsable":
                            responsible_value = t["value"]
                            break
                    host_tags_map[h["hostid"]] = responsible_value

    # Filtrar problemas por responsable
    filtered_problems = []
    for p in problems:
        t_info = trigger_map.get(p["objectid"])
        if not t_info:
            continue
        host_resp = host_tags_map.get(t_info["hostid"])
        if host_resp == responsible:
            filtered_problems.append({
                "problem": p,
                "host": t_info["host_name"],
                "groups": t_info["groups"],
            })

    return filtered_problems


def list_responsibles():
    """Lista todos los responsables (tag 'responsable') que existen en hosts."""
    hosts = zabbix_request("host.get", {
        "output": ["hostid", "name"],
        "selectTags": "extend",
    })

    responsibles = {}
    for h in (hosts or []):
        for t in h.get("tags", []):
            if t["tag"] == "responsable":
                resp = t["value"]
                if resp not in responsibles:
                    responsibles[resp] = []
                responsibles[resp].append(h["name"])

    return responsibles


def print_report_by_responsible():
    """Genera reporte filtrado por responsable. Pide el responsable al usuario."""
    print("\nConsultando responsables disponibles...")
    responsibles = list_responsibles()

    if not responsibles:
        print("No hay hosts con tag 'responsable'.")
        return

    print()
    print("Responsables disponibles:")
    print("-" * 70)
    resp_list = sorted(responsibles.keys())
    for i, resp in enumerate(resp_list, 1):
        count = len(responsibles[resp])
        print(f"  {i}. {resp}  ({count} host(s))")
    print()

    try:
        choice = input("Seleccione numero (o 'b' para volver): ").strip()
        if choice.lower() == "b" or not choice:
            return
        selected = resp_list[int(choice) - 1]
    except (ValueError, IndexError):
        print("Seleccion invalida.")
        return

    problems = get_report_by_responsible(selected)

    print()
    print("=" * 70)
    print(f"REPORTE PARA RESPONSABLE: {selected}")
    print(f"Hosts asignados: {len(responsibles[selected])}")
    print(f"Problemas activos en sus hosts: {len(problems) if problems else 0}")
    print("=" * 70)

    if not problems:
        print("\n  No hay problemas activos en sus hosts. Operacion estable.")
        print("=" * 70)
        return

    # Agrupar por host
    by_host = defaultdict(list)
    for p in problems:
        by_host[p["host"]].append(p)

    sev_names = {0: "Info", 1: "Info", 2: "Warning", 3: "Average", 4: "High", 5: "Disaster"}

    for host, items in sorted(by_host.items()):
        print(f"\n  {host} — {len(items)} problema(s)")
        print("  " + "-" * 66)
        for item in items:
            p = item["problem"]
            sev = sev_names.get(int(p["severity"]), "?")
            ack = "" if p["acknowledged"] == "1" else " [sin reconocer]"
            print(f"    [{sev:<8}] {p['name']}{ack}")

    print()
    print("=" * 70)


def get_monitoring_quality_report():
    """
    Reporte de calidad del monitoreo para administrador Zabbix.
    Detecta: items no soportados, sin datos, hosts sin tags, triggers ruidosos.
    """
    from datetime import timedelta
    now = datetime.now()
    time_24h = int((now - timedelta(hours=24)).timestamp())

    # 1. Items no soportados (state=1)
    unsupported = zabbix_request("item.get", {
        "filter": {"state": "1", "status": "0"},
        "output": ["itemid", "name", "key_", "error", "hostid"],
        "selectHosts": ["name"],
        "limit": 200,
    }) or []

    # 2. Hosts sin tags
    all_hosts = zabbix_request("host.get", {
        "output": ["hostid", "name"],
        "selectTags": "extend",
        "filter": {"status": "0"},
    }) or []

    hosts_no_tags = [h for h in all_hosts if not h.get("tags")]
    hosts_missing_responsable = [
        h for h in all_hosts
        if not any(t["tag"] == "responsable" for t in h.get("tags", []))
    ]

    # 3. Triggers ruidosos (que cambiaron de estado muchas veces en 24h)
    noisy_events = zabbix_request("event.get", {
        "output": ["objectid", "name"],
        "time_from": time_24h,
        "source": 0,
        "object": 0,
        "value": 1,
    }) or []

    from collections import Counter
    trigger_counts = Counter(e["objectid"] for e in noisy_events)
    noisy_triggers_ids = [tid for tid, count in trigger_counts.items() if count >= 3]

    noisy_triggers_info = []
    if noisy_triggers_ids:
        for i in range(0, len(noisy_triggers_ids), 500):
            batch = noisy_triggers_ids[i:i+500]
            trigs = zabbix_request("trigger.get", {
                "triggerids": batch,
                "output": ["triggerid", "description"],
                "selectHosts": ["name"],
            }) or []
            for t in trigs:
                host = t["hosts"][0]["name"] if t.get("hosts") else "?"
                noisy_triggers_info.append({
                    "name": t["description"],
                    "host": host,
                    "count": trigger_counts[t["triggerid"]],
                })

    noisy_triggers_info.sort(key=lambda x: x["count"], reverse=True)

    # 4. Hosts deshabilitados
    disabled_hosts = zabbix_request("host.get", {
        "output": ["hostid", "name"],
        "filter": {"status": "1"},
    }) or []

    return {
        "timestamp": now.strftime("%Y-%m-%d %H:%M"),
        "total_hosts": len(all_hosts),
        "unsupported_items": unsupported,
        "hosts_no_tags": hosts_no_tags,
        "hosts_no_responsable": hosts_missing_responsable,
        "noisy_triggers": noisy_triggers_info,
        "disabled_hosts": disabled_hosts,
    }


def print_monitoring_quality_report():
    """Reporte de calidad del monitoreo para admin Zabbix."""
    print("\nAnalizando calidad del monitoreo...")
    data = get_monitoring_quality_report()

    print()
    print("=" * 70)
    print(f"CALIDAD DEL MONITOREO — {data['timestamp']}")
    print(f"Total hosts habilitados: {data['total_hosts']}")
    print("=" * 70)

    # Items no soportados
    unsup = data["unsupported_items"]
    print(f"\nITEMS NO SOPORTADOS: {len(unsup)}")
    print("-" * 70)
    if unsup:
        # Agrupar por host
        by_host = defaultdict(list)
        for item in unsup:
            host_name = item["hosts"][0]["name"] if item.get("hosts") else "?"
            by_host[host_name].append(item)
        for host, items in sorted(by_host.items(), key=lambda x: -len(x[1])):
            print(f"  {host}: {len(items)} item(s)")
            for it in items[:3]:
                error = (it.get("error", "")[:60] + "...") if len(it.get("error", "")) > 60 else it.get("error", "sin detalle")
                print(f"    - {it['name']}")
                print(f"      error: {error}")
            if len(items) > 3:
                print(f"    ... y {len(items) - 3} mas")
    else:
        print("  Ninguno.")

    # Hosts sin tags / sin responsable
    print(f"\nHOSTS SIN TAGS: {len(data['hosts_no_tags'])}")
    print("-" * 70)
    if data["hosts_no_tags"]:
        for h in data["hosts_no_tags"]:
            print(f"  - {h['name']}")
    else:
        print("  Todos los hosts tienen tags.")

    print(f"\nHOSTS SIN TAG 'responsable': {len(data['hosts_no_responsable'])}")
    print("-" * 70)
    if data["hosts_no_responsable"]:
        for h in data["hosts_no_responsable"]:
            print(f"  - {h['name']}")
    else:
        print("  Todos los hosts tienen responsable asignado.")

    # Triggers ruidosos
    noisy = data["noisy_triggers"]
    print(f"\nTRIGGERS RUIDOSOS (3+ veces en 24h): {len(noisy)}")
    print("-" * 70)
    if noisy:
        for t in noisy[:10]:
            print(f"  {t['count']:>3}x  {t['host']}  -> {t['name']}")
        if len(noisy) > 10:
            print(f"  ... y {len(noisy) - 10} mas")
    else:
        print("  Ninguno detectado en ultimas 24h.")

    # Hosts deshabilitados
    disabled = data["disabled_hosts"]
    print(f"\nHOSTS DESHABILITADOS: {len(disabled)}")
    print("-" * 70)
    if disabled:
        for h in disabled:
            print(f"  - {h['name']}")
    else:
        print("  Ninguno.")

    # Recomendaciones
    print()
    print("RECOMENDACIONES PARA ADMIN ZABBIX")
    print("-" * 70)
    if unsup:
        print(f"  -> Revisar {len(unsup)} item(s) no soportados. Verificar keys, OIDs, credenciales.")
    if data["hosts_no_responsable"]:
        print(f"  -> Asignar tag 'responsable' a {len(data['hosts_no_responsable'])} host(s) para habilitar reporte por dominio.")
    if noisy:
        top_noisy = noisy[0]
        print(f"  -> Trigger mas ruidoso: '{top_noisy['name']}' en {top_noisy['host']} ({top_noisy['count']}x). Considerar ajustar umbral o agregar dependencia.")
    if not unsup and not data["hosts_no_responsable"] and not noisy:
        print("  -> Calidad del monitoreo: OK. Sin acciones pendientes.")
    print("=" * 70)
