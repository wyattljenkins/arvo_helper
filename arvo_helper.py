import hashlib
import requests
from datetime import datetime, date
from collections import defaultdict

# ---------------------------
# LOGIN + DATA FETCH
# ---------------------------

def prism_login(username, password):
    login_url = "https://www.prism.horse/api/login"
    hashed_pw = hashlib.md5(password.encode()).hexdigest()

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Referer": "https://www.prism.horse/portal/login",
        "x-auth-username": username,
        "x-auth-password": hashed_pw,
        "x-auth-token": "null"
    }

    payload = {
        "platformType": 3,
        "platformVersion": "1.0",
        "deviceToken": "57ab57f07cd139d83913c9a97e61878e",
        "deviceId": "57ab57f07cd139d83913c9a97e61878e"
    }

    session = requests.Session()
    resp = session.post(login_url, headers=headers, json=payload)
    resp.raise_for_status()

    data = resp.json()
    token = data["responseData"]["token"]

    session.headers.update({
        "x-auth-token": token,
        "User-Agent": "Mozilla/5.0"
    })

    return session


def date_to_epoch_ms(dt: date):
    dt_midnight = datetime(dt.year, dt.month, dt.day)
    return int(dt_midnight.timestamp() * 1000)


def fetch_trackwork(session, dt: date):
    due_ms = date_to_epoch_ms(dt)
    trainer_id = 118508
    url = f"https://www.prism.horse/api/v2/trackwork/?dueDate={due_ms}&trainerIds={trainer_id}"
    r = session.get(url)
    r.raise_for_status()
    return r.json()


# ---------------------------
# PROCESSING / GROUPING
# ---------------------------

def group_by_barn(data):
    trot_key = "Trot Up PM"
    swim_key = "Swim 1 PM"

    resp = data.get("responseData", {})
    tasks = resp.get("tasks", [])

    barns = defaultdict(lambda: {trot_key: [], swim_key: []})

    for task in tasks:
        barn_obj = task.get("barn") or {}
        barn_name = task.get("barnName") or barn_obj.get("name") or "Unknown Barn"

        horse_name = (
            task.get("horseName")
            or task.get("horse", {}).get("name")
            or ""
        ).strip()
        if not horse_name:
            continue

        labels = []
        for ow in task.get("otherWorks") or []:
            label = (ow.get("label") or "").strip()
            if label:
                labels.append(label)

        ow_string = (task.get("otherWorksString") or "").strip()
        if ow_string:
            labels.append(ow_string)

        if trot_key in labels:
            barns[barn_name][trot_key].append(horse_name)

        if swim_key in labels:
            barns[barn_name][swim_key].append(horse_name)

    # Clean duplicates
    for barn in barns:
        for key in barns[barn]:
            barns[barn][key] = sorted(list(set(barns[barn][key])))

    return barns


# ---------------------------
# HTML RENDERING
# ---------------------------

def barns_to_html(barns):
    html = [
        "<html><head><meta charset='utf-8'>",
        "<title>Arvo Helper</title>",
        "<style>",
        "body { font-family: Arial; padding: 20px; }",
        "h1 { font-size: 24px; }",
        ".both { color: #d633ff; font-weight: bold; }",
        "h2 { margin-top: 20px; margin-bottom: 5px; }",
        "</style>",
        "</head><body>",
        "<h1>Arvo Tasks</h1>"
    ]

    trot_key = "Trot Up PM"
    swim_key = "Swim 1 PM"

    for barn in sorted(barns.keys()):
        trot = barns[barn][trot_key]
        swim = barns[barn][swim_key]

        if not trot and not swim:
            continue

        both = set(trot) & set(swim)

        html.append(f"<h2>{barn}</h2>")

        if trot:
            html.append(f"<strong>{trot_key}</strong><ul>")
            for h in trot:
                cls = "both" if h in both else ""
                html.append(f"<li class='{cls}'>{h}</li>")
            html.append("</ul>")

        if swim:
            html.append(f"<strong>{swim_key}</strong><ul>")
            for h in swim:
                cls = "both" if h in both else ""
                html.append(f"<li class='{cls}'>{h}</li>")
            html.append("</ul>")

    html.append("</body></html>")
    return "\n".join(html)

def get_box_order_html():
    # Re-use the same login + fetch as Arvo tasks
    username = "ben.gleeson"
    password = "ben8295"

    session = prism_login(username, password)
    today = datetime.now().date()

    data = fetch_trackwork(session, today)
    return box_order_to_html(data)


