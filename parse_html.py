import sys
import os
from xml.etree import ElementTree as ET
from html import escape

if len(sys.argv) != 2:
    print("Użycie: python parse_html.py <plik_xml>")
    sys.exit(1)

xml_file = sys.argv[1]
html_file = os.path.splitext(xml_file)[0] + '.html'

tree = ET.parse(xml_file)
root = tree.getroot()

# Metadane skanowania
scan_args = root.attrib.get('args', '')
scan_start = root.attrib.get('startstr', '')
scan_version = root.attrib.get('version', '')

runstats = root.find('runstats')
elapsed, hosts_up, hosts_down, hosts_total = '', '', '', ''
if runstats is not None:
    finished = runstats.find('finished')
    if finished is not None:
        elapsed = finished.attrib.get('elapsed', '')
    hosts_elem = runstats.find('hosts')
    if hosts_elem is not None:
        hosts_up = hosts_elem.attrib.get('up', '')
        hosts_down = hosts_elem.attrib.get('down', '')
        hosts_total = hosts_elem.attrib.get('total', '')

def td(val, bold=False):
    val = escape(str(val)) if val else '<span style="color:#aaa">—</span>'
    return f'<td><b>{val}</b></td>' if bold else f'<td>{val}</td>'

hosts_html = ''

for host in root.findall('host'):
    status = host.find('status')
    host_state = status.attrib.get('state', '') if status is not None else ''
    host_reason = status.attrib.get('reason', '') if status is not None else ''

    ip, ipv6, mac, mac_vendor = '', '', '', ''
    for addr in host.findall('address'):
        atype = addr.attrib.get('addrtype', '')
        if atype == 'ipv4':   ip = addr.attrib.get('addr', '')
        elif atype == 'ipv6': ipv6 = addr.attrib.get('addr', '')
        elif atype == 'mac':
            mac = addr.attrib.get('addr', '')
            mac_vendor = addr.attrib.get('vendor', '')

    hostnames = host.find('hostnames')
    hostname = ''
    if hostnames is not None:
        hn = hostnames.find('hostname')
        if hn is not None:
            hostname = hn.attrib.get('name', '')

    os_name, os_accuracy = '', ''
    os_elem = host.find('os')
    if os_elem is not None:
        osmatch = os_elem.find('osmatch')
        if osmatch is not None:
            os_name = osmatch.attrib.get('name', '')
            os_accuracy = osmatch.attrib.get('accuracy', '') + '%'

    uptime_seconds, uptime_lastboot = '', ''
    uptime = host.find('uptime')
    if uptime is not None:
        uptime_seconds = uptime.attrib.get('seconds', '') + 's'
        uptime_lastboot = uptime.attrib.get('lastboot', '')

    distance = ''
    dist_elem = host.find('distance')
    if dist_elem is not None:
        distance = dist_elem.attrib.get('value', '') + ' hop(s)'

    state_color = '#27ae60' if host_state == 'up' else '#e74c3c'
    display_ip = ip or ipv6 or 'nieznany'

    # Host scripts (globalne, nie per-port)
    hostscript_rows = ''
    hostscript = host.find('hostscript')
    if hostscript is not None:
        for script in hostscript.findall('script'):
            sid = escape(script.attrib.get('id', ''))
            sout = escape(script.attrib.get('output', ''))
            hostscript_rows += f'<tr><td colspan="9" style="background:#f0f4ff"><b>🔍 Skrypt hosta [{sid}]:</b> {sout}</td></tr>'

    # Porty
    port_rows = ''
    ports = host.find('ports')

    # Filtrowane porty (filtered/closed summary)
    if ports is not None:
        extraports = ports.find('extraports')
        if extraports is not None:
            ep_state = extraports.attrib.get('state', '')
            ep_count = extraports.attrib.get('count', '')
            port_rows += f'<tr><td colspan="9" style="color:#888;font-style:italic">ℹ️ {ep_count} portów w stanie: {ep_state}</td></tr>'

        for port in ports.findall('port'):
            protocol = port.attrib.get('protocol', '')
            portid = port.attrib.get('portid', '')

            state_elem = port.find('state')
            port_state = state_elem.attrib.get('state', '') if state_elem is not None else ''
            port_reason = state_elem.attrib.get('reason', '') if state_elem is not None else ''

            svc = port.find('service')
            svc_name, svc_product, svc_version, svc_extrainfo, svc_tunnel = '', '', '', '', ''
            cpe = ''
            if svc is not None:
                svc_name = svc.attrib.get('name', '')
                svc_product = svc.attrib.get('product', '')
                svc_version = svc.attrib.get('version', '')
                svc_extrainfo = svc.attrib.get('extrainfo', '')
                svc_tunnel = svc.attrib.get('tunnel', '')
                cpe_list = [c.text for c in svc.findall('cpe') if c.text]
                cpe = ', '.join(cpe_list)

            # Skrypty NSE per-port
            nse_parts = []
            for script in port.findall('script'):
                sid = escape(script.attrib.get('id', ''))
                sout = escape(script.attrib.get('output', ''))
                nse_parts.append(f'<b>{sid}</b>: {sout}')
            nse_html = '<br>'.join(nse_parts)

            ps_color = '#27ae60' if port_state == 'open' else ('#e67e22' if port_state == 'filtered' else '#7f8c8d')
            tunnel_badge = f' <span style="background:#8e44ad;color:#fff;padding:1px 5px;border-radius:3px;font-size:11px">{escape(svc_tunnel)}</span>' if svc_tunnel else ''

            full_version = ' '.join(filter(None, [svc_product, svc_version, f'({svc_extrainfo})' if svc_extrainfo else '']))

            port_rows += f'''<tr>
                <td><b>{escape(portid)}/{escape(protocol)}</b></td>
                <td><span style="color:{ps_color};font-weight:bold">{escape(port_state)}</span></td>
                <td>{escape(port_reason)}</td>
                <td>{escape(svc_name)}{tunnel_badge}</td>
                <td>{escape(full_version)}</td>
                <td style="font-size:11px;color:#555">{escape(cpe)}</td>
                <td colspan="3" style="font-size:11px">{nse_html}</td>
            </tr>'''

    hosts_html += f'''
    <div class="host-card">
        <div class="host-header">
            <span class="ip">{escape(display_ip)}</span>
            {'<span class="hostname">' + escape(hostname) + '</span>' if hostname else ''}
            <span class="badge" style="background:{state_color}">{escape(host_state)} ({escape(host_reason)})</span>
        </div>
        <div class="host-meta">
            {'<span>🖧 MAC: <b>' + escape(mac) + '</b>' + (' (' + escape(mac_vendor) + ')' if mac_vendor else '') + '</span>' if mac else ''}
            {'<span>💻 OS: <b>' + escape(os_name) + '</b> (' + escape(os_accuracy) + ')</span>' if os_name else ''}
            {'<span>⏱ Uptime: <b>' + escape(uptime_seconds) + '</b> (ostatni restart: ' + escape(uptime_lastboot) + ')</span>' if uptime_seconds else ''}
            {'<span>📡 Odległość: <b>' + escape(distance) + '</b></span>' if distance else ''}
            {'<span>🌐 IPv6: <b>' + escape(ipv6) + '</b></span>' if ipv6 else ''}
        </div>
        <table class="port-table">
            <thead>
                <tr>
                    <th>Port/Proto</th><th>Stan</th><th>Powód</th>
                    <th>Usługa</th><th>Wersja/Produkt</th><th>CPE</th><th colspan="3">Skrypty NSE</th>
                </tr>
            </thead>
            <tbody>
                {port_rows if port_rows else '<tr><td colspan="9" style="color:#aaa;text-align:center">Brak otwartych portów</td></tr>'}
                {hostscript_rows}
            </tbody>
        </table>
    </div>
'''

