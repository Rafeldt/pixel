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
import os
import sqlite3
from collections import defaultdict
from pathlib import Path

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash

from stamps import STAMPS, get_stamp_by_id

DB_PATH = Path(__file__).parent / "data" / "progress.db"

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "dev-secret-change-me")


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
        rows = conn.execute(
            "SELECT stamp_id FROM stamps WHERE username = ? "
            "ORDER BY claimed_at",
            (username,),
        ).fetchall()
    claimed_ids = [r["stamp_id"] for r in rows]
    return render_template(
        "dashboard.html",
        username=username,
        display_name=student["display_name"] if student else username,
        stamps=STAMPS,
        claimed_ids=claimed_ids,
        claimed_set=set(claimed_ids),
    )


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
    progress = defaultdict(set)
    for r in stamp_rows:
        progress[r["username"]].add(r["stamp_id"])

    return render_template(
        "teacher.html",
        students=students,
        stamps=STAMPS,
        progress=progress,
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
        conn.commit()
    # Preserve scroll/focus by anchoring to the toggled student row
    return redirect(url_for("teacher") + f"#student-{username}")


@app.route("/teacher/logout")
def teacher_logout():
    session.pop("teacher", None)
    return redirect(url_for("teacher"))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
