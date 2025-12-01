from flask import Flask, Response, jsonify, request
from arvo_helper import get_arvo_html, get_box_order_html

app = Flask(__name__)

# In-memory store for checkbox state:
# { "YYYY-MM-DD": { "section|Lot X|box": true/false, ... } }
BOX_STATE: dict[str, dict[str, bool]] = {}


@app.route("/")
def home():
    # Landing page with Te Akau-inspired styling
    return """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Te Akau Stable Helper</title>
      <style>
        :root {
          --ta-tangerine: #f58220;
          --ta-tangerine-dark: #e06f10;
          --ta-navy: #002a4d;
          --ta-bg: #f5f5f5;
          --ta-text: #222222;
        }

        * {
          box-sizing: border-box;
        }

        body {
          margin: 0;
          font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          color: var(--ta-text);
          background: linear-gradient(
            180deg,
            var(--ta-navy) 0,
            var(--ta-navy) 230px,
            var(--ta-bg) 230px
          );
        }

        .shell {
          max-width: 960px;
          margin: 0 auto;
          padding: 24px 20px 40px;
        }

        .top-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          color: #ffffff;
        }

        .brand-mark {
          font-size: 13px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          opacity: 0.9;
        }

        .top-bar-title {
          font-size: 28px;
          font-weight: 700;
          margin: 6px 0 0;
        }

        .hero-card {
          background: #ffffff;
          border-radius: 18px;
          padding: 24px 24px 28px;
          margin-top: 32px;
          box-shadow: 0 18px 36px rgba(0, 0, 0, 0.12);
        }

        .hero-heading {
          font-size: 22px;
          font-weight: 700;
          color: var(--ta-navy);
          margin: 0 0 4px;
        }

        .hero-subtitle {
          font-size: 14px;
          color: #555;
          margin: 0 0 20px;
        }

        .divider {
          width: 60px;
          height: 3px;
          border-radius: 999px;
          background: var(--ta-tangerine);
          margin-bottom: 18px;
        }

        .btn-container {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin-top: 4px;
        }

        a.btn {
          display: inline-block;
          padding: 10px 16px;
          border-radius: 50px;
          text-decoration: none;
          font-size: 14px;
          font-weight: 600;
          border: 1px solid transparent;
          transition: background 0.16s ease, color 0.16s ease, transform 0.08s ease;
          cursor: pointer;
        }

        a.btn-primary {
          background: var(--ta-tangerine);
          color: #ffffff;
        }
        a.btn-primary:hover {
          background: var(--ta-tangerine-dark);
          transform: translateY(-1px);
        }

        a.btn-secondary {
          background: #ffffff;
          color: var(--ta-navy);
          border-color: rgba(0,0,0,0.08);
        }
        a.btn-secondary:hover {
          background: #f3f3f3;
          transform: translateY(-1px);
        }

        .footer-note {
          margin-top: 22px;
          font-size: 12px;
          color: #777;
        }

        @media (max-width: 600px) {
          .hero-card {
            padding: 18px 16px 22px;
          }
          .top-bar-title {
            font-size: 22px;
          }
        }
      </style>
    </head>
    <body>
      <div class="shell">
        <header class="top-bar">
          <div>
            <div class="brand-mark">Te Akau Racing · Cranbourne</div>
            <div class="top-bar-title">Stable Helper</div>
          </div>
        </header>

        <main class="hero-card">
          <h1 class="hero-heading">Morning & Afternoon Tools</h1>
          <p class="hero-subtitle">
            Quick views to keep the tangerine team humming – built around today’s Prism schedule.
          </p>
          <div class="divider"></div>

          <div class="btn-container">
            <a href="/arvo" class="btn btn-primary">Arvo Tasks</a>
            <a href="/boxes" class="btn btn-secondary">Box Order (Muck Out)</a>
          </div>

          <div class="footer-note">
            Powered by your Prism login · Updates with each new day’s schedule.
          </div>
        </main>
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
