"""Import students from a class roster CSV into the website's database.

Usage:
    python import_students.py path\\to\\roster.csv

The roster CSV uses ';' as separator and has columns:
    Klasse;Nachname;Vorname;...

For each student we:
  - derive a username from the first word of Vorname (lowercased, accents
    stripped),
  - reuse an existing password from credentials.csv if the student is
    already known, otherwise generate a fresh 6-character password,
  - insert or update the row in the students table,
  - write credentials.csv (next to this script) for use by
    generate_login_cards.py.

Re-run this script when the roster changes; existing students keep their
passwords, new students get fresh ones.
"""
import csv
import secrets
import sqlite3
import sys
import unicodedata
from pathlib import Path

from werkzeug.security import generate_password_hash

HERE = Path(__file__).parent
DB_PATH = HERE / "data" / "progress.db"
CREDENTIALS_CSV = HERE / "credentials.csv"

# Avoid ambiguous chars (0/O, 1/l/i) for hand-typeable passwords
PWD_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
PWD_LENGTH = 6


def slugify(name: str) -> str:
    """First word of name, accents removed, lowercased, alphanumeric only."""
    first = name.strip().split()[0]
    normalized = unicodedata.normalize("NFKD", first)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return "".join(ch for ch in ascii_only if ch.isalnum()).lower()


def gen_password() -> str:
    return "".join(secrets.choice(PWD_ALPHABET) for _ in range(PWD_LENGTH))


def load_existing_passwords() -> dict[str, str]:
    if not CREDENTIALS_CSV.exists():
        return {}
    with CREDENTIALS_CSV.open(encoding="utf-8", newline="") as f:
        return {row["username"]: row["password"] for row in csv.DictReader(f)}


def ensure_schema(conn: sqlite3.Connection) -> None:
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
          FOREIGN KEY (username) REFERENCES students(username) ON DELETE CASCADE
        );
        """
    )


def main(csv_path: Path) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing = load_existing_passwords()
    records = []
    seen_usernames = set()

    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            klasse = (row.get("Klasse") or "").strip()
            nachname = (row.get("Nachname") or "").strip()
            vorname = (row.get("Vorname") or "").strip()
            if not vorname:
                continue
            username = slugify(vorname)
            if not username:
                print(f"  skipping {vorname!r} (no usable username)")
                continue
            if username in seen_usernames:
                print(f"  WARNING: duplicate username {username!r} "
                      f"(student {vorname} {nachname}). Skipping.")
                continue
            seen_usernames.add(username)
            display = f"{vorname} {nachname}".strip()
            password = existing.get(username) or gen_password()
            records.append((username, display, klasse, password))

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_schema(conn)
    new_count = 0
    update_count = 0
    for username, display, klasse, password in records:
        exists = conn.execute(
            "SELECT 1 FROM students WHERE username = ?", (username,)
        ).fetchone()
        if exists:
            conn.execute(
                "UPDATE students SET display_name = ?, klasse = ? "
                "WHERE username = ?",
                (display, klasse, username),
            )
            update_count += 1
        else:
            conn.execute(
                "INSERT INTO students (username, display_name, klasse, "
                "password_hash) VALUES (?, ?, ?, ?)",
                (username, display, klasse, generate_password_hash(password)),
            )
            new_count += 1
    conn.commit()
    conn.close()

    with CREDENTIALS_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["username", "password", "display_name", "klasse"]
        )
        w.writeheader()
        for username, display, klasse, password in records:
            w.writerow(
                {"username": username, "password": password,
                 "display_name": display, "klasse": klasse}
            )

    print(f"Read {len(records)} students from {csv_path.name}")
    print(f"  {new_count} new, {update_count} existing (passwords preserved)")
    print(f"Credentials -> {CREDENTIALS_CSV}")
    print(f"Database    -> {DB_PATH}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_students.py <roster.csv>")
        sys.exit(1)
    main(Path(sys.argv[1]))
