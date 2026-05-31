from datetime import datetime
from pathlib import Path

from zabbix.client import (
    get_hosts,
    search_hosts,
    get_host_details,
    get_host_items,
    get_host_item_summary,
    get_host_problems
)


BACK_COMMANDS = ["b", "back", "atras", "atrás"]


def is_back_command(value):
    """
    Verifica si el usuario quiere volver al menú principal.
    """
    return value.strip().lower() in BACK_COMMANDS


def ask_input(prompt):
    """
    Pide datos al usuario.
    Si el usuario escribe b, back, atras o atrás, vuelve al menú principal.
    """
    value = input(prompt).strip()

    if is_back_command(value):
        return None

    return value


def format_status(status):
    """
    En Zabbix:
    0 = Enabled
    1 = Disabled
    """
    if str(status) == "0":
        return "Enabled"
    elif str(status) == "1":
        return "Disabled"
    return "Unknown"


def format_item_state(state):
    """
    En Zabbix:
    0 = Normal
    1 = Unsupported
    """
    if str(state) == "0":
        return "Normal"
    elif str(state) == "1":
        return "Unsupported"
    return "Unknown"


def format_problem_severity(severity):
    """
    Severidades de Zabbix:
    0 = Not classified
    1 = Information
    2 = Warning
    3 = Average
    4 = High
    5 = Disaster
    """
    mapping = {
        "0": "Not classified",
        "1": "Information",
        "2": "Warning",
        "3": "Average",
        "4": "High",
        "5": "Disaster"
    }

    return mapping.get(str(severity), "Unknown")


def format_lastclock(lastclock):
    """
    Convierte el timestamp de Zabbix a una fecha legible.
    """
    if not lastclock or str(lastclock) == "0":
        return "No data"

    try:
        return datetime.fromtimestamp(int(lastclock)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "Invalid date"


def print_hosts(hosts):
    if not hosts:
        print("\nNo hosts found.")
        return

    print(f"\nTotal hosts shown: {len(hosts)}\n")

    for host in hosts:
        hostid = host.get("hostid", "")
        name = host.get("name") or host.get("host", "")
        status = format_status(host.get("status"))

        print(f"{hostid} | {name} | {status}")


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

    print("\nGroups:")
    groups = host.get("groups", [])
    if groups:
        for group in groups:
            print(f"- {group.get('name')}")
    else:
        print("- No groups found")

    print("\nInterfaces:")
    interfaces = host.get("interfaces", [])
    if interfaces:
        for interface in interfaces:
            interface_type = interface.get("type")
            ip = interface.get("ip")
            dns = interface.get("dns")
            port = interface.get("port")
            main = interface.get("main")

            print(
                f"- Type: {interface_type} | "
                f"IP: {ip} | "
                f"DNS: {dns} | "
                f"Port: {port} | "
                f"Main: {main}"
            )
    else:
        print("- No interfaces found")

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
            "type",
            "name",
            "alias",
            "os",
            "serialno_a",
            "model",
            "vendor",
            "location",
            "site_address_a"
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
    """
    Genera una evaluación simple del host.
    Esta es la primera capa de análisis accionable.
    """
    findings = []
    actions = []
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
        actions.append(
            "Validate whether the host should remain disabled or be removed from operational monitoring."
        )
        priority = "Low"

    if not interfaces:
        findings.append("The host has no configured interfaces.")
        actions.append(
            "Review the host configuration and add the required Agent, SNMP, JMX or IPMI interface."
        )
        priority = "High"

    if not templates:
        findings.append("The host has no templates assigned.")
        actions.append(
            "Assign the appropriate monitoring template according to the device or system type."
        )
        priority = "High"

    if not tags:
        findings.append("The host has no tags configured.")
        actions.append(
            "Add business and operational tags such as system, owner, location and criticality."
        )
        if priority == "Low":
            priority = "Medium"

    if item_summary["total"] == 0:
        findings.append("The host has no monitoring items.")
        actions.append("Review template assignment or item creation.")
        priority = "High"

    if item_summary["unsupported"] > 0:
        findings.append(f"The host has {item_summary['unsupported']} unsupported items.")
        actions.append(
            "Review unsupported items, item keys, SNMP OIDs, macros, permissions or template compatibility."
        )
        if priority != "High":
            priority = "Medium"

    if item_summary["without_data"] > 0:
        findings.append(f"The host has {item_summary['without_data']} items without data.")
        actions.append(
            "Validate agent/SNMP availability, item configuration and whether the device is reachable."
        )
        if priority != "High":
            priority = "Medium"

    if active_high_problems:
        findings.append(f"The host has {len(active_high_problems)} active High/Disaster problems.")
        actions.append(
            "Prioritize active High/Disaster problems and validate operational impact."
        )
        priority = "High"

    if problems and not active_high_problems:
        findings.append(f"The host has {len(problems)} active problems.")
        actions.append(
            "Review active problems and confirm whether they require operational action."
        )
        if priority == "Low":
            priority = "Medium"

    if not findings:
        assessment = "The host appears to be monitored correctly. No major monitoring gaps were detected."
        actions.append("No immediate action required. Continue regular monitoring.")
    else:
        assessment = "The host has monitoring findings that should be reviewed."

    return {
        "priority": priority,
        "assessment": assessment,
        "findings": findings,
        "actions": actions
    }


def build_host_diagnostic_data(hostid):
    """
    Construye los datos del diagnóstico de un host para usarlos en pantalla o reporte.
    """
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

    print("\nRecommended actions")
    print("-" * 70)

    for action in assessment["actions"]:
        print(f"- {action}")

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
    """
    Convierte el diagnóstico de un host en Markdown.
    """
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

    lines.append("## Recommended actions")
    lines.append("")

    for action in assessment["actions"]:
        lines.append(f"- {action}")

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
        "This report identifies monitoring gaps or active issues that may affect visibility, "
        "incident response and operational decision-making."
    )
    lines.append("")

    return "\n".join(lines)


def save_host_diagnostic_report(hostid):
    """
    Genera y guarda un reporte Markdown del diagnóstico de un host.
    """
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

    reports_dir = Path("output") / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"host_diagnostic_{safe_host_name}_{hostid}_{timestamp}.md"

    markdown_content = render_host_diagnostic_markdown(diagnostic_data)

    report_path.write_text(markdown_content, encoding="utf-8")

    print("\nReport generated successfully.")
    print(f"Path: {report_path}")


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
        print("0. Exit")
        print("\nTip: inside any option, type 'b' to go back to the main menu.")

        option = input("\nChoose an option: ").strip()

        try:
            if option == "1":
                hosts = get_hosts(limit=50)
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