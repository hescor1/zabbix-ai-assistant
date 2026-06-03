import requests

from config import settings


def zabbix_request(method, params=None):
    """
    Función base para hablar con la API de Zabbix.
    Todas las demás funciones usan esta función.
    """
    if params is None:
        params = {}

    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "auth": settings.zabbix_token,
        "id": 1
    }

    headers = {
        "Content-Type": "application/json-rpc"
    }

    response = requests.post(
        settings.zabbix_api_url,
        json=payload,
        headers=headers,
        timeout=settings.request_timeout_seconds
    )

    response.raise_for_status()

    data = response.json()

    if "error" in data:
        error = data["error"]
        message = error.get("message", "Error desconocido")
        details = error.get("data", "")
        raise Exception(f"Error de Zabbix API: {message} - {details}")

    return data["result"]


def get_hosts(limit=None):
    """
    Obtiene una lista limitada de hosts.
    Incluye interfaces y grupos para mostrar IP y contexto.
    """
    if limit is None:
        limit = settings.host_search_limit

    params = {
        "output": ["hostid", "host", "name", "status"],
        "selectInterfaces": [
            "interfaceid",
            "type",
            "ip",
            "dns",
            "port",
            "main",
            "useip"
        ],
        "selectGroups": ["groupid", "name"],
        "sortfield": "name",
        "limit": limit
    }

    return zabbix_request("host.get", params)


def search_hosts(search_text, limit=None):
    """
    Busca hosts por nombre técnico o nombre visible.
    Incluye interfaces y grupos para mostrar IP y contexto.
    """
    if limit is None:
        limit = settings.host_search_limit

    params = {
        "output": ["hostid", "host", "name", "status"],
        "selectInterfaces": [
            "interfaceid",
            "type",
            "ip",
            "dns",
            "port",
            "main",
            "useip"
        ],
        "selectGroups": ["groupid", "name"],
        "search": {
            "host": search_text,
            "name": search_text
        },
        "searchByAny": True,
        "sortfield": "name",
        "limit": limit
    }

    return zabbix_request("host.get", params)


def get_hosts_with_interfaces(limit=None):
    """
    Obtiene hosts visibles con interfaces y grupos.
    Se usa para búsquedas inteligentes por IP, DNS, hostid o nombre.
    """
    if limit is None:
        limit = 1000

    params = {
        "output": ["hostid", "host", "name", "status"],
        "selectInterfaces": [
            "interfaceid",
            "type",
            "ip",
            "dns",
            "port",
            "main",
            "useip"
        ],
        "selectGroups": ["groupid", "name"],
        "sortfield": "name",
        "limit": limit
    }

    return zabbix_request("host.get", params)


def get_host_details(hostid):
    """
    Obtiene información más completa de un host específico.
    """
    params = {
        "output": ["hostid", "host", "name", "status"],
        "hostids": hostid,
        "selectInterfaces": [
            "interfaceid",
            "type",
            "ip",
            "dns",
            "port",
            "main",
            "useip"
        ],
        "selectGroups": ["groupid", "name"],
        "selectParentTemplates": ["templateid", "name"],
        "selectTags": ["tag", "value"],
        "selectInventory": "extend"
    }

    result = zabbix_request("host.get", params)

    if not result:
        return None

    return result[0]


def get_host_items(hostid, search_text=None, limit=100):
    """
    Obtiene ítems de un host.
    Se usa para revisar ítems específicos, no para diagnóstico masivo.
    """
    params = {
        "output": [
            "itemid",
            "name",
            "key_",
            "type",
            "value_type",
            "status",
            "state",
            "lastvalue",
            "lastclock",
            "units"
        ],
        "hostids": hostid,
        "sortfield": "name",
        "limit": limit
    }

    if search_text:
        params["search"] = {
            "name": search_text,
            "key_": search_text
        }
        params["searchByAny"] = True

    return zabbix_request("item.get", params)


def get_host_item_summary(hostid):
    """
    Devuelve un resumen de ítems por host:
    total, enabled, disabled, unsupported, sin datos y última fecha de dato.
    """
    params = {
        "output": [
            "itemid",
            "name",
            "key_",
            "status",
            "state",
            "lastclock"
        ],
        "hostids": hostid
    }

    items = zabbix_request("item.get", params)

    summary = {
        "total": len(items),
        "enabled": 0,
        "disabled": 0,
        "unsupported": 0,
        "without_data": 0,
        "latest_clock": 0,
        "unsupported_items": []
    }

    for item in items:
        status = str(item.get("status"))
        state = str(item.get("state"))
        lastclock_raw = item.get("lastclock") or "0"

        try:
            lastclock = int(lastclock_raw)
        except ValueError:
            lastclock = 0

        if status == "0":
            summary["enabled"] += 1
        elif status == "1":
            summary["disabled"] += 1

        if state == "1":
            summary["unsupported"] += 1
            summary["unsupported_items"].append({
                "itemid": item.get("itemid"),
                "name": item.get("name"),
                "key": item.get("key_")
            })

        if lastclock == 0:
            summary["without_data"] += 1

        if lastclock > summary["latest_clock"]:
            summary["latest_clock"] = lastclock

    return summary