html = f'''<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<title>Raport Nmap – {escape(scan_start)}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "Segoe UI", Arial, sans-serif; background: #f0f2f5; color: #2c3e50; padding: 24px; }}
  h1 {{ font-size: 24px; margin-bottom: 4px; color: #1a252f; }}
  .meta {{ color: #666; font-size: 13px; margin-bottom: 20px; }}
  .meta span {{ margin-right: 20px; }}
  .summary-bar {{
    display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap;
  }}
  .summary-box {{
    background: #fff; border-radius: 8px; padding: 14px 22px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08); text-align: center; min-width: 120px;
  }}
  .summary-box .num {{ font-size: 28px; font-weight: 700; }}
  .summary-box .label {{ font-size: 12px; color: #888; margin-top: 2px; }}
  .host-card {{
    background: #fff; border-radius: 10px; margin-bottom: 20px;
    box-shadow: 0 1px 6px rgba(0,0,0,.09); overflow: hidden;
  }}
  .host-header {{
    background: #2c3e50; color: #fff; padding: 12px 18px;
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  }}
  .host-header .ip {{ font-size: 20px; font-weight: 700; font-family: monospace; }}
  .host-header .hostname {{ font-size: 13px; color: #aed6f1; }}
  .badge {{
    font-size: 11px; padding: 2px 8px; border-radius: 10px;
    color: #fff; font-weight: 600; margin-left: auto;
  }}
  .host-meta {{
    padding: 8px 18px; background: #f8f9fa; font-size: 13px;
    display: flex; gap: 20px; flex-wrap: wrap; border-bottom: 1px solid #eee;
  }}
  .host-meta span {{ color: #555; }}
  .port-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .port-table th {{
    background: #ecf0f1; padding: 8px 12px; text-align: left;
    font-weight: 600; border-bottom: 2px solid #ddd; white-space: nowrap;
  }}
  .port-table td {{ padding: 7px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
  .port-table tr:last-child td {{ border-bottom: none; }}
  .port-table tr:hover td {{ background: #fafbff; }}
  .cmd {{ font-family: monospace; background: #1e272e; color: #a8e063; padding: 10px 16px;
          border-radius: 6px; font-size: 12px; margin-bottom: 20px; word-break: break-all; }}
</style>
</head>
<body>
<h1>📡 Raport Nmap</h1>
<div class="meta">
  <span>🕐 {escape(scan_start)}</span>
  <span>🔧 Wersja Nmap: {escape(scan_version)}</span>
  {'<span>⏱ Czas skanowania: ' + escape(elapsed) + 's</span>' if elapsed else ''}
</div>
<div class="cmd">{escape(scan_args)}</div>
<div class="summary-bar">
  <div class="summary-box"><div class="num" style="color:#27ae60">{hosts_up}</div><div class="label">Hosty online</div></div>
  <div class="summary-box"><div class="num" style="color:#e74c3c">{hosts_down}</div><div class="label">Hosty offline</div></div>
  <div class="summary-box"><div class="num">{hosts_total}</div><div class="label">Łącznie</div></div>
</div>
{hosts_html}
</body>
</html>'''

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✔️ Zapisano HTML: {html_file}")
