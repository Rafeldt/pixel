"""Bildfilter Stempel-Wanderung - Flask app.

Run:
  python app.py
then open http://127.0.0.1:5000

Accounts are NOT self-registered. Use import_students.py to seed students
from a class roster CSV. Each student logs in with username + password
from the credentials.csv / login_cards.pdf.

Stamps are awarded by the teacher via /teacher, not by entering codes.

Env vars:
  APP_SECRET        Flask session secret (default: dev-secret-change-me)
  TEACHER_PASSWORD  Password for /teacher (default: lehrer)
"""
import json
import os
import sqlite3
from collections import defaultdict
from pathlib import Path

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash

from stamps import STAMPS, TUTORIALS, get_stamp_by_id, tutorial_for_stamp

DB_PATH = Path(__file__).parent / "data" / "progress.db"

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "dev-secret-change-me")


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Ensure schema is current. Idempotent (CREATE IF NOT EXISTS)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
              username      TEXT PRIMARY KEY,
              display_name  TEXT NOT NULL,
              klasse        TEXT,
              password_hash TEXT NOT NULL,
              created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS stamps (
              username   TEXT NOT NULL,
              stamp_id   TEXT NOT NULL,
              claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (username, stamp_id),
              FOREIGN KEY (username) REFERENCES students(username)
                ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS ready_marks (
              username  TEXT NOT NULL,
              stamp_id  TEXT NOT NULL,
              marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (username, stamp_id),
              FOREIGN KEY (username) REFERENCES students(username)
                ON DELETE CASCADE
            );
            """
        )


init_db()


@app.before_request
def drop_stale_session():
    """Clear a logged-in session if the student no longer exists
    (e.g. roster was re-imported and removed them)."""
    if "username" not in session:
        return
    if request.endpoint in (None, "static", "logout"):
        return
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM students WHERE username = ?",
            (session["username"],),
        ).fetchone()
    if not exists:
        session.clear()
        flash("Deine Sitzung ist abgelaufen. Bitte melde dich erneut an.",
              "info")
        return redirect(url_for("index"))


# ===================================================================== Student
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    username = (request.form.get("username") or "").strip().lower()
    password = (request.form.get("password") or "").strip()

    if not username or not password:
        flash("Bitte Benutzername und Passwort eingeben.", "error")
        return redirect(url_for("index"))

    with get_db() as conn:
        row = conn.execute(
            "SELECT password_hash FROM students WHERE username = ?",
            (username,),
        ).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password):
        flash("Benutzername oder Passwort stimmt nicht.", "error")
        return redirect(url_for("index"))

    session["username"] = username
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("index"))
    username = session["username"]
    with get_db() as conn:
        student = conn.execute(
            "SELECT display_name FROM students WHERE username = ?",
            (username,),
        ).fetchone()
        claimed_rows = conn.execute(
            "SELECT stamp_id FROM stamps WHERE username = ? "
            "ORDER BY claimed_at",
            (username,),
        ).fetchall()
        ready_rows = conn.execute(
            "SELECT stamp_id FROM ready_marks WHERE username = ?",
            (username,),
        ).fetchall()
    claimed_ids = [r["stamp_id"] for r in claimed_rows]
    ready_set = {r["stamp_id"] for r in ready_rows}
    # Map stamp_id -> tutorial dict (or None) for the dashboard cards.
    tutorial_by_stamp = {s["id"]: tutorial_for_stamp(s["id"]) for s in STAMPS}
    return render_template(
        "dashboard.html",
        username=username,
        display_name=student["display_name"] if student else username,
        stamps=STAMPS,
        claimed_ids=claimed_ids,
        claimed_set=set(claimed_ids),
        ready_set=ready_set,
        tutorial_by_stamp=tutorial_by_stamp,
    )


@app.route("/tutorials")
def tutorials():
    if "username" not in session and not session.get("teacher"):
        return redirect(url_for("index"))
    stamps_by_id = {s["id"]: s for s in STAMPS}
    return render_template(
        "tutorials.html",
        tutorials=TUTORIALS,
        stamps_by_id=stamps_by_id,
    )


GALLERY_MANIFEST = Path(__file__).parent / "static" / "gallery" / "manifest.json"


@app.route("/gallery")
def gallery():
    """Anonymised showcase: every student's filters run on shared test images.

    Login-gated (students or teacher). The images and manifest are rendered
    offline by render_gallery.py; no student code runs here.
    """
    if "username" not in session and not session.get("teacher"):
        return redirect(url_for("index"))
    try:
        manifest = json.loads(GALLERY_MANIFEST.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        manifest = {"sources": [], "filters": [], "projects": []}

    sources = manifest.get("sources", [])
    source_ids = [s["id"] for s in sources]
    sel = request.args.get("bild")
    if sel not in source_ids:
        sel = source_ids[0] if source_ids else None
    selected = next((s for s in sources if s["id"] == sel), None)

    return render_template(
        "gallery.html",
        sources=sources,
        filters=manifest.get("filters", []),
        projects=manifest.get("projects", []),
        selected=selected,
    )


@app.route("/student/ready", methods=["POST"])
def student_ready():
    if "username" not in session:
        return redirect(url_for("index"))
    stamp_id = (request.form.get("stamp_id") or "").strip()
    if not stamp_id or get_stamp_by_id(stamp_id) is None:
        abort(400)
    username = session["username"]
    with get_db() as conn:
        # Already-awarded stamps don't need a ready mark.
        awarded = conn.execute(
            "SELECT 1 FROM stamps WHERE username = ? AND stamp_id = ?",
            (username, stamp_id),
        ).fetchone()
        if awarded:
            return redirect(url_for("dashboard"))
        existing = conn.execute(
            "SELECT 1 FROM ready_marks WHERE username = ? AND stamp_id = ?",
            (username, stamp_id),
        ).fetchone()
        if existing:
            conn.execute(
                "DELETE FROM ready_marks WHERE username = ? "
                "AND stamp_id = ?",
                (username, stamp_id),
            )
        else:
            conn.execute(
                "INSERT INTO ready_marks (username, stamp_id) "
                "VALUES (?, ?)",
                (username, stamp_id),
            )
        conn.commit()
    return redirect(url_for("dashboard") + f"#stamp-{stamp_id}")


# ===================================================================== Teacher
def require_teacher():
    if not session.get("teacher"):
        abort(403)


@app.route("/teacher", methods=["GET", "POST"])
def teacher():
    teacher_pw = os.environ.get("TEACHER_PASSWORD", "lehrer")
    if request.method == "POST":
        if request.form.get("password") == teacher_pw:
            session["teacher"] = True
        else:
            flash("Falsches Passwort.", "error")
        return redirect(url_for("teacher"))

    if not session.get("teacher"):
        return render_template("teacher_login.html")

    with get_db() as conn:
        students = conn.execute(
            "SELECT username, display_name FROM students "
            "ORDER BY display_name"
        ).fetchall()
        stamp_rows = conn.execute(
            "SELECT username, stamp_id FROM stamps"
        ).fetchall()
        ready_rows = conn.execute(
            "SELECT username, stamp_id FROM ready_marks"
        ).fetchall()
    progress = defaultdict(set)
    for r in stamp_rows:
        progress[r["username"]].add(r["stamp_id"])
    ready = defaultdict(set)
    for r in ready_rows:
        ready[r["username"]].add(r["stamp_id"])

    return render_template(
        "teacher.html",
        students=students,
        stamps=STAMPS,
        progress=progress,
        ready=ready,
    )


@app.route("/teacher/toggle", methods=["POST"])
def teacher_toggle():
    require_teacher()
    username = (request.form.get("username") or "").strip()
    stamp_id = (request.form.get("stamp_id") or "").strip()
    if not username or not stamp_id:
        abort(400)
    if get_stamp_by_id(stamp_id) is None:
        abort(400)

    with get_db() as conn:
        student_exists = conn.execute(
            "SELECT 1 FROM students WHERE username = ?", (username,)
        ).fetchone()
        if not student_exists:
            abort(404)
        existing = conn.execute(
            "SELECT 1 FROM stamps WHERE username = ? AND stamp_id = ?",
            (username, stamp_id),
        ).fetchone()
        if existing:
            conn.execute(
                "DELETE FROM stamps WHERE username = ? AND stamp_id = ?",
                (username, stamp_id),
            )
        else:
            conn.execute(
                "INSERT INTO stamps (username, stamp_id) VALUES (?, ?)",
                (username, stamp_id),
            )
            # Awarding a stamp clears any pending self-mark.
            conn.execute(
                "DELETE FROM ready_marks WHERE username = ? "
                "AND stamp_id = ?",
                (username, stamp_id),
            )
        conn.commit()
    # Preserve scroll/focus by anchoring to the toggled student row
    return redirect(url_for("teacher") + f"#student-{username}")


@app.route("/teacher/logout")
def teacher_logout():
    session.pop("teacher", None)
    return redirect(url_for("teacher"))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
