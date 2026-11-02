"""SQLite access. One connection per request; foreign keys on; rows as dicts."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click
from flask.cli import with_appcontext
from flask import current_app, g


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        path = current_app.config["DATABASE"]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(path, timeout=10, detect_types=0)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript((Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
    db.commit()


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create the database tables (safe to run again - existing data is kept)."""
    init_db()
    click.echo(f"Database ready: {current_app.config['DATABASE']}")


@click.command("create-admin")
@with_appcontext
@click.option("--username", prompt=True)
@click.password_option(confirmation_prompt=True)
def create_admin_command(username, password):
    """Create an administrator account (or reset its password)."""
    from werkzeug.security import generate_password_hash
    from .security import password_problem
    problem = password_problem(password)
    if problem:
        raise click.ClickException(problem)
    init_db()
    db = get_db()
    h = generate_password_hash(password, method="scrypt")
    if db.execute("SELECT 1 FROM admins WHERE username = ?", (username,)).fetchone():
        db.execute("UPDATE admins SET password_hash = ? WHERE username = ?", (h, username))
        msg = f"Password updated for '{username}'."
    else:
        db.execute("INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)", (username, h, now()))
        msg = f"Administrator '{username}' created."
    db.commit()
    click.echo(msg)


@click.command("seed-demo")
@with_appcontext
@click.option("--count", default=12, show_default=True)
def seed_demo_command(count):
    """Add clearly-marked DEMO enquiries so the admin area can be explored. Never use on the live site."""
    import random
    from .pricing import estimate
    from .security import new_reference
    init_db()
    db = get_db()
    rng = random.Random(7)
    first = ["Amelia", "Oliver", "Isla", "George", "Ava", "Harry", "Mia", "Noah", "Grace", "Jack", "Freya", "Leo"]
    last = ["Patel", "Hughes", "Khan", "Walsh", "Evans", "Begum", "Taylor", "Reid", "Moore", "Clarke"]
    services = [("residential", "regular"), ("residential", "deep"), ("residential", "end_of_tenancy"), ("commercial", "office_regular"),
                ("residential", "after_builders"), ("commercial", "office_deep")]
    for i in range(count):
        sector, service = rng.choice(services)
        beds, baths, area = rng.randint(1, 4), rng.randint(1, 2), rng.choice([1500, 2500, 4000, 8000])
        freq = rng.choice(["weekly", "fortnightly", "one_off"]) if service in ("regular", "office_regular") else "one_off"
        est = estimate(sector, service, beds, baths, area, freq, [])
        name = f"DEMO {rng.choice(first)} {rng.choice(last)}"
        created = now()
        db.execute("""INSERT INTO enquiries (ref, kind, status, created_at, updated_at, name, email, phone, postcode, sector, service,
                      bedrooms, bathrooms, floor_area, frequency, extras, preferred_date, message, estimate_low, estimate_high, contact_pref)
                      VALUES (?, 'quote', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', NULL, ?, ?, ?, 'email')""",
                   (new_reference(), rng.choice(["new", "new", "contacted", "quoted", "booked"]), created, created, name,
                    f"demo{i}@example.com", "07700 900" + str(100 + i), rng.choice(["M1 2AB", "M20 6RT", "SK4 3HG", "M33 7YT"]),
                    sector, service, beds if sector == "residential" else None, baths if sector == "residential" else None,
                    area if sector == "commercial" else None, freq, "Demo enquiry - safe to delete.", est[0], est[1]))
    db.commit()
    click.echo(f"Added {count} demo enquiries (names start with 'DEMO').")


@click.command("purge-old")
@click.option("--months", default=12, show_default=True, help="Delete enquiries older than this that never became bookings.")
@click.option("--yes", is_flag=True, help="Skip the confirmation question (for scheduled jobs).")
@with_appcontext
def purge_old_command(months, yes):
    """Delete old enquiries that didn't lead to a booking, as promised in the privacy notice."""
    db = get_db()
    where = "status != 'booked' AND created_at < datetime('now', ?)"
    arg = f"-{int(months)} months"
    n = db.execute(f"SELECT COUNT(*) FROM enquiries WHERE {where}", (arg,)).fetchone()[0]
    if n == 0:
        click.echo("Nothing to delete.")
        return
    if not yes:
        click.confirm(f"Permanently delete {n} enquiries older than {months} months that were never booked?", abort=True)
    db.execute(f"DELETE FROM enquiries WHERE {where}", (arg,))
    db.commit()
    click.echo(f"Deleted {n} enquiries.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(seed_demo_command)
    app.cli.add_command(purge_old_command)
