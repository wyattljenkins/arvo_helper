import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, date
from zoneinfo import ZoneInfo

import requests

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
        "x-auth-token": "null",
    }

    payload = {
        "platformType": 3,
        "platformVersion": "1.0",
        "deviceToken": "57ab57f07cd139d83913c9a97e61878e",
        "deviceId": "57ab57f07cd139d83913c9a97e61878e",
    }

    session = requests.Session()
    resp = session.post(login_url, headers=headers, json=payload)
    resp.raise_for_status()

    data = resp.json()
    token = data["responseData"]["token"]

    session.headers.update(
        {
            "x-auth-token": token,
            "User-Agent": "Mozilla/5.0",
        }
    )

    return session


MEL_TZ = ZoneInfo("Australia/Melbourne")


def date_to_epoch_ms(dt: date) -> int:
    """Interpret dt as midnight in Melbourne time, no matter where the server is."""
    dt_midnight = datetime(dt.year, dt.month, dt.day, tzinfo=MEL_TZ)
    return int(dt_midnight.timestamp() * 1000)


def fetch_trackwork(session, dt: date):
    due_ms = date_to_epoch_ms(dt)
    trainer_id = 118508
    url = f"https://www.prism.horse/api/v2/trackwork/?dueDate={due_ms}&trainerIds={trainer_id}"
    r = session.get(url)
    r.raise_for_status()
    return r.json()


# ---------------------------
# ARVO TASKS
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


def barns_to_html(barns):
    trot_key = "Trot Up PM"
    swim_key = "Swim 1 PM"

    html = [
        "<!doctype html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>Afternoon Tasks - Te Akau</title>",
        "<style>",
        ":root {",
        "  --ta-tangerine: #f58220;",
        "  --ta-tangerine-dark: #e06f10;",
        "  --ta-navy: #002a4d;",
        "  --ta-bg: #f5f5f5;",
        "  --ta-text: #222222;",
        "}",
        "* { box-sizing: border-box; }",
        "body {",
        "  margin: 0;",
        "  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;",
        "  color: var(--ta-text);",
        "  background: linear-gradient(180deg, var(--ta-navy) 0, var(--ta-navy) 220px, var(--ta-bg) 220px);",
        "}",
        ".shell { max-width: 960px; margin: 0 auto; padding: 24px 20px 40px; }",
        ".top-bar { display: flex; align-items: center; justify-content: space-between; color: #fff; }",
        ".brand-mark { font-size: 13px; letter-spacing: 0.18em; text-transform: uppercase; opacity: 0.9; }",
        ".top-bar-title { font-size: 26px; font-weight: 700; margin: 6px 0 0; }",
        ".card {",
        "  background: #ffffff;",
        "  border-radius: 18px;",
        "  padding: 22px 22px 26px;",
        "  margin-top: 28px;",
        "  box-shadow: 0 18px 36px rgba(0,0,0,0.12);",
        "}",
        ".back-link {",
        "  display: inline-flex;",
        "  align-items: center;",
        "  gap: 6px;",
        "  text-decoration: none;",
        "  font-size: 13px;",
        "  color: var(--ta-navy);",
        "  margin-bottom: 8px;",
        "}",
        ".back-link span { font-size: 16px; }",
        ".page-title { margin: 4px 0 2px; font-size: 22px; color: var(--ta-navy); }",
        ".subtitle { font-size: 14px; color: #555; margin-bottom: 16px; }",
        ".divider { width: 60px; height: 3px; background: var(--ta-tangerine); border-radius: 999px; margin-bottom: 18px; }",
        "h2 { margin: 18px 0 4px; font-size: 18px; color: var(--ta-navy); }",
        "strong { color: var(--ta-navy); }",
        "ul { margin: 4px 0 10px 18px; padding: 0; }",
        "li { margin: 2px 0; }",
        "li.both { color: var(--ta-tangerine-dark); font-weight: 600; }",
        ".legend { font-size: 12px; color: #777; margin-bottom: 10px; }",
        "@media (max-width: 600px) {",
        "  .card { padding: 18px 16px 22px; }",
        "  .top-bar-title { font-size: 22px; }",
        "}",
        "</style>",
        "</head>",
        "<body>",
        "<div class='shell'>",
        "  <header class='top-bar'>",
        "    <div>",
        "      <div class='brand-mark'>Te Akau Racing · Cranbourne</div>",
        "      <div class='top-bar-title'>Afternoon Tasks</div>",
        "    </div>",
        "  </header>",
        "  <main class='card'>",
        "    <a href='/' class='back-link'><span>&larr;</span> Back to menu</a>",
        "    <h1 class='page-title'>Horses to Trot Up &amp; Swim</h1>",
        "    <p class='subtitle'>Auto-generated from today&#39;s Prism schedule for Mark Walker.</p>",
        "    <div class='divider'></div>",
        "    <div class='legend'><strong>Note:</strong> names shown in tangerine appear in both "
        + trot_key
        + " and "
        + swim_key
        + ".</div>",
    ]

    for barn in sorted(barns.keys()):
        trot = barns[barn][trot_key]
        swim = barns[barn][swim_key]

        if not trot and not swim:
            continue

        both = set(trot) & set(swim)

        html.append(f"<h2>{barn}</h2>")

        if trot:
            html.append(f"<strong>{trot_key}</strong>")
            html.append("<ul>")
            for h in trot:
                cls = "both" if h in both else ""
                html.append(f"<li class='{cls}'>{h}</li>")
            html.append("</ul>")

        if swim:
            html.append(f"<strong>{swim_key}</strong>")
            html.append("<ul>")
            for h in swim:
                cls = "both" if h in both else ""
                html.append(f"<li class='{cls}'>{h}</li>")
            html.append("</ul>")

    html.append("  </main>")
    html.append("</div>")
    html.append("</body></html>")
    return "\n".join(html)


