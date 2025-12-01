from flask import Flask, Response, jsonify, request
from arvo_helper import get_arvo_html, get_box_order_html

app = Flask(__name__)

# In-memory store for checkbox state:
# { "YYYY-MM-DD": { "section|Lot X|box": true/false, ... } }
BOX_STATE: dict[str, dict[str, bool]] = {}


@app.route("/")
def home():
    # Simple landing page with buttons
    return """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Te Akau Helper</title>
      <style>
        body {
          font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          padding: 20px;
          background: #f5f5f5;
        }
        h1 { margin-bottom: 0.5rem; }
        .subtitle { color: #555; margin-bottom: 1.5rem; }
        .btn-container { display: flex; flex-direction: column; gap: 0.75rem; max-width: 260px; }
        a.btn {
          display: inline-block;
          padding: 10px 14px;
          border-radius: 6px;
          text-decoration: none;
          background: #ff7a00;
          color: white;
          font-weight: 600;
          text-align: center;
        }
        a.btn.secondary {
          background: #0066cc;
        }
      </style>
    </head>
    <body>
      <h1>Te Akau Stable Helper</h1>
      <div class="subtitle">Choose a tool:</div>
      <div class="btn-container">
        <a href="/arvo" class="btn">Arvo Tasks</a>
        <a href="/boxes" class="btn secondary">Box Order (Muck Out)</a>
      </div>
    </body>
    </html>
    """


@app.route("/arvo")
def arvo():
    html = get_arvo_html()
    return Response(html, mimetype="text/html")


@app.route("/boxes")
def boxes():
    html = get_box_order_html()
    return Response(html, mimetype="text/html")


# ---- Real-time box state API ----

@app.route("/api/boxes/state", methods=["GET"])
def get_boxes_state():
    """Return checkbox state for a given date (YYYY-MM-DD)."""
    date = request.args.get("date")
    if not date:
        return jsonify({})
    return jsonify(BOX_STATE.get(date, {}))


@app.route("/api/boxes/state", methods=["POST"])
def update_boxes_state():
    """Update checkbox state for a given date + key."""
    payload = request.get_json(force=True) or {}
    date = payload.get("date")
    key = payload.get("key")
    checked = bool(payload.get("checked"))

    if not date or not key:
        return jsonify({"ok": False, "error": "missing date or key"}), 400

    BOX_STATE.setdefault(date, {})[key] = checked
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)