def filter_dependent_problems(problems):
    """
    Filtra problemas cuyos triggers dependen de otro trigger que también
    tiene un problema activo. Esto replica el comportamiento de la web de Zabbix
    que oculta el trigger dependiente cuando su dependencia está activa.
    Ejemplo: si >60°C (High) está activo, oculta >50°C (Warning) porque
    el trigger de >50 depende del de >60.
    """
    if not problems:
        return problems

    # Recolectar los trigger IDs (objectid) de los problemas activos
    trigger_ids = list(set(
        str(problem.get("objectid"))
        for problem in problems
        if problem.get("objectid")
    ))

    if not trigger_ids:
        return problems

    # Consultar triggers con sus dependencias
    try:
        triggers = zabbix_request("trigger.get", {
            "output": ["triggerid"],
            "triggerids": trigger_ids,
            "selectDependencies": ["triggerid"]
        })
    except Exception:
        # Si falla, devolver sin filtrar
        return problems

    # Set de trigger IDs activos (que tienen problema)
    active_trigger_ids = set(trigger_ids)

    # Identificar triggers que dependen de otro trigger activo
    triggers_to_hide = set()
    for trigger in triggers:
        triggerid = str(trigger.get("triggerid"))
        dependencies = trigger.get("dependencies", [])
        for dep in dependencies:
            dep_triggerid = str(dep.get("triggerid"))
            if dep_triggerid in active_trigger_ids:
                # Este trigger depende de otro que también está activo
                triggers_to_hide.add(triggerid)
                break

    # Filtrar problemas de triggers dependientes
    return [
        problem for problem in problems
        if str(problem.get("objectid")) not in triggers_to_hide
    ]


def get_host_problems(hostid, limit=20):
    """
    Obtiene problemas activos asociados a un host.
    Excluye problemas suprimidos, síntomas y dependencias de triggers.
    """
    params = {
        "output": [
            "eventid",
            "objectid",
            "name",
            "severity",
            "clock",
            "acknowledged",
            "suppressed",
            "cause_eventid"
        ],
        "hostids": hostid,
        "sortfield": "eventid",
        "sortorder": "DESC",
        "limit": limit
    }

    try:
        problems = zabbix_request("problem.get", params)
    except Exception:
        params["output"] = [
            "eventid", "objectid", "name", "severity",
            "clock", "acknowledged", "suppressed"
        ]
        try:
            problems = zabbix_request("problem.get", params)
        except Exception:
            params["output"] = [
                "eventid", "objectid", "name", "severity",
                "clock", "acknowledged"
            ]
            problems = zabbix_request("problem.get", params)

    filtered = []
    for problem in problems:
        if str(problem.get("suppressed", "0")) == "1":
            continue
        if str(problem.get("cause_eventid", "0")) != "0":
            continue
        filtered.append(problem)

    return filter_dependent_problems(filtered)


def get_active_problems(limit=None):
    """
    Obtiene problemas activos generales de Zabbix.
    Excluye problemas suprimidos (mantenimiento) y problemas síntoma (Zabbix 7.0+).
    Trae los campos suppressed y cause_eventid para filtrar en Python.
    """
    if limit is None:
        limit = settings.default_problem_limit

    params = {
        "output": [
            "eventid",
            "objectid",
            "name",
            "severity",
            "clock",
            "acknowledged",
            "suppressed",
            "cause_eventid"
        ],
        "sortfield": "eventid",
        "sortorder": "DESC",
        "limit": limit
    }

    try:
        problems = zabbix_request("problem.get", params)
    except Exception:
        params["output"] = [
            "eventid", "objectid", "name", "severity",
            "clock", "acknowledged", "suppressed"
        ]
        try:
            problems = zabbix_request("problem.get", params)
        except Exception:
            params["output"] = [
                "eventid", "objectid", "name", "severity",
                "clock", "acknowledged"
            ]
            problems = zabbix_request("problem.get", params)

    filtered = []
    for problem in problems:
        if str(problem.get("suppressed", "0")) == "1":
            continue
        if str(problem.get("cause_eventid", "0")) != "0":
            continue
        filtered.append(problem)

    return filter_dependent_problems(filtered)


def get_host_groups(limit=None):
    """
    Obtiene grupos de hosts de Zabbix.
    Incluye hosts visibles para poder contar cuántos hosts ve el token/API user.
    """
    if limit is None:
        limit = settings.host_search_limit

    params = {
        "output": ["groupid", "name"],
        "selectHosts": ["hostid"],
        "sortfield": "name",
        "limit": limit
    }

    return zabbix_request("hostgroup.get", params)


def search_host_groups(search_text, limit=None):
    """
    Busca grupos de hosts por nombre.
    Incluye hosts visibles para mostrar un conteo antes de analizarlos.
    """
    if limit is None:
        limit = settings.host_search_limit

    params = {
        "output": ["groupid", "name"],
        "selectHosts": ["hostid"],
        "search": {
            "name": search_text
        },
        "sortfield": "name",
        "limit": limit
    }

    return zabbix_request("hostgroup.get", params)


def get_hosts_by_groupid(groupid, limit=None):
    """
    Obtiene hosts de un grupo específico.
    Incluye interfaces para mostrar IP en los resúmenes de grupo.
    """
    if limit is None:
        limit = settings.group_host_analysis_limit

    params = {
        "output": ["hostid", "host", "name", "status"],
        "selectInterfaces": [
            "interfaceid",
            "type",
            "ip",
            "dns",
            "port",
            "main",
            "useip"
        ],
        "selectGroups": ["groupid", "name"],
        "groupids": groupid,
        "sortfield": "name",
        "limit": limit
    }

    return zabbix_request("host.get", params)
