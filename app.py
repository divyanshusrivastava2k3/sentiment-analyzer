"""Flask application: AI-Based Sentiment Analyzer."""
import io
from collections import Counter

import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, url_for

from config import Config
from sentiment import engine
from storage import store

app = Flask(__name__)
app.config.from_object(Config)

ALLOWED_EXTENSIONS = {"csv"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def summarize(rows: list) -> dict:
    counts = Counter(r["label"] for r in rows)
    total = max(len(rows), 1)
    avg_conf = sum(r["confidence"] for r in rows) / total
    return {
        "total": len(rows),
        "positive": counts.get("positive", 0),
        "negative": counts.get("negative", 0),
        "neutral": counts.get("neutral", 0),
        "avg_confidence": round(avg_conf, 4),
    }


@app.route("/", methods=["GET"])
def index():
    history = store.recent_analyses(limit=10)
    return render_template("index.html", history=history, mongo_ok=store.mongo_ok)


@app.route("/analyze", methods=["POST"])
def analyze():
    text = request.form.get("text", "").strip()
    if not text:
        return jsonify({"error": "Please enter some text to analyze."}), 400
    result = engine.analyze_batch([text])[0]
    rows = [{**result, "text": text}]
    summary = summarize(rows)
    doc = store.save_analysis(source="single-text", summary=summary, rows=rows)
    return jsonify({"summary": summary, "results": rows, "id": doc["_id"]})


@app.route("/analyze-bulk", methods=["POST"])
def analyze_bulk():
    texts = [ln.strip() for ln in request.form.get("texts", "").splitlines() if ln.strip()]
    if not texts:
        return jsonify({"error": "Paste at least one review line."}), 400
    if len(texts) > 500:
        return jsonify({"error": "Maximum 500 lines per batch."}), 400
    results = engine.analyze_batch(texts)
    rows = [{"text": t, **r} for t, r in zip(texts, results)]
    summary = summarize(rows)
    doc = store.save_analysis(source="bulk-paste", summary=summary, rows=rows)
    return jsonify({"summary": summary, "results": rows, "id": doc["_id"]})


@app.route("/analyze-csv", methods=["POST"])
def analyze_csv():
    file = request.files.get("file")
    column = request.form.get("column", "").strip()
    if not file or file.filename == "":
        return jsonify({"error": "Choose a CSV file first."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only .csv files are supported."}), 400
    try:
        df = pd.read_csv(io.StringIO(request.files["file"].stream.read().decode("utf-8-sig")))
    except Exception as exc:  # malformed CSV
        return jsonify({"error": f"Could not parse CSV: {exc}"}), 400
    if df.empty:
        return jsonify({"error": "CSV has no rows."}), 400
    col = column if column in df.columns else df.columns[0]
    texts = df[col].astype(str).str.strip().tolist()
    texts = [t for t in texts if t][:1000]
    if not texts:
        return jsonify({"error": "Selected column has no usable text."}), 400
    results = engine.analyze_batch(texts)
    rows = [{"text": t, **r} for t, r in zip(texts, results)]
    summary = summarize(rows)
    doc = store.save_analysis(source=f"csv:{file.filename}", summary=summary, rows=rows)
    return jsonify({"summary": summary, "results": rows, "column_used": col, "id": doc["_id"]})


@app.route("/history/<analysis_id>")
def history_detail(analysis_id):
    doc = store.get_analysis(analysis_id)
    if not doc:
        return redirect(url_for("index"))
    return render_template("report.html", doc=doc)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