def get_arvo_html():
    username = os.environ["PRISM_USER"]
    password = os.environ["PRISM_PASS"]

    today = datetime.now(MEL_TZ).date()

    session = prism_login(username, password)
    data = fetch_trackwork(session, today)
    barns = group_by_barn(data)
    return barns_to_html(barns)


# ---------------------------
# BOX ORDER (MUCK OUT)
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


def box_order_to_html(data, day_date: date) -> str:
    """
    Build HTML for box order, grouped into:
      - Section 1: Barns A, B, C (lots + treadmills)
      - Section 2: Barn D (lots + treadmills)

    Treadmills:
      - Detected via 'treadmill' in groupName (case-insensitive).
      - Box order is preserved in Prism order per section.
      - Rendered to the right of the Lots table.
    """
    resp = data.get("responseData", {})
    tasks = resp.get("tasks", [])

    # Lots by section
    sections: dict[str, dict[str, list[str]]] = {
        "abc": defaultdict(list),
        "d": defaultdict(list),
    }

    # Treadmills by section (preserve order)
    treadmill_sections: dict[str, list[str]] = {
        "abc": [],
        "d": [],
    }

    stats = {
        "total_tasks": len(tasks),
        "with_lot": 0,
        "with_box": 0,
        "abc_entries": 0,
        "d_entries": 0,
    }

    all_lots = set()

    # --- Pass 1: build mapping from parent task id -> 'Lot X' label ---
    lot_id_to_label: dict[int, str] = {}

    for t in tasks:
        group_name = (t.get("groupName") or "").strip()
        lot_num = _parse_lot_number(group_name)
        if lot_num is not None:
            lot_id_to_label[t.get("id")] = f"Lot {lot_num}"

    # --- Pass 2: assign each task to a lot or treadmill ---
    for task in tasks:
        barn_name = task.get("barnName") or (task.get("barn") or {}).get("name")
        group_name = (task.get("groupName") or "").strip()
        group_lower = group_name.lower()

        # Determine section (ABC vs D)
        section_key: str | None = None
        if barn_name:
            if barn_name.startswith("Barn D"):
                section_key = "d"
            elif (
                barn_name.startswith("Barn A")
                or barn_name.startswith("Barn B")
                or barn_name.startswith("Barn C")
            ):
                section_key = "abc"

        # Box name (if any)
        box_name = task.get("boxName") or (task.get("boxInfo") or {}).get("name")
        box_str = str(box_name).strip() if box_name else ""

        # --- Treadmills: capture and preserve order, then skip lot logic ---
        if "treadmill" in group_lower:
            if section_key and box_str:
                treadmill_sections[section_key].append(box_str)
            # treadmills are not lots, so continue to next task
            continue

        # --- Lots: as before ---
        lot_label = None

        # Case 1: this task itself has 'Lot X 4:45'
        lot_num_direct = _parse_lot_number(group_name)
        if lot_num_direct is not None:
            lot_label = f"Lot {lot_num_direct}"
        else:
            # Case 2: groupName is numeric -> lookup parent lot by id
            if group_name.isdigit():
                parent_id = int(group_name)
                lot_label = lot_id_to_label.get(parent_id)

        if not lot_label:
            # Not a lot or treadmill
            continue

        stats["with_lot"] += 1

        if not box_str:
            continue

        stats["with_box"] += 1

        if section_key == "abc":
            stats["abc_entries"] += 1
        elif section_key == "d":
            stats["d_entries"] += 1

        if not section_key:
            continue

        sections[section_key][lot_label].append(box_str)
        all_lots.add(lot_label)

    # --- Sort & dedupe boxes, and sort lots numerically ---

    def sort_key_box(x: str):
        try:
            return int(x)
        except ValueError:
            return x

    for sec in sections.values():
        for lot, boxes in sec.items():
            unique = sorted(set(boxes), key=sort_key_box)
            sec[lot] = unique

    def lot_sort_value(label: str) -> int:
        parts = label.split()
        if len(parts) >= 2:
            try:
                return int(parts[1])
            except ValueError:
                pass
        return 9999

    sorted_lots = sorted(all_lots, key=lot_sort_value)

    date_str = day_date.isoformat()

    html = [
        "<!doctype html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>Box Order - Te Akau</title>",
        "<style>",
        ":root {",
        "  --ta-tangerine: #f58220;",
        "  --ta-tangerine-dark: #e06f10;",
        "  --ta-navy: #002a4d;",
        "  --ta-bg: #f5f5f5;",
        "  --ta-text: #222222;",
        "}",
        "* { box-sizing: border-box; }",
        "body {",
        "  margin: 0;",
        "  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;",
        "  color: var(--ta-text);",
        "  background: linear-gradient(180deg, var(--ta-navy) 0, var(--ta-navy) 220px, var(--ta-bg) 220px);",
        "}",
        ".shell { max-width: 960px; margin: 0 auto; padding: 24px 20px 40px; }",
        ".top-bar { display: flex; align-items: center; justify-content: space-between; color: #fff; }",
        ".brand-mark { font-size: 13px; letter-spacing: 0.18em; text-transform: uppercase; opacity: 0.9; }",
        ".top-bar-title { font-size: 26px; font-weight: 700; margin: 6px 0 0; }",
        ".card {",
        "  background: #ffffff;",
        "  border-radius: 18px;",
        "  padding: 22px 22px 26px;",
        "  margin-top: 28px;",
        "  box-shadow: 0 18px 36px rgba(0,0,0,0.12);",
        "}",
        ".back-link {",
        "  display: inline-flex;",
        "  align-items: center;",
        "  gap: 6px;",
        "  text-decoration: none;",
        "  font-size: 13px;",
        "  color: var(--ta-navy);",
        "  margin-bottom: 8px;",
        "}",
        ".back-link span { font-size: 16px; }",
        ".page-title { margin: 4px 0 2px; font-size: 22px; color: var(--ta-navy); }",
        ".subtitle { font-size: 14px; color: #555; margin-bottom: 10px; }",
        ".debug { font-size: 11px; color: #999; margin-bottom: 16px; }",
        ".section {",
        "  margin-top: 18px;",
        "  padding-top: 4px;",
        "}",
        ".section h2 { font-size: 18px; color: var(--ta-navy); margin: 0 0 8px; }",
        ".section-grid {",
        "  display: grid;",
        "  grid-template-columns: minmax(0, 1.7fr) minmax(0, 1.2fr);",
        "  gap: 16px;",
        "  align-items: flex-start;",
        "}",
        ".panel {",
        "  background: #fff;",
        "  border-radius: 12px;",
        "  padding: 10px 10px 12px;",
        "  box-shadow: 0 1px 3px rgba(0,0,0,0.06);",
        "}",
        ".panel-title {",
        "  font-size: 14px;",
        "  font-weight: 600;",
        "  color: var(--ta-navy);",
        "  margin: 0 0 6px;",
        "}",
        "table {",
        "  border-collapse: collapse;",
        "  width: 100%;",
        "  background: #fff;",
        "}",
        "th, td {",
        "  padding: 6px 8px;",
        "  border-bottom: 1px solid #eee;",
        "  vertical-align: top;",
        "  font-size: 13px;",
        "}",
        "th { text-align: left; font-weight: 600; color: var(--ta-navy); }",
        ".lot-label { white-space: nowrap; font-weight: 600; }",
        ".boxes label {",
        "  margin-right: 8px;",
        "  display: inline-flex;",
        "  align-items: center;",
        "  gap: 3px;",
        "  padding: 2px 0;",
        "}",
        ".boxes input[type='checkbox'] {",
        "  accent-color: var(--ta-tangerine);",
        "}",
        "@media (max-width: 700px) {",
        "  .card { padding: 18px 16px 22px; }",
        "  .top-bar-title { font-size: 22px; }",
        "  .section-grid { grid-template-columns: minmax(0, 1fr); }",
        "}",
        "</style>",
        "</head>",
        f"<body data-date='{date_str}'>",
        "<div class='shell'>",
        "  <header class='top-bar'>",
        "    <div>",
        "      <div class='brand-mark'>Te Akau Racing · Cranbourne</div>",
        "      <div class='top-bar-title'>Box Order</div>",
        "    </div>",
        "  </header>",
        "  <main class='card'>",
        "    <a href='/' class='back-link'><span>&larr;</span> Back to menu</a>",
        "    <h1 class='page-title'>Muck Out Checklist</h1>",
        "    <p class='subtitle'>Tick off boxes as you muck out, so no horse comes back to a dirty box.</p>",
        f"    <div class='debug'>Debug: total tasks={stats['total_tasks']}, "
        f"with lot={stats['with_lot']}, with box={stats['with_box']}, "
        f"ABC entries={stats['abc_entries']}, D entries={stats['d_entries']}</div>",
    ]

    def render_section(title: str, section_key: str):
        html.append(f"    <section class='section'>")
        html.append(f"      <h2>{title}</h2>")
        html.append("      <div class='section-grid'>")

        # LEFT PANEL: LOTS
        html.append("        <div class='panel'>")
        html.append("          <div class='panel-title'>Lots</div>")
        html.append("          <table>")
        html.append("            <tr><th>Lot</th><th>Boxes</th></tr>")

        sec = sections[section_key]

        for lot_label in sorted_lots:
            boxes = sec.get(lot_label, [])
            html.append("            <tr>")
            html.append(f"              <td class='lot-label'>{lot_label}</td>")
            if boxes:
                html.append("              <td class='boxes'>")
                for b in boxes:
                    key = f"{section_key}|{lot_label}|{b}"
                    html.append(
                        f"                <label><input type='checkbox' class='box-check' "
                        f"data-key='{key}'> {b}</label>"
                    )
                html.append("              </td>")
            else:
                html.append("              <td class='boxes'>–</td>")
            html.append("            </tr>")

        html.append("          </table>")
        html.append("        </div>")  # end left panel

        # RIGHT PANEL: TREADMILLS (if any)
        tread_boxes = treadmill_sections[section_key]
        if tread_boxes:
            html.append("        <div class='panel'>")
            html.append("          <div class='panel-title'>Treadmills</div>")
            html.append("          <table>")
            html.append("            <tr><th>Type</th><th>Boxes</th></tr>")
            html.append("            <tr>")
            html.append("              <td class='lot-label'>Treadmill</td>")
            html.append("              <td class='boxes'>")
            for b in tread_boxes:
                key = f"{section_key}|Treadmill|{b}"
                html.append(
                    f"                <label><input type='checkbox' class='box-check' "
                    f"data-key='{key}'> {b}</label>"
                )
            html.append("              </td>")
            html.append("            </tr>")
            html.append("          </table>")
            html.append("        </div>")
        else:
            # If no treadmills, still output an empty panel for visual balance
            html.append("        <div class='panel'>")
            html.append("          <div class='panel-title'>Treadmills</div>")
            html.append("          <p style='font-size: 12px; color: #888; margin: 4px 0 0;'>No treadmills today.</p>")
            html.append("        </div>")

        html.append("      </div>")  # section-grid
        html.append("    </section>")

    render_section("Barns A, B, C", "abc")
    render_section("Barn D", "d")

    # Real-time checkbox sync (unchanged, now also covers treadmills)
    html.append(
        """
    <script>
    (function() {
      const body = document.body;
      const date = body.getAttribute('data-date');
      const checkboxes = Array.from(document.querySelectorAll('.box-check'));

      function applyState(state) {
        checkboxes.forEach(cb => {
          const key = cb.dataset.key;
          if (Object.prototype.hasOwnProperty.call(state, key)) {
            cb.checked = !!state[key];
          }
        });
      }

      function fetchState() {
        fetch(`/api/boxes/state?date=${encodeURIComponent(date)}`)
          .then(r => r.json())
          .then(applyState)
          .catch(console.error);
      }

      // Initial load
      fetchState();

      // When user changes a checkbox, send update
      checkboxes.forEach(cb => {
        cb.addEventListener('change', () => {
          const payload = {
            date: date,
            key: cb.dataset.key,
            checked: cb.checked
          };
          fetch('/api/boxes/state', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          }).catch(console.error);
        });
      });

      // Poll every 5 seconds to pick up others' changes
      setInterval(fetchState, 5000);
    })();
    </script>
    """
    )

    html.append("  </main>")
    html.append("</div>")
    html.append("</body></html>")

    return "\n".join(html)


def get_box_order_html():
    username = os.environ["PRISM_USER"]
    password = os.environ["PRISM_PASS"]

    today = datetime.now(MEL_TZ).date()

    session = prism_login(username, password)
    data = fetch_trackwork(session, today)
    return box_order_to_html(data, today)
