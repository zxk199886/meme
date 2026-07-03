"""Local web front-end: upload old + new CML, view the differences, download
the marked-up workbook.

Run with:
    python -m cml_compare.webapp        (opens on http://127.0.0.1:5000)

Uploads are processed in a temporary directory; nothing is persisted after
the server stops.
"""

from __future__ import annotations

import os
import tempfile
import uuid

from flask import Flask, abort, render_template, request, send_file
from werkzeug.utils import secure_filename

from .cli import default_output_name
from .diff import compare
from .parser import CMLParseError, parse_cml
from .report import write_marked_up_report

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

_WORKDIR = tempfile.mkdtemp(prefix="cml_compare_")
_RESULTS: dict[str, str] = {}  # token -> path of marked-up workbook


@app.get("/")
def index():
    return render_template("index.html", result=None, error=None)


@app.post("/compare")
def compare_files():
    old_file = request.files.get("old_file")
    new_file = request.files.get("new_file")
    if not old_file or not new_file or not old_file.filename or not new_file.filename:
        return render_template("index.html", result=None,
                               error="Please select both the OLD and the NEW CML file.")

    token = uuid.uuid4().hex
    updir = os.path.join(_WORKDIR, token)
    os.makedirs(updir, exist_ok=True)
    old_path = os.path.join(updir, "OLD_" + secure_filename(old_file.filename))
    new_path = os.path.join(updir, "NEW_" + secure_filename(new_file.filename))
    old_file.save(old_path)
    new_file.save(new_path)

    try:
        diff = compare(parse_cml(old_path), parse_cml(new_path))
        out_name = default_output_name(new_file.filename)
        out_path = os.path.join(updir, out_name)
        write_marked_up_report(diff, out_path)
    except CMLParseError as exc:
        return render_template("index.html", result=None,
                               error=f"Could not parse the workbook: {exc}")

    _RESULTS[token] = out_path
    common = set(diff.old_doc.features) & set(diff.new_doc.features)
    result = {
        "token": token,
        "download_name": out_name,
        "old_name": old_file.filename,
        "new_name": new_file.filename,
        "old_version": diff.old_doc.version or "n/a",
        "new_version": diff.new_doc.version or "n/a",
        "old_count": len(diff.old_doc.features),
        "new_count": len(diff.new_doc.features),
        "unchanged": len(common) - len(diff.modified_features),
        "diff": diff,
    }
    return render_template("index.html", result=result, error=None)


@app.get("/download/<token>")
def download(token):
    path = _RESULTS.get(token)
    if not path or not os.path.isfile(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


def main():
    print("CML Compare web app - open http://127.0.0.1:5000 in your browser")
    app.run(host="127.0.0.1", port=int(os.environ.get("CML_COMPARE_PORT", "5000")))


if __name__ == "__main__":
    main()
