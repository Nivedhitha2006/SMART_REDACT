"""
app.py — Smart Document Redaction Flask Application
Routes: GET / (home), POST /redact, GET /download/<filename>, GET /history
"""

import os
import uuid
import tempfile
from pathlib import Path
from flask import (
    Flask, render_template, request,
    send_file, jsonify
)
from redactor import redact_text
from database import init_db, log_session, get_recent_sessions
from file_parser import extract_text

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "redact-dev-secret-2026")

TEMP_DIR = Path(tempfile.gettempdir()) / "smart_redactor_outputs"
TEMP_DIR.mkdir(exist_ok=True)

init_db()

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".csv"}


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/redact", methods=["POST"])
def redact():
    source = "paste"
    raw_text = ""
    original_filename = "output"

    uploaded_file = request.files.get("file")
    if uploaded_file and uploaded_file.filename:
        filename = uploaded_file.filename

        if not allowed_file(filename):
            return jsonify({
                "error": (
                    f"Unsupported file type. "
                    "Accepted: .txt  .pdf  .docx  .pptx  .xlsx  .xls  .csv"
                )
            }), 400

        try:
            file_bytes = uploaded_file.read()
            raw_text = extract_text(file_bytes, filename)
            source = "upload"
            original_filename = Path(filename).stem
        except (ValueError, RuntimeError) as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Could not read file: {str(e)}"}), 400
    else:
        raw_text = request.form.get("text", "").strip()

    if not raw_text:
        return jsonify({
            "error": "No text provided. Paste text or upload a supported file."
        }), 400

    if len(raw_text) > 500_000:
        return jsonify({
            "error": "Input too large. Maximum 500,000 characters."
        }), 400

    all_types = {"NAME", "EMAIL", "PHONE", "AADHAAR", "PAN"}
    enabled_raw = request.form.getlist("entity_types")
    enabled_types = set(enabled_raw) if enabled_raw else all_types
    enabled_types = enabled_types & all_types

    try:
        result = redact_text(raw_text, enabled_types=enabled_types)
    except Exception as e:
        return jsonify({"error": f"Redaction failed: {str(e)}"}), 500

    token = uuid.uuid4().hex
    output_path = TEMP_DIR / f"{token}.txt"
    output_path.write_text(result["redacted_text"], encoding="utf-8")

    try:
        log_session(source, result["summary"])
    except Exception:
        pass

    return jsonify({
        "redacted_text":    result["redacted_text"],
        "highlighted_html": result["highlighted_html"],
        "summary":          result["summary"],
        "download_token":   token,
        "source":           source,
        "original_filename": original_filename,
    })


@app.route("/download/<token>", methods=["GET"])
def download(token: str):
    if not token.isalnum() or len(token) > 64:
        return "Invalid token.", 400

    output_path = TEMP_DIR / f"{token}.txt"
    if not output_path.exists():
        return "File not found or expired.", 404

    return send_file(
        output_path,
        as_attachment=True,
        download_name="redacted_output.txt",
        mimetype="text/plain",
    )


@app.route("/history", methods=["GET"])
def history():
    sessions = get_recent_sessions(limit=20)
    return jsonify(sessions)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)