from signals import print_sre_report, print_executive_summary
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from config import settings
from zabbix.client import (
    get_hosts,
    search_hosts,
    get_host_details,
    get_host_items,
    get_host_item_summary,
    get_host_problems,
    get_host_groups,
    get_hosts_by_groupid,
    get_hosts_with_interfaces,
    get_active_problems
)

BACK_COMMANDS = ["b", "back", "atras", "atrás"]


def is_back_command(value):
    return value.strip().lower() in BACK_COMMANDS


def ask_input(prompt):
    value = input(prompt).strip()
    if is_back_command(value):
        return None
    return value


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def similarity_score(text_a, text_b):
    return SequenceMatcher(
        None,
        normalize_text(text_a),
        normalize_text(text_b)
    ).ratio()


def format_status(status):
    if str(status) == "0":
        return "Enabled"
    elif str(status) == "1":
        return "Disabled"
    return "Unknown"


def format_status_es(status):
    if str(status) == "0":
        return "Habilitado"
    elif str(status) == "1":
        return "Deshabilitado"
    return "Desconocido"


def format_item_state(state):
    if str(state) == "0":
        return "Normal"
    elif str(state) == "1":
        return "Unsupported"
    return "Unknown"


def format_problem_severity(severity):
    mapping = {
        "0": "Not classified",
        "1": "Information",
        "2": "Warning",
        "3": "Average",
        "4": "High",
        "5": "Disaster"
    }
    return mapping.get(str(severity), "Unknown")


def format_problem_severity_es(severity):
    mapping = {
        "0": "No clasificado",
        "1": "Información",
        "2": "Advertencia",
        "3": "Promedio",
        "4": "Alta",
        "5": "Desastre"
    }
    return mapping.get(str(severity), "Desconocida")


