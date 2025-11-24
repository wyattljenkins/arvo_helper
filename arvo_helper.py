import hashlib
import os
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


def get_arvo_html():
    username = os.environ["PRISM_USER"]
    password = os.environ["PRISM_PASS"]

    session = prism_login(username, password)
    today = datetime.now().date()

    data = fetch_trackwork(session, today)
    barns = group_by_barn(data)
    return barns_to_html(barns)


