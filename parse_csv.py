import csv
import sys
import os
from xml.etree import ElementTree as ET

if len(sys.argv) != 2:
    print("Użycie: python parse_csv.py <plik_xml>")
    sys.exit(1)

xml_file = sys.argv[1]
csv_file = os.path.splitext(xml_file)[0] + '.csv'

tree = ET.parse(xml_file)
root = tree.getroot()

# Zbieramy wszystkie możliwe kolumny dynamicznie
rows = []

for host in root.findall('host'):
    # --- Podstawowe info o hoście ---
    status = host.find('status')
    host_state = status.attrib.get('state', '') if status is not None else ''
    host_reason = status.attrib.get('reason', '') if status is not None else ''

    # Adresy (może być kilka: ipv4, ipv6, mac)
    ip, ipv6, mac, mac_vendor = '', '', '', ''
    for addr in host.findall('address'):
        atype = addr.attrib.get('addrtype', '')
        if atype == 'ipv4':
            ip = addr.attrib.get('addr', '')
        elif atype == 'ipv6':
            ipv6 = addr.attrib.get('addr', '')
        elif atype == 'mac':
            mac = addr.attrib.get('addr', '')
            mac_vendor = addr.attrib.get('vendor', '')

    # Hostname
    hostnames = host.find('hostnames')
    hostname = ''
    if hostnames is not None:
        hn = hostnames.find('hostname')
        if hn is not None:
            hostname = hn.attrib.get('name', '')

    # OS detection
    os_name, os_accuracy = '', ''
    os_elem = host.find('os')
    if os_elem is not None:
        osmatch = os_elem.find('osmatch')
        if osmatch is not None:
            os_name = osmatch.attrib.get('name', '')
            os_accuracy = osmatch.attrib.get('accuracy', '')

    # Uptime
    uptime_seconds, uptime_lastboot = '', ''
    uptime = host.find('uptime')
    if uptime is not None:
        uptime_seconds = uptime.attrib.get('seconds', '')
        uptime_lastboot = uptime.attrib.get('lastboot', '')

    # Distance (TTL hops)
    distance = ''
    dist_elem = host.find('distance')
    if dist_elem is not None:
        distance = dist_elem.attrib.get('value', '')

    # Porty
    ports = host.find('ports')
    if ports is not None:
        for port in ports.findall('port'):
            protocol = port.attrib.get('protocol', '')
            portid = port.attrib.get('portid', '')

            state_elem = port.find('state')
            port_state = state_elem.attrib.get('state', '') if state_elem is not None else ''
            port_reason = state_elem.attrib.get('reason', '') if state_elem is not None else ''

            svc = port.find('service')
            svc_name, svc_product, svc_version, svc_extrainfo, svc_tunnel, svc_method, svc_conf = '', '', '', '', '', '', ''
            if svc is not None:
                svc_name = svc.attrib.get('name', '')
                svc_product = svc.attrib.get('product', '')
                svc_version = svc.attrib.get('version', '')
                svc_extrainfo = svc.attrib.get('extrainfo', '')
                svc_tunnel = svc.attrib.get('tunnel', '')
                svc_method = svc.attrib.get('method', '')
                svc_conf = svc.attrib.get('conf', '')

            # Skrypty NSE na porcie
            scripts = {}
            for script in port.findall('script'):
                sid = script.attrib.get('id', '')
                sout = script.attrib.get('output', '')
                scripts[sid] = sout
            nse_output = ' | '.join(f"{k}: {v}" for k, v in scripts.items())

            # CPE
            cpe_list = [cpe.text for cpe in (svc.findall('cpe') if svc is not None else [])]
            cpe = ', '.join(filter(None, cpe_list))

            rows.append({
                'IP': ip,
                'IPv6': ipv6,
                'MAC': mac,
                'Producent MAC': mac_vendor,
                'Hostname': hostname,
                'Stan hosta': host_state,
                'Powód stanu hosta': host_reason,
                'Protokół': protocol,
                'Port': portid,
                'Stan portu': port_state,
                'Powód stanu portu': port_reason,
                'Usługa': svc_name,
                'Produkt': svc_product,
                'Wersja': svc_version,
                'Dodatkowe info': svc_extrainfo,
                'Tunel': svc_tunnel,
                'Metoda detekcji': svc_method,
                'Pewność detekcji': svc_conf,
                'CPE': cpe,
                'Skrypty NSE': nse_output,
                'OS': os_name,
                'Dokładność OS (%)': os_accuracy,
                'Uptime (s)': uptime_seconds,
                'Ostatni reboot': uptime_lastboot,
                'Odległość (hop)': distance,
            })
    else:
        # Host bez otwartych portów — zapisz samo info o hoście
        rows.append({
            'IP': ip,
            'IPv6': ipv6,
            'MAC': mac,
            'Producent MAC': mac_vendor,
            'Hostname': hostname,
            'Stan hosta': host_state,
            'Powód stanu hosta': host_reason,
            'Protokół': '',
            'Port': '',
            'Stan portu': '',
            'Powód stanu portu': '',
            'Usługa': '',
            'Produkt': '',
            'Wersja': '',
            'Dodatkowe info': '',
            'Tunel': '',
            'Metoda detekcji': '',
            'Pewność detekcji': '',
            'CPE': '',
            'Skrypty NSE': '',
            'OS': os_name,
            'Dokładność OS (%)': os_accuracy,
            'Uptime (s)': uptime_seconds,
            'Ostatni reboot': uptime_lastboot,
            'Odległość (hop)': distance,
        })

if not rows:
    print("Brak hostów w pliku XML.")
    sys.exit(0)

fieldnames = list(rows[0].keys())

with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"✔️ Zapisano CSV: {csv_file}  ({len(rows)} wierszy)")