def format_lastclock(lastclock):
    if not lastclock or str(lastclock) == "0":
        return "No data"
    try:
        return datetime.fromtimestamp(int(lastclock)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "Invalid date"


def format_lastclock_es(lastclock):
    if not lastclock or str(lastclock) == "0":
        return "Sin datos"
    try:
        return datetime.fromtimestamp(int(lastclock)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "Fecha inválida"


def format_interface_type(interface_type):
    mapping = {
        "1": "Agent",
        "2": "SNMP",
        "3": "IPMI",
        "4": "JMX"
    }
    return mapping.get(str(interface_type), "Unknown")


def get_primary_interface(host):
    """
    Devuelve la interfaz principal del host.
    Si no hay una interfaz marcada como main=1, devuelve la primera.
    """
    interfaces = host.get("interfaces", [])
    if not interfaces:
        return None
    for interface in interfaces:
        if str(interface.get("main")) == "1":
            return interface
    return interfaces[0]


def get_host_ip(host):
    interface = get_primary_interface(host)
    if not interface:
        return ""
    return interface.get("ip") or ""


def get_host_dns(host):
    interface = get_primary_interface(host)
    if not interface:
        return ""
    return interface.get("dns") or ""


def get_host_interface_type(host):
    interface = get_primary_interface(host)
    if not interface:
        return ""
    return format_interface_type(interface.get("type"))


def get_host_groups_text(host):
    groups = host.get("groups", [])
    if not groups:
        return ""
    return ", ".join(group.get("name", "") for group in groups)


def print_hosts(hosts):
    if not hosts:
        print("\nNo hosts found.")
        return
    print(f"\nTotal hosts shown: {len(hosts)}\n")
    for host in hosts:
        hostid = host.get("hostid", "")
        name = host.get("name") or host.get("host", "")
        status = format_status(host.get("status"))
        ip = get_host_ip(host)
        dns = get_host_dns(host)
        interface_type = get_host_interface_type(host)
        print(
            f"{hostid} | {name} | IP: {ip or '-'} | "
            f"DNS: {dns or '-'} | Interface: {interface_type or '-'} | {status}"
        )


def print_host_groups(groups):
    if not groups:
        print("\nNo host groups found.")
        return
    print(f"\nTotal host groups shown: {len(groups)}\n")
    for group in groups:
        hosts_visible = len(group.get("hosts", []))
        print(f"{group.get('groupid')} | {group.get('name')} | Hosts visible: {hosts_visible}")


def find_host_groups_by_text(search_text, groups, max_results=20):
    """
    Busca grupos por coincidencia parcial real.
    No usa similitud agresiva para evitar falsos positivos.
    """
    search_normalized = normalize_text(search_text)
    results = []
    for group in groups:
        group_name = group.get("name", "")
        group_normalized = normalize_text(group_name)
        if search_normalized in group_normalized:
            results.append(group)
    return results[:max_results]


def smart_search_host_groups(search_text):
    """
    Busca host groups localmente sobre los grupos visibles.
    """
    all_groups = get_host_groups(limit=1000)
    return find_host_groups_by_text(search_text, all_groups)


def print_host_details(host):
    if not host:
        print("\nHost not found.")
        return
    print("\nHost details")
    print("-" * 50)
    print(f"Host ID: {host.get('hostid')}")
    print(f"Technical name: {host.get('host')}")
    print(f"Visible name: {host.get('name')}")
    print(f"Status: {format_status(host.get('status'))}")
    print("\nInterfaces:")
    interfaces = host.get("interfaces", [])
    if interfaces:
        for interface in interfaces:
            interface_type = format_interface_type(interface.get("type"))
            ip = interface.get("ip")
            dns = interface.get("dns")
            port = interface.get("port")
            main = interface.get("main")
            print(
                f"- Type: {interface_type} | "
                f"IP: {ip or '-'} | "
                f"DNS: {dns or '-'} | "
                f"Port: {port or '-'} | "
                f"Main: {main}"
            )
    else:
        print("- No interfaces found")
    print("\nGroups:")
    groups = host.get("groups", [])
    if groups:
        for group in groups:
            print(f"- {group.get('name')}")
    else:
        print("- No groups found")
    print("\nTemplates:")
    templates = host.get("parentTemplates", [])
    if templates:
        for template in templates:
            print(f"- {template.get('name')}")
    else:
        print("- No templates found")
    print("\nTags:")
    tags = host.get("tags", [])
    if tags:
        for tag in tags:
            print(f"- {tag.get('tag')} = {tag.get('value')}")
    else:
        print("- No tags found")
    print("\nInventory:")
    inventory = host.get("inventory", {})
    if inventory:
        important_fields = [
            "type", "name", "alias", "os", "serialno_a",
            "model", "vendor", "location", "site_address_a"
        ]
        has_data = False
        for field in important_fields:
            value = inventory.get(field)
            if value:
                has_data = True
                print(f"- {field}: {value}")
        if not has_data:
            print("- Inventory exists but important fields are empty")
    else:
        print("- No inventory found")


def smart_search_hosts(search_text):
    """
    Busca hosts visibles por:
    - hostid
    - technical host name
    - visible name
    - IP
    - DNS
    - grupo
    La busqueda es local para poder encontrar IPs parciales como 10.57 o 192.168.
    """
    search_normalized = normalize_text(search_text)
    hosts = get_hosts_with_interfaces(limit=1000)
    results = []
    for host in hosts:
        hostid = normalize_text(host.get("hostid"))
        technical_name = normalize_text(host.get("host"))
        visible_name = normalize_text(host.get("name"))
        groups_text = normalize_text(get_host_groups_text(host))
        interfaces = host.get("interfaces", [])
        fields_to_match = [
            hostid,
            technical_name,
            visible_name,
            groups_text
        ]
        for interface in interfaces:
            fields_to_match.append(normalize_text(interface.get("ip")))
            fields_to_match.append(normalize_text(interface.get("dns")))
        matched = False
        for field in fields_to_match:
            if search_normalized and search_normalized in field:
                matched = True
                break
        if matched:
            results.append(host)
    return results


def print_smart_host_results(hosts):
    if not hosts:
        print("\nNo hosts found.")
        return
    print(f"\nTotal hosts found: {len(hosts)}\n")
    for host in hosts:
        hostid = host.get("hostid")
        name = host.get("name") or host.get("host")
        technical_name = host.get("host")
        status = format_status(host.get("status"))
        ip = get_host_ip(host)
        dns = get_host_dns(host)
        interface_type = get_host_interface_type(host)
        groups = get_host_groups_text(host)
        print(
            f"{hostid} | {name} | Technical: {technical_name} | "
            f"IP: {ip or '-'} | DNS: {dns or '-'} | "
            f"Interface: {interface_type or '-'} | Groups: {groups or '-'} | {status}"
        )


def search_host_and_select_hostid():
    """
    Flujo interactivo:
    1. Busca host por nombre/IP/DNS/grupo/hostid.
    2. Muestra resultados.
    3. Si solo hay un resultado, usa ese hostid automaticamente.
    4. Si hay varios resultados, permite seleccionar un hostid.
    """
    search_text = ask_input(
        "\nType host name, IP, DNS, group, hostid or part of it, or 'b' to go back: "
    )
    if search_text is None:
        return None
    if not search_text:
        print("\nSearch text cannot be empty.")
        return None
    hosts = smart_search_hosts(search_text)
    if not hosts:
        print("\nNo hosts found.")
        return None
    print_smart_host_results(hosts)
    if len(hosts) == 1:
        hostid = hosts[0].get("hostid")
        name = hosts[0].get("name") or hosts[0].get("host")
        print(f"\nOnly one host found. Using hostid: {hostid} | {name}")
        return hostid
    hostid = ask_input(
        "\nType the hostid to continue, or 'b' to go back: "
    )
    if hostid is None:
        return None
    if not hostid:
        print("\nHost ID cannot be empty.")
        return None
    valid_hostids = [str(host.get("hostid")) for host in hosts]
    if str(hostid) not in valid_hostids:
        print("\nThe hostid you typed was not in the search results.")
        print("Run the search again and choose one of the displayed host IDs.")
        return None
    return hostid


def print_host_items(items):
    if not items:
        print("\nNo items found.")
        return
    print(f"\nTotal items shown: {len(items)}")
    print("-" * 100)
    for item in items:
        itemid = item.get("itemid")
        name = item.get("name")
        key = item.get("key_")
        status = format_status(item.get("status"))
        state = format_item_state(item.get("state"))
        lastvalue = item.get("lastvalue", "")
        units = item.get("units", "")
        lastclock = format_lastclock(item.get("lastclock"))
        if units and lastvalue:
            value_to_show = f"{lastvalue} {units}"
        else:
            value_to_show = lastvalue if lastvalue else "No value"
        print(f"\nItem ID: {itemid}")
        print(f"Name: {name}")
        print(f"Key: {key}")
        print(f"Status: {status}")
        print(f"State: {state}")
        print(f"Last value: {value_to_show}")
        print(f"Last clock: {lastclock}")


def build_host_assessment(host, item_summary, problems):
    findings = []
    review_points = []
    admin_checks = []
    management_follow_up = []
    priority = "Low"
    host_status = str(host.get("status"))
    interfaces = host.get("interfaces", [])
    templates = host.get("parentTemplates", [])
    tags = host.get("tags", [])
    active_high_problems = [
        problem for problem in problems
        if str(problem.get("severity")) in ["4", "5"]
    ]
    if host_status == "1":
        findings.append("The host is disabled in Zabbix.")
        review_points.append(
            "Confirm whether this host should remain disabled or if it should be included in operational monitoring."
        )
        admin_checks.append(
            "Review host status and validate if the disabled condition is intentional."
        )
        priority = "Low"
    if not interfaces:
        findings.append("The host has no configured interfaces.")
        review_points.append(
            "The host may not be able to collect data because no monitoring interface is configured."
        )
        admin_checks.append(
            "Review whether the host requires Agent, SNMP, JMX or IPMI interface."
        )
        priority = "High"
    if not templates:
        findings.append("The host has no templates assigned.")
        review_points.append(
            "The host may have incomplete monitoring coverage because no template is assigned."
        )
        admin_checks.append(
            "Review template assignment according to the device or system type."
        )
        priority = "High"
    if not tags:
        findings.append("The host has no tags configured.")
        review_points.append(
            "The host lacks business or operational classification for reporting."
        )
        admin_checks.append(
            "Review minimum tags such as system, owner, location and criticality."
        )
        if priority == "Low":
            priority = "Medium"
    if item_summary["total"] == 0:
        findings.append("The host has no monitoring items.")
        review_points.append(
            "The host may not be effectively monitored because no items were found."
        )
        admin_checks.append(
            "Review template assignment, item creation or host configuration."
        )
        priority = "High"
    if item_summary["unsupported"] > 0:
        findings.append(f"The host has {item_summary['unsupported']} unsupported items.")
        review_points.append(
            "Unsupported items can reduce monitoring quality and should be reviewed by the Zabbix administrator."
        )
        admin_checks.append(
            "Review item keys, SNMP OIDs, macros, permissions, preprocessing or template compatibility."
        )
        if priority != "High":
            priority = "Medium"
    if item_summary["without_data"] > 0:
        findings.append(f"The host has {item_summary['without_data']} items without data.")
        review_points.append(
            "Items without data may indicate partial loss of visibility."
        )
        admin_checks.append(
            "Review item status, lastclock, agent/SNMP availability, proxy availability and update interval."
        )
        if priority != "High":
            priority = "Medium"
    if active_high_problems:
        findings.append(f"The host has {len(active_high_problems)} active High/Disaster problems.")
        review_points.append(
            "High or Disaster problems should be reviewed with priority by the responsible team."
        )
        management_follow_up.append(
            "Confirm ownership and define follow-up with the responsible technical or process owner."
        )
        priority = "High"
    if problems and not active_high_problems:
        findings.append(f"The host has {len(problems)} active problems.")
        review_points.append(
            "Active problems should be reviewed to determine if they represent real issues, accepted conditions or monitoring noise."
        )
        if priority == "Low":
            priority = "Medium"
    if not findings:
        assessment = "The host appears to be monitored correctly. No major monitoring gaps were detected."
        review_points.append("No immediate review point detected for this host.")
        admin_checks.append("Continue regular monitoring.")
    else:
        assessment = "The host has monitoring findings that should be reviewed."
    if not management_follow_up:
        management_follow_up.append(
            "No management escalation is suggested from this host diagnostic unless the technical owner confirms operational impact."
        )
    return {
        "priority": priority,
        "assessment": assessment,
        "findings": findings,
        "review_points": review_points,
        "admin_checks": admin_checks,
        "management_follow_up": management_follow_up
    }


def build_host_diagnostic_data(hostid):
    host = get_host_details(hostid)
    if not host:
        return None
    item_summary = get_host_item_summary(hostid)
    problems = get_host_problems(hostid)
    assessment = build_host_assessment(host, item_summary, problems)
    return {
        "host": host,
        "item_summary": item_summary,
        "problems": problems,
        "assessment": assessment
    }


def print_host_diagnostic_report(hostid):
    diagnostic_data = build_host_diagnostic_data(hostid)
    if not diagnostic_data:
        print("\nHost not found.")
        return
    host = diagnostic_data["host"]
    item_summary = diagnostic_data["item_summary"]
    problems = diagnostic_data["problems"]
    assessment = diagnostic_data["assessment"]
    print("\nHost Diagnostic Report")
    print("=" * 70)
    print(f"Host ID: {host.get('hostid')}")
    print(f"Technical name: {host.get('host')}")
    print(f"Visible name: {host.get('name')}")
    print(f"Status: {format_status(host.get('status'))}")
    print(f"Priority: {assessment['priority']}")
    print("\nTechnical summary")
    print("-" * 70)
    interfaces = host.get("interfaces", [])
    templates = host.get("parentTemplates", [])
    groups = host.get("groups", [])
    tags = host.get("tags", [])
    print(f"Groups: {len(groups)}")
    print(f"Interfaces: {len(interfaces)}")
    print(f"Templates: {len(templates)}")
    print(f"Tags: {len(tags)}")
    print(f"Total items: {item_summary['total']}")
    print(f"Enabled items: {item_summary['enabled']}")
    print(f"Disabled items: {item_summary['disabled']}")
    print(f"Unsupported items: {item_summary['unsupported']}")
    print(f"Items without data: {item_summary['without_data']}")
    print(f"Latest data received: {format_lastclock(item_summary['latest_clock'])}")
    print(f"Active problems: {len(problems)}")
    print("\nAssessment")
    print("-" * 70)
    print(assessment["assessment"])
    print("\nFindings")
    print("-" * 70)
    if assessment["findings"]:
        for finding in assessment["findings"]:
            print(f"- {finding}")
    else:
        print("- No relevant findings detected.")
    print("\nReview points")
    print("-" * 70)
    for point in assessment["review_points"]:
        print(f"- {point}")
    print("\nAdmin technical checks")
    print("-" * 70)
    for check in assessment["admin_checks"]:
        print(f"- {check}")
    print("\nManagement follow-up")
    print("-" * 70)
    for follow_up in assessment["management_follow_up"]:
        print(f"- {follow_up}")
    if problems:
        print("\nActive problems")
        print("-" * 70)
        for problem in problems:
            name = problem.get("name")
            severity = format_problem_severity(problem.get("severity"))
            clock = format_lastclock(problem.get("clock"))
            acknowledged = problem.get("acknowledged")
            print(
                f"- [{severity}] {name} | "
                f"Since: {clock} | "
                f"Acknowledged: {acknowledged}"
            )
    if item_summary["unsupported_items"]:
        print("\nUnsupported items sample")
        print("-" * 70)
        for item in item_summary["unsupported_items"][:10]:
            print(f"- {item.get('name')} | Key: {item.get('key')}")


def render_host_diagnostic_markdown(diagnostic_data):
    host = diagnostic_data["host"]
    item_summary = diagnostic_data["item_summary"]
    problems = diagnostic_data["problems"]
    assessment = diagnostic_data["assessment"]
    interfaces = host.get("interfaces", [])
    templates = host.get("parentTemplates", [])
    groups = host.get("groups", [])
    tags = host.get("tags", [])
    lines = []
    lines.append("# Host Diagnostic Report")
    lines.append("")
    lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Environment: {settings.environment}")
    lines.append("")
    lines.append("## Host information")
    lines.append("")
    lines.append(f"- Host ID: {host.get('hostid')}")
    lines.append(f"- Technical name: {host.get('host')}")
    lines.append(f"- Visible name: {host.get('name')}")
    lines.append(f"- Status: {format_status(host.get('status'))}")
    lines.append(f"- Priority: {assessment['priority']}")
    lines.append("")
    lines.append("## Technical summary")
    lines.append("")
    lines.append(f"- Groups: {len(groups)}")
    lines.append(f"- Interfaces: {len(interfaces)}")
    lines.append(f"- Templates: {len(templates)}")
    lines.append(f"- Tags: {len(tags)}")
    lines.append(f"- Total items: {item_summary['total']}")
    lines.append(f"- Enabled items: {item_summary['enabled']}")
    lines.append(f"- Disabled items: {item_summary['disabled']}")
    lines.append(f"- Unsupported items: {item_summary['unsupported']}")
    lines.append(f"- Items without data: {item_summary['without_data']}")
    lines.append(f"- Latest data received: {format_lastclock(item_summary['latest_clock'])}")
    lines.append(f"- Active problems: {len(problems)}")
    lines.append("")
    lines.append("## Assessment")
    lines.append("")
    lines.append(assessment["assessment"])
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    if assessment["findings"]:
        for finding in assessment["findings"]:
            lines.append(f"- {finding}")
    else:
        lines.append("- No relevant findings detected.")
    lines.append("")
    lines.append("## Review points")
    lines.append("")
    for point in assessment["review_points"]:
        lines.append(f"- {point}")
    lines.append("")
    lines.append("## Admin technical checks")
    lines.append("")
    for check in assessment["admin_checks"]:
        lines.append(f"- {check}")
    lines.append("")
    lines.append("## Management follow-up")
    lines.append("")
    for follow_up in assessment["management_follow_up"]:
        lines.append(f"- {follow_up}")
    lines.append("")
    if problems:
        lines.append("## Active problems")
        lines.append("")
        for problem in problems:
            name = problem.get("name")
            severity = format_problem_severity(problem.get("severity"))
            clock = format_lastclock(problem.get("clock"))
            acknowledged = problem.get("acknowledged")
            lines.append(
                f"- [{severity}] {name} | Since: {clock} | Acknowledged: {acknowledged}"
            )
        lines.append("")
    if item_summary["unsupported_items"]:
        lines.append("## Unsupported items sample")
        lines.append("")
        for item in item_summary["unsupported_items"][:10]:
            lines.append(f"- {item.get('name')} | Key: {item.get('key')}")
        lines.append("")
    lines.append("## Management interpretation")
    lines.append("")
    lines.append(
        "This report identifies monitoring findings that may affect visibility, "
        "monitoring quality or operational follow-up. The final remediation path "
        "should be defined by the responsible technical or process owner."
    )
    lines.append("")
    return "\n".join(lines)


def save_host_diagnostic_report(hostid):
    diagnostic_data = build_host_diagnostic_data(hostid)
    if not diagnostic_data:
        print("\nHost not found.")
        return
    host = diagnostic_data["host"]
    host_name = host.get("name") or host.get("host") or f"host_{hostid}"
    safe_host_name = (
        host_name.replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )
    reports_dir = Path(settings.report_output_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"host_diagnostic_{safe_host_name}_{hostid}_{timestamp}.md"
    markdown_content = render_host_diagnostic_markdown(diagnostic_data)
    report_path.write_text(markdown_content, encoding="utf-8")
    print("\nReport generated successfully.")
    print(f"Path: {report_path}")


def build_host_group_health_summary(groupid, limit=None):
    if limit is None:
        limit = settings.group_host_analysis_limit
    hosts = get_hosts_by_groupid(groupid, limit=limit)
    summary = {
        "groupid": groupid,
        "hosts_analyzed": len(hosts),
        "analysis_limit": limit,
        "enabled_hosts": 0,
        "disabled_hosts": 0,
        "hosts_with_active_problems": 0,
        "hosts_with_high_or_disaster": 0,
        "hosts_with_unsupported_items": 0,
        "hosts_with_items_without_data": 0,
        "total_unsupported_items": 0,
        "total_items_without_data": 0,
        "priority": "Low",
        "review_points": [],
        "admin_checks": [],
        "management_follow_up": []
    }
    host_results = []
    if not hosts:
        summary["priority"] = "Not analyzed"
        summary["review_points"].append("No hosts were found in this group.")
        summary["review_points"].append(
            "Possible causes: the group is empty, the selected group is not the intended one, or the API user has no permission to view hosts in this group."
        )
        summary["admin_checks"].append(
            "Validate the group ID, search the group again using option 7, and confirm API permissions for this host group."
        )
        summary["management_follow_up"].append(
            "No management conclusion should be generated because no hosts were analyzed."
        )
        return summary, host_results
    for host in hosts:
        hostid = host.get("hostid")
        host_name = host.get("name") or host.get("host")
        ip = get_host_ip(host)
        if str(host.get("status")) == "0":
            summary["enabled_hosts"] += 1
        elif str(host.get("status")) == "1":
            summary["disabled_hosts"] += 1
        item_summary = get_host_item_summary(hostid)
        problems = get_host_problems(hostid, limit=20)
        high_or_disaster = [
            problem for problem in problems
            if str(problem.get("severity")) in ["4", "5"]
        ]
        if problems:
            summary["hosts_with_active_problems"] += 1
        if high_or_disaster:
            summary["hosts_with_high_or_disaster"] += 1
        if item_summary["unsupported"] > 0:
            summary["hosts_with_unsupported_items"] += 1
            summary["total_unsupported_items"] += item_summary["unsupported"]
        if item_summary["without_data"] > 0:
            summary["hosts_with_items_without_data"] += 1
            summary["total_items_without_data"] += item_summary["without_data"]
        host_results.append({
            "hostid": hostid,
            "name": host_name,
            "ip": ip,
            "status": format_status(host.get("status")),
            "active_problems": len(problems),
            "high_or_disaster": len(high_or_disaster),
            "unsupported_items": item_summary["unsupported"],
            "items_without_data": item_summary["without_data"]
        })
    if summary["hosts_with_high_or_disaster"] > 0:
        summary["priority"] = "High"
        summary["review_points"].append(
            "The group has hosts with active High or Disaster problems."
        )
        summary["management_follow_up"].append(
            "Confirm ownership and follow-up for hosts with High or Disaster problems."
        )
    if summary["hosts_with_active_problems"] > 0 and summary["priority"] != "High":
        summary["priority"] = "Medium"
        summary["review_points"].append(
            "The group has hosts with active problems that should be reviewed."
        )
    if summary["hosts_with_unsupported_items"] > 0:
        if summary["priority"] == "Low":
            summary["priority"] = "Medium"
        summary["review_points"].append(
            "The group has unsupported items. This is relevant for monitoring quality."
        )
        summary["admin_checks"].append(
            "Review unsupported items by host, template, key, OID, macro or preprocessing rule."
        )
    if summary["hosts_with_items_without_data"] > 0:
        if summary["priority"] == "Low":
            summary["priority"] = "Medium"
        summary["review_points"].append(
            "The group has items without data. This may indicate partial visibility gaps."
        )
        summary["admin_checks"].append(
            "Review hosts with items without data, lastclock values, proxy availability and item update intervals."
        )
    if not summary["review_points"]:
        summary["review_points"].append(
            "No major monitoring findings were detected in the analyzed hosts."
        )
    if not summary["admin_checks"]:
        summary["admin_checks"].append(
            "No specific Zabbix administration checks were detected for this group sample."
        )
    if not summary["management_follow_up"]:
        summary["management_follow_up"].append(
            "No management escalation is suggested unless the technical review confirms operational impact."
        )
    return summary, host_results


def print_host_group_health_summary(groupid):
    summary, host_results = build_host_group_health_summary(groupid)
    print("\nHost Group Health Summary")
    print("=" * 70)
    print(f"Group ID: {summary['groupid']}")
    print(f"Hosts analyzed: {summary['hosts_analyzed']}")
    print(f"Analysis limit: {summary['analysis_limit']}")
    print(f"Priority: {summary['priority']}")
    print("\nGroup summary")
    print("-" * 70)
    print(f"Enabled hosts: {summary['enabled_hosts']}")
    print(f"Disabled hosts: {summary['disabled_hosts']}")
    print(f"Hosts with active problems: {summary['hosts_with_active_problems']}")
    print(f"Hosts with High/Disaster problems: {summary['hosts_with_high_or_disaster']}")
    print(f"Hosts with unsupported items: {summary['hosts_with_unsupported_items']}")
    print(f"Hosts with items without data: {summary['hosts_with_items_without_data']}")
    print(f"Total unsupported items: {summary['total_unsupported_items']}")
    print(f"Total items without data: {summary['total_items_without_data']}")
    print("\nReview points")
    print("-" * 70)
    for point in summary["review_points"]:
        print(f"- {point}")
    print("\nAdmin technical checks")
    print("-" * 70)
    for check in summary["admin_checks"]:
        print(f"- {check}")
    print("\nManagement follow-up")
    print("-" * 70)
    for follow_up in summary["management_follow_up"]:
        print(f"- {follow_up}")
    if not host_results:
        print("\nTop hosts requiring review")
        print("-" * 70)
        print("- No hosts were analyzed.")
        return
    print("\nTop hosts requiring review")
    print("-" * 70)
    relevant_hosts = [
        host for host in host_results
        if host["active_problems"] > 0
        or host["unsupported_items"] > 0
        or host["items_without_data"] > 0
    ]
    if not relevant_hosts:
        print("- No hosts requiring review in the analyzed sample.")
        return
    for host in relevant_hosts[:20]:
        print(
            f"- {host['hostid']} | {host['name']} | IP: {host['ip'] or '-'} | "
            f"Problems: {host['active_problems']} | "
            f"High/Disaster: {host['high_or_disaster']} | "
            f"Unsupported: {host['unsupported_items']} | "
            f"Without data: {host['items_without_data']}"
        )


def get_tag_value(tags, tag_name):
    """
    Extrae el valor de un tag especifico de la lista de tags del host.
    Retorna el valor o cadena vacia si no existe.
    """
    for tag in tags:
        if normalize_text(tag.get("tag")) == normalize_text(tag_name):
            return tag.get("value", "")
    return ""


def construir_resumen_diario_zabbix():
    """
    Construye una radiografia diaria general del ambiente Zabbix visible para el usuario API.
    No intenta solucionar problemas; solo identifica hallazgos para revision.
    """
    hosts = get_hosts_with_interfaces(limit=1000)
    problemas_activos = get_active_problems(limit=100)
    resumen = {
        "ambiente": settings.environment,
        "hosts_analizados": len(hosts),
        "hosts_habilitados": 0,
        "hosts_deshabilitados": 0,
        "problemas_activos": len(problemas_activos),
        "problemas_altos_o_desastre": 0,
        "hosts_con_problemas": 0,
        "hosts_con_problemas_altos_o_desastre": 0,
        "hosts_con_items_no_soportados": 0,
        "hosts_con_items_sin_datos": 0,
        "hosts_sin_tags": 0,
        "total_items_no_soportados": 0,
        "total_items_sin_datos": 0,
        "prioridad_general": "Baja",
        "insights": [],
        "revision_admin_zabbix": [],
        "seguimiento_gerencial": [],
        "detalle_problemas": [],
        "resultados_hosts": []
    }
    for problema in problemas_activos:
        if str(problema.get("severity")) in ["4", "5"]:
            resumen["problemas_altos_o_desastre"] += 1
    for host in hosts:
        hostid = host.get("hostid")
        nombre_host = host.get("name") or host.get("host")
        estado_host = str(host.get("status"))
        ip = get_host_ip(host)
        grupos = get_host_groups_text(host)
        if estado_host == "0":
            resumen["hosts_habilitados"] += 1
        elif estado_host == "1":
            resumen["hosts_deshabilitados"] += 1
        host_detallado = get_host_details(hostid)
        tags = host_detallado.get("tags", []) if host_detallado else []
        if not tags:
            resumen["hosts_sin_tags"] += 1
        resumen_items = get_host_item_summary(hostid)
        problemas_host = get_host_problems(hostid, limit=20)
        problemas_altos_o_desastre_host = [
            problema for problema in problemas_host
            if str(problema.get("severity")) in ["4", "5"]
        ]
        if problemas_host:
            resumen["hosts_con_problemas"] += 1
        if problemas_altos_o_desastre_host:
            resumen["hosts_con_problemas_altos_o_desastre"] += 1
        if resumen_items["unsupported"] > 0:
            resumen["hosts_con_items_no_soportados"] += 1
            resumen["total_items_no_soportados"] += resumen_items["unsupported"]
        if resumen_items["without_data"] > 0:
            resumen["hosts_con_items_sin_datos"] += 1
            resumen["total_items_sin_datos"] += resumen_items["without_data"]
        prioridad_host = "Baja"
        if problemas_altos_o_desastre_host:
            prioridad_host = "Alta"
        elif (
            problemas_host
            or resumen_items["unsupported"] > 0
            or resumen_items["without_data"] > 0
            or not tags
        ):
            prioridad_host = "Media"
        resumen["resultados_hosts"].append({
            "hostid": hostid,
            "nombre": nombre_host,
            "ip": ip,
            "grupos": grupos,
            "estado": format_status_es(estado_host),
            "problemas_activos": len(problemas_host),
            "problemas_altos_o_desastre": len(problemas_altos_o_desastre_host),
            "items_no_soportados": resumen_items["unsupported"],
            "items_sin_datos": resumen_items["without_data"],
            "tags": len(tags),
            "dominio": get_tag_value(tags, "dominio"),
            "responsable": get_tag_value(tags, "responsable"),
            "criticidad": get_tag_value(tags, "criticidad"),
            "tipo": get_tag_value(tags, "tipo"),
            "prioridad": prioridad_host
        })
        for problema in problemas_host:
            resumen["detalle_problemas"].append({
                "host": nombre_host,
                "ip": ip,
                "dominio": get_tag_value(tags, "dominio"),
                "responsable": get_tag_value(tags, "responsable"),
                "nombre_problema": problema.get("name"),
                "severidad": format_problem_severity_es(problema.get("severity")),
                "severidad_num": str(problema.get("severity")),
                "clock": problema.get("clock"),
                "acknowledged": problema.get("acknowledged")
            })
    if (
        resumen["problemas_altos_o_desastre"] > 0
        or resumen["hosts_con_problemas_altos_o_desastre"] > 0
    ):
        resumen["prioridad_general"] = "Alta"
    elif (
        resumen["problemas_activos"] > 0
        or resumen["hosts_con_items_no_soportados"] > 0
        or resumen["hosts_con_items_sin_datos"] > 0
        or resumen["hosts_sin_tags"] > 0
    ):
        resumen["prioridad_general"] = "Media"
    if resumen["hosts_con_items_no_soportados"] > 0:
        resumen["revision_admin_zabbix"].append(
            "Revisar items no soportados. Posibles causas: keys incorrectos, OIDs SNMP, macros, permisos, preprocesamiento o compatibilidad de plantillas."
        )
    if resumen["hosts_con_items_sin_datos"] > 0:
        resumen["revision_admin_zabbix"].append(
            "Revisar items sin datos. Validar lastclock, estado del item, disponibilidad Agent/SNMP, proxy y frecuencia de actualizacion."
        )
    if resumen["hosts_sin_tags"] > 0:
        resumen["revision_admin_zabbix"].append(
            "Revisar hosts sin tags. La falta de tags limita reportes por dominio, responsable, criticidad, ubicacion o servicio."
        )
    if resumen["hosts_con_problemas_altos_o_desastre"] > 0:
        resumen["seguimiento_gerencial"].append(
            "Existen hosts con problemas de severidad Alta o Desastre. Se debe confirmar responsable y seguimiento con el dueno tecnico o de proceso."
        )
    if resumen["prioridad_general"] == "Baja":
        resumen["seguimiento_gerencial"].append(
            "No se sugiere escalamiento gerencial, salvo que la revision tecnica confirme impacto operativo."
        )
    if not resumen["revision_admin_zabbix"]:
        resumen["revision_admin_zabbix"].append(
            "No se detectaron hallazgos mayores de administracion Zabbix en este resumen."
        )
    # Generar insights principales
    insights = []
    if resumen["problemas_altos_o_desastre"] > 0:
        insights.append(
            f"Hay {resumen['problemas_altos_o_desastre']} problema(s) de severidad Alta/Desastre que requiere(n) seguimiento."
        )
    if resumen["problemas_activos"] > 0 and resumen["problemas_altos_o_desastre"] == 0:
        insights.append(
            f"Hay {resumen['problemas_activos']} problema(s) activo(s); ninguno de severidad Alta/Desastre."
        )
    if resumen["total_items_sin_datos"] > 0:
        insights.append(
            f"Hay {resumen['total_items_sin_datos']} items sin datos en {resumen['hosts_con_items_sin_datos']} host(s); "
            f"se recomienda revisar si corresponden a items realmente esperados o a monitoreo no aplicable."
        )
    if resumen["hosts_sin_tags"] > 0:
        insights.append(
            f"Hay {resumen['hosts_sin_tags']} host(s) sin tags; esto limita reportes por dominio, responsable y criticidad."
        )
    if resumen["hosts_con_items_no_soportados"] > 0:
        insights.append(
            f"Hay {resumen['hosts_con_items_no_soportados']} host(s) con items no soportados "
            f"({resumen['total_items_no_soportados']} items en total); esto afecta la calidad del monitoreo."
        )
    if resumen["hosts_deshabilitados"] > 0:
        insights.append(
            f"Hay {resumen['hosts_deshabilitados']} host(s) deshabilitado(s); confirmar si es intencional."
        )
    if not insights:
        insights.append(
            "No se detectaron hallazgos relevantes en este ciclo de revision."
        )
    resumen["insights"] = insights
    return resumen


def imprimir_resumen_diario_zabbix():
    resumen = construir_resumen_diario_zabbix()
    print("\nResumen diario de salud de Zabbix")
    print("=" * 70)
    print(f"Ambiente: {resumen['ambiente']}")
    print(f"Hosts analizados: {resumen['hosts_analizados']}")
    print(f"Hosts habilitados: {resumen['hosts_habilitados']}")
    print(f"Hosts deshabilitados: {resumen['hosts_deshabilitados']}")
    print(f"Problemas activos: {resumen['problemas_activos']}")
    print(f"Problemas Alta/Desastre: {resumen['problemas_altos_o_desastre']}")
    print(f"Hosts con problemas activos: {resumen['hosts_con_problemas']}")
    print(f"Hosts con problemas Alta/Desastre: {resumen['hosts_con_problemas_altos_o_desastre']}")
    print(f"Hosts con items no soportados: {resumen['hosts_con_items_no_soportados']}")
    print(f"Hosts con items sin datos: {resumen['hosts_con_items_sin_datos']}")
    print(f"Hosts sin tags: {resumen['hosts_sin_tags']}")
    print(f"Total items no soportados: {resumen['total_items_no_soportados']}")
    print(f"Total items sin datos: {resumen['total_items_sin_datos']}")
    print(f"Prioridad general: {resumen['prioridad_general']}")
    print("\nInsights principales")
    print("-" * 70)
    for insight in resumen["insights"]:
        print(f"- {insight}")
    print("\nRevision tecnica del administrador Zabbix")
    print("-" * 70)
    for revision in resumen["revision_admin_zabbix"]:
        print(f"- {revision}")
    print("\nSeguimiento gerencial / duenos de proceso")
    print("-" * 70)
    for seguimiento in resumen["seguimiento_gerencial"]:
        print(f"- {seguimiento}")
    print("\nHosts principales que requieren revision")
    print("-" * 70)
    hosts_relevantes = [
        host for host in resumen["resultados_hosts"]
        if host["prioridad"] in ["Alta", "Media"]
        or host["problemas_activos"] > 0
        or host["items_no_soportados"] > 0
        or host["items_sin_datos"] > 0
        or host["tags"] == 0
    ]
    if not hosts_relevantes:
        print("- No hay hosts que requieran revision segun los criterios actuales.")
        return
    orden_prioridad = {
        "Alta": 3,
        "Media": 2,
        "Baja": 1
    }
    hosts_relevantes.sort(
        key=lambda host: (
            orden_prioridad.get(host["prioridad"], 0),
            host["problemas_altos_o_desastre"],
            host["problemas_activos"],
            host["items_no_soportados"],
            host["items_sin_datos"]
        ),
        reverse=True
    )
    for host in hosts_relevantes[:20]:
        print(
            f"- {host['hostid']} | {host['nombre']} | IP: {host['ip'] or '-'} | "
            f"Grupos: {host['grupos'] or '-'} | Prioridad: {host['prioridad']} | "
            f"Problemas: {host['problemas_activos']} | "
            f"Alta/Desastre: {host['problemas_altos_o_desastre']} | "
            f"No soportados: {host['items_no_soportados']} | "
            f"Sin datos: {host['items_sin_datos']} | "
            f"Tags: {host['tags']}"
        )


def calcular_duracion(clock):
    """
    Calcula la duracion de un problema desde su timestamp hasta ahora.
    Retorna un texto legible como '2d 7h' o '3h 25m'.
    """
    try:
        inicio = datetime.fromtimestamp(int(clock))
        ahora = datetime.now()
        diferencia = ahora - inicio
        dias = diferencia.days
        horas = diferencia.seconds // 3600
        minutos = (diferencia.seconds % 3600) // 60
        if dias > 0:
            return f"{dias}d {horas}h"
        elif horas > 0:
            return f"{horas}h {minutos}m"
        else:
            return f"{minutos}m"
    except Exception:
        return "desconocida"


def generar_cuerpo_correo_noc(resumen):
    """
    Genera el cuerpo de correo en texto plano para el NOC.
    Muestra todo el ambiente, solo problemas Warning y superior.
    """
    lineas = []
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    lineas.append(f"Resumen diario de salud Zabbix - {resumen['ambiente']}")
    lineas.append(f"Fecha: {fecha}")
    lineas.append(f"Prioridad general: {resumen['prioridad_general']}")
    lineas.append("")
    lineas.append("=" * 60)
    lineas.append("INSIGHTS PRINCIPALES")
    lineas.append("=" * 60)
    for insight in resumen.get("insights", []):
        lineas.append(f"- {insight}")
    lineas.append("")
    # Problemas activos (solo Warning y superior, severidad >= 2)
    problemas_noc = [
        p for p in resumen.get("detalle_problemas", [])
        if p["severidad_num"] in ["2", "3", "4", "5"]
    ]
    # Ordenar: primero los mas severos
    orden_severidad = {"5": 5, "4": 4, "3": 3, "2": 2}
    problemas_noc.sort(
        key=lambda p: orden_severidad.get(p["severidad_num"], 0),
        reverse=True
    )
    lineas.append("=" * 60)
    lineas.append(f"PROBLEMAS ACTIVOS ({len(problemas_noc)})")
    lineas.append("=" * 60)
    if problemas_noc:
        for p in problemas_noc:
            duracion = calcular_duracion(p["clock"])
            lineas.append(
                f"- [{p['severidad']}] {p['host']} ({p['ip'] or 'sin IP'}) "
                f"| Dominio: {p['dominio'] or '-'}"
            )
            lineas.append(
                f"  Problema: {p['nombre_problema']}"
            )
            lineas.append(
                f"  Desde: {format_lastclock_es(p['clock'])} | Duracion: {duracion}"
            )
            lineas.append("")
    else:
        lineas.append("- No hay problemas activos de severidad Warning o superior.")
        lineas.append("")
    # Hosts que requieren revision
    hosts_relevantes = [
        h for h in resumen.get("resultados_hosts", [])
        if h["prioridad"] in ["Alta", "Media"]
        or h["problemas_activos"] > 0
        or h["items_no_soportados"] > 0
        or h["items_sin_datos"] > 0
    ]
    orden_prioridad = {"Alta": 3, "Media": 2, "Baja": 1}
    hosts_relevantes.sort(
        key=lambda h: (
            orden_prioridad.get(h["prioridad"], 0),
            h["problemas_altos_o_desastre"],
            h["problemas_activos"],
            h["items_no_soportados"]
        ),
        reverse=True
    )
    lineas.append("=" * 60)
    lineas.append(f"HOSTS QUE REQUIEREN REVISION ({len(hosts_relevantes)})")
    lineas.append("=" * 60)
    if hosts_relevantes:
        for h in hosts_relevantes[:20]:
            lineas.append(
                f"- {h['nombre']} | IP: {h['ip'] or '-'} "
                f"| Dominio: {h.get('dominio') or '-'} "
                f"| Prioridad: {h['prioridad']}"
            )
            detalles = []
            if h["problemas_activos"] > 0:
                detalles.append(f"{h['problemas_activos']} problema(s)")
            if h["items_no_soportados"] > 0:
                detalles.append(f"{h['items_no_soportados']} no soportados")
            if h["items_sin_datos"] > 0:
                detalles.append(f"{h['items_sin_datos']} sin datos")
            if detalles:
                lineas.append(f"  {' | '.join(detalles)}")
            lineas.append("")
    else:
        lineas.append("- No hay hosts que requieran revision.")
        lineas.append("")
    # Revision tecnica
    lineas.append("=" * 60)
    lineas.append("REVISION TECNICA ADMINISTRADOR ZABBIX")
    lineas.append("=" * 60)
    for revision in resumen.get("revision_admin_zabbix", []):
        lineas.append(f"- {revision}")
    lineas.append("")
    # Seguimiento gerencial
    lineas.append("=" * 60)
    lineas.append("SEGUIMIENTO GERENCIAL")
    lineas.append("=" * 60)
    for seguimiento in resumen.get("seguimiento_gerencial", []):
        lineas.append(f"- {seguimiento}")
    lineas.append("")
    # Pie
    lineas.append("-" * 60)
    lineas.append(f"Generado por Zabbix AI Assistant | {fecha}")
    lineas.append("")
    return "\n".join(lineas)


def mostrar_cuerpo_correo_noc():
    """
    Genera el resumen diario y muestra el cuerpo del correo NOC en pantalla.
    No envia el correo.
    """
    print("\nGenerando resumen diario...")
    resumen = construir_resumen_diario_zabbix()
    cuerpo = generar_cuerpo_correo_noc(resumen)
    print("\n" + "=" * 60)
    print("VISTA PREVIA DEL CORREO NOC")
    print("=" * 60)
    print()
    print(cuerpo)
    input("Presiona Enter para volver al menu...")


def main():
    while True:
        print("\nZabbix Assistant")
        print("-" * 50)
        print("1. List hosts")
        print("2. Search host by name")
        print("3. Show host details by hostid")
        print("4. Show host items by hostid")
        print("5. Show host diagnostic report by hostid")
        print("6. Save host diagnostic report to Markdown")
        print("7. Search host groups")
        print("8. Show host group health summary")
        print("9. Smart search hosts by name, IP, DNS, group or hostid")
        print("10. Search host and run diagnostic")
        print("11. Search host and save diagnostic Markdown")
        print("12. Generar resumen diario de salud de Zabbix")
        print("13. Generar cuerpo de correo NOC (vista previa)")
        print("14. Reporte SRE (Golden Signals + MTTR + Aging)")
        print("15. Resumen ejecutivo (vista gerencia)")
        print("0. Exit")
        print("\nTip: inside any option, type 'b' to go back to the main menu.")
        option = input("\nChoose an option: ").strip()
        try:
            if not option:
                print("\nNo option selected. Please choose a valid menu option.")
                continue
            if option == "1":
                hosts = get_hosts()
                print_hosts(hosts)
            elif option == "2":
                search_text = ask_input(
                    "\nType host name or part of the name, or 'b' to go back: "
                )
                if search_text is None:
                    continue
                if not search_text:
                    print("\nSearch text cannot be empty.")
                    continue
                hosts = search_hosts(search_text)
                print_hosts(hosts)
            elif option == "3":
                hostid = ask_input("\nType hostid, or 'b' to go back: ")
                if hostid is None:
                    continue
                if not hostid:
                    print("\nHost ID cannot be empty.")
                    continue
                host = get_host_details(hostid)
                print_host_details(host)
            elif option == "4":
                hostid = ask_input("\nType hostid, or 'b' to go back: ")
                if hostid is None:
                    continue
                if not hostid:
                    print("\nHost ID cannot be empty.")
                    continue
                search_text = ask_input(
                    "\nFilter items by name or key. Press Enter to show first 100 items, or type 'b' to go back: "
                )
                if search_text is None:
                    continue
                if not search_text:
                    search_text = None
                items = get_host_items(hostid, search_text=search_text, limit=100)
                print_host_items(items)
            elif option == "5":
                hostid = ask_input("\nType hostid, or 'b' to go back: ")
                if hostid is None:
                    continue
                if not hostid:
                    print("\nHost ID cannot be empty.")
                    continue
                print_host_diagnostic_report(hostid)
            elif option == "6":
                hostid = ask_input("\nType hostid, or 'b' to go back: ")
                if hostid is None:
                    continue
                if not hostid:
                    print("\nHost ID cannot be empty.")
                    continue
                save_host_diagnostic_report(hostid)
            elif option == "7":
                search_text = ask_input(
                    "\nType host group name or part of the name, or 'b' to go back: "
                )
                if search_text is None:
                    continue
                if not search_text:
                    print("\nSearch text cannot be empty.")
                    continue
                groups = smart_search_host_groups(search_text)
                if groups:
                    print_host_groups(groups)
                else:
                    print(f"\nNo host groups found for: {search_text}")
                    print("No similar visible groups were found for this API user.")
                    print("Try another word, or validate whether the API user can see the expected host groups.")
            elif option == "8":
                groupid = ask_input("\nType host groupid, or 'b' to go back: ")
                if groupid is None:
                    continue
                if not groupid:
                    print("\nHost group ID cannot be empty.")
                    continue
                print_host_group_health_summary(groupid)
            elif option == "9":
                search_text = ask_input(
                    "\nType host name, IP, DNS, group, hostid or part of it, or 'b' to go back: "
                )
                if search_text is None:
                    continue
                if not search_text:
                    print("\nSearch text cannot be empty.")
                    continue
                hosts = smart_search_hosts(search_text)
                print_smart_host_results(hosts)
            elif option == "10":
                hostid = search_host_and_select_hostid()
                if hostid is None:
                    continue
                print_host_diagnostic_report(hostid)
            elif option == "11":
                hostid = search_host_and_select_hostid()
                if hostid is None:
                    continue
                save_host_diagnostic_report(hostid)
            elif option == "12":
                imprimir_resumen_diario_zabbix()
                input("\nPresiona Enter para volver al menu...")
            elif option == "13":
                mostrar_cuerpo_correo_noc()
            elif option == "14":
                print_sre_report()
                input("\nPresiona Enter para volver al menu...")
            elif option == "15":
                print_executive_summary()
                input("\nPresiona Enter para volver al menu...")
            elif option == "0":
                print("\nExiting...")
                break
            elif is_back_command(option):
                print("\nYou are already in the main menu.")
            else:
                print("\nInvalid option.")
        except Exception as error:
            print("\nAn error occurred while executing the option.")
            print(f"Details: {error}")


if __name__ == "__main__":
    main()