def get_arvo_html():
    username = "ben.gleeson"
    password = "ben8295"

    session = prism_login(username, password)
    today = datetime.now().date()

    data = fetch_trackwork(session, today)
    barns = group_by_barn(data)
    return barns_to_html(barns)


# ---------------------------
# BOX ORDER (MUCK OUT) HELPERS
# ---------------------------

def _parse_lot_number(group_name: str):
    """
    Extract the lot number from a groupName like 'Lot 1 4:45'.
    Returns an int or None if it can't be parsed.
    """
    if not group_name:
        return None
    parts = group_name.split()
    if len(parts) < 2:
        return None
    if parts[0].lower() != "lot":
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None
    
def box_order_to_html(data):
    """
    Build HTML for box order, grouped into:
      - Section 1: Barns A, B, C
      - Section 2: Barn D

    Output looks like a tick-list per lot, per section.
    """
    resp = data.get("responseData", {})
    tasks = resp.get("tasks", [])

    # sections['abc'][lot] -> [box numbers]
    # sections['d'][lot]   -> [box numbers]
    from collections import defaultdict

    sections = {
        "abc": defaultdict(list),
        "d": defaultdict(list),
    }

    all_lots = set()

    for task in tasks:
        barn_name = task.get("barnName") or (task.get("barn") or {}).get("name")
        group_name = task.get("groupName") or ""
        lot_no = _parse_lot_number(group_name)

        box_name = (
            task.get("boxName")
            or (task.get("boxInfo") or {}).get("name")
        )

        if not barn_name or lot_no is None or not box_name:
            continue

        # Normalise box as string, but we’ll sort numerically later
        box_str = str(box_name).strip()
        if not box_str:
            continue

        # Decide which section
        section_key = None
        if barn_name.startswith("Barn D"):
            section_key = "d"
        elif barn_name.startswith("Barn A") or barn_name.startswith("Barn B") or barn_name.startswith("Barn C"):
            section_key = "abc"

        if not section_key:
            # ignore other barns for now
            continue

        sections[section_key][lot_no].append(box_str)
        all_lots.add(lot_no)

    all_lots = sorted(all_lots)

    # Sort and dedupe each section's boxes
    for sec in sections.values():
        for lot, boxes in sec.items():
            # numeric sort if possible, fall back to string
            def sort_key(x):
                try:
                    return int(x)
                except ValueError:
                    return x
            unique = sorted(set(boxes), key=sort_key)
            sec[lot] = unique

    # Build HTML
    html = [
        "<!doctype html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>Box Order - Te Akau</title>",
        "<style>",
        "body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; background: #f5f5f5; }",
        "h1 { margin-bottom: 0.25rem; }",
        ".subtitle { color: #555; margin-bottom: 1.25rem; }",
        ".section { background: white; padding: 16px; border-radius: 8px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }",
        ".section h2 { margin-top: 0; margin-bottom: 0.75rem; }",
        "table { border-collapse: collapse; width: 100%; max-width: 500px; }",
        "th, td { padding: 6px 8px; border-bottom: 1px solid #eee; vertical-align: top; }",
        "th { text-align: left; font-weight: 600; }",
        ".lot-label { white-space: nowrap; }",
        ".boxes label { margin-right: 8px; display: inline-block; }",
        ".back-link { margin-bottom: 12px; display: inline-block; }",
        "</style>",
        "</head>",
        "<body>",
        "<a href='/' class='back-link'>&larr; Back to menu</a>",
        "<h1>Box Order</h1>",
        "<div class='subtitle'>Tick off boxes as you muck out, so no horse comes back to a dirty box.</div>",
    ]

    # Helper to render a section
    def render_section(title, section_key):
        html.append("<div class='section'>")
        html.append(f"<h2>{title}</h2>")
        html.append("<table>")
        html.append("<tr><th>Lot</th><th>Boxes</th></tr>")

        sec = sections[section_key]

        for lot in all_lots:
            boxes = sec.get(lot, [])
            html.append("<tr>")
            html.append(f"<td class='lot-label'>Lot {lot}</td>")
            if boxes:
                html.append("<td class='boxes'>")
                for b in boxes:
                    html.append(
                        f"<label><input type='checkbox'> {b}</label>"
                    )
                html.append("</td>")
            else:
                html.append("<td class='boxes'>–</td>")
            html.append("</tr>")

        html.append("</table>")
        html.append("</div>")

    render_section("Barns A, B, C", "abc")
    render_section("Barn D", "d")

    html.append("</body></html>")

    return "\n".join(html)

