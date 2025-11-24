from flask import Flask, Response
from arvo_helper import get_arvo_html

app = Flask(__name__)

@app.route("/")
def home():
    return "<h2>Arvo Helper Running</h2><p>Go to /arvo</p>"

@app.route("/arvo")
def arvo():
    html = get_arvo_html()
    return Response(html, mimetype="text/html")