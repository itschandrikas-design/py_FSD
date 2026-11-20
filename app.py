import os
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from jinja2 import DictLoader


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-demo-secret")
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bloodbank.db")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ELIGIBILITY_WAIT_DAYS = 56

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
COMPATIBLE_DONORS = {
    "A+": ["A+", "A-", "O+", "O-"],
    "A-": ["A-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "AB+": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
    "AB-": ["A-", "B-", "AB-", "O-"],
    "O+": ["O+", "O-"],
    "O-": ["O-"],
}


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS donors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT,
                blood_group TEXT NOT NULL,
                phone TEXT NOT NULL,
                location TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                blood_group TEXT NOT NULL,
                units INTEGER NOT NULL,
                location TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blood_group TEXT UNIQUE NOT NULL,
                units INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blood_group TEXT NOT NULL,
                units INTEGER NOT NULL CHECK (units >= 0),
                collected_on TEXT NOT NULL,
                expires_on TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name TEXT PRIMARY KEY
            )
        """)

        donor_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(donors)")
        }
        if "last_donation_date" not in donor_columns:
            conn.execute("ALTER TABLE donors ADD COLUMN last_donation_date TEXT")

        request_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(requests)")
        }
        if "priority" not in request_columns:
            conn.execute(
                "ALTER TABLE requests ADD COLUMN priority TEXT NOT NULL DEFAULT 'Normal'"
            )

        for group in BLOOD_GROUPS:
            conn.execute(
                "INSERT OR IGNORE INTO inventory (blood_group, units) VALUES (?, 0)",
                (group,),
            )

        migrated = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE name = ?",
            ("inventory_batches_v1",),
        ).fetchone()
        if migrated is None:
            conn.execute("""
                INSERT INTO inventory_batches
                    (blood_group, units, collected_on, expires_on)
                SELECT blood_group, units, date('now'), NULL
                FROM inventory
                WHERE units > 0
            """)
            conn.execute("UPDATE inventory SET units = 0")
            conn.execute(
                "INSERT INTO schema_migrations (name) VALUES (?)",
                ("inventory_batches_v1",),
            )


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def donor_is_eligible(donor):
    if not 18 <= donor["age"] <= 65:
        return False
    last_donation = donor["last_donation_date"]
    if not last_donation:
        return True
    try:
        last_date = date.fromisoformat(last_donation)
    except ValueError:
        return False
    return last_date <= date.today() - timedelta(days=ELIGIBILITY_WAIT_DAYS)


TEMPLATES = {
    "base.html": """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }} - Smart Blood Bank</title>
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; color: #333; background: #f4f6f9; font-family: Arial, sans-serif; }
        .navbar { display: flex; justify-content: space-between; align-items: center; gap: 16px;
            padding: 16px 5%; color: white; background: #b51224; }
        .navbar h2 { margin: 0; }
        .nav-links { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
        .navbar a, .nav-button { padding: 9px 13px; color: white; background: #ffffff26;
            border: 0; border-radius: 6px; text-decoration: none; cursor: pointer; font-size: 14px; }
        .container { width: 92%; max-width: 1150px; margin: 30px auto; }
        h1 { color: #b51224; }
        .login-page { min-height: 100vh; display: grid; place-items: center; padding: 20px;
            background: linear-gradient(135deg, #8b0015, #ef5350); }
        .login-box { width: 100%; max-width: 430px; padding: 36px; text-align: center;
            background: white; border-radius: 14px; box-shadow: 0 10px 35px #0003; }
        .login-box h1 { margin-top: 0; }
        .form-box, .card, .table-box { margin: 18px 0; padding: 20px; background: white;
            border-radius: 10px; box-shadow: 0 3px 14px #0000000d; }
        input, select { width: 100%; margin: 7px 0; padding: 11px; border: 1px solid #ccc;
            border-radius: 6px; font-size: 15px; }
        button, .button { display: inline-block; margin: 4px 2px; padding: 10px 13px;
            color: white; background: #b51224; border: 0; border-radius: 6px;
            text-decoration: none; cursor: pointer; font-size: 14px; }
        button:hover, .button:hover { background: #870018; }
        .green { background: #198754; } .blue { background: #1675c1; } .gray { background: #666; }
        .message { padding: 11px; color: #8b0015; background: #ffe8ea; border-radius: 6px; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; }
        .card { text-align: center; } .card h2 { color: #b51224; }
        .table-box { overflow-x: auto; } table { width: 100%; border-collapse: collapse; min-width: 650px; }
        th, td { padding: 11px; text-align: left; vertical-align: top; border-bottom: 1px solid #eee; }
        th { color: white; background: #b51224; } .blood { color: #b51224; font-weight: bold; }
        .status-eligible { color: #14743b; font-weight: bold; }
        .status-ineligible { color: #b51224; font-weight: bold; }
        .filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 8px; }
        .inline-form { display: inline-block; }
        @media (max-width: 620px) {
            .navbar { align-items: flex-start; flex-direction: column; }
            .login-box { padding: 26px 20px; }
        }
    </style>
</head>
<body>
{% if not login_page %}
<nav class="navbar">
    <h2>🩸 Smart Blood Bank</h2>
    <div class="nav-links">
    {% if session.get('admin') %}
        <a href="{{ url_for('dashboard') }}">Dashboard</a>
        <a href="{{ url_for('donors') }}">Donors</a>
        <a href="{{ url_for('requests_page') }}">Requests</a>
        <a href="{{ url_for('inventory_page') }}">Inventory</a>
        <form class="inline-form" action="{{ url_for('logout') }}" method="post">
            <button class="nav-button" type="submit">Logout</button>
        </form>
    {% else %}
        <a href="{{ url_for('login') }}">Admin Login</a>
        <a href="{{ url_for('register_donor') }}">Donor Registration</a>
    {% endif %}
    </div>
</nav>
{% endif %}
{% for message in get_flashed_messages() %}
    <div class="container"><p class="message">{{ message }}</p></div>
{% endfor %}
{% block content %}{% endblock %}
</body>
</html>
""",
    "index.html": """
{% extends "base.html" %}
{% block content %}
<main class="login-page"><section class="login-box">
    <h1>🩸 Smart Blood Bank</h1>
    <p>Management &amp; Intelligent Donor Matching System</p>
    <h2>Admin Login</h2>
    <p>Demo login: <strong>admin</strong> / <strong>admin123</strong></p>
    <form action="{{ url_for('login') }}" method="post">
        <input name="username" placeholder="Enter Username" autocomplete="username" required>
        <input name="password" type="password" placeholder="Enter Password"
               autocomplete="current-password" required>
        <button type="submit">Login</button>
    </form>
    <a href="{{ url_for('register_donor') }}">Register as a Blood Donor</a>
</section></main>
{% endblock %}
""",
    "dashboard.html": """
{% extends "base.html" %}
{% block content %}<main class="container">
    <h1>Admin Dashboard</h1><p>Blood Bank Management System overview</p>
    <section class="cards">
        <div class="card"><h3>Total Donors</h3><h2>{{ donors }}</h2></div>
        <div class="card"><h3>Blood Requests</h3><h2>{{ requests_count }}</h2></div>
        <div class="card"><h3>Usable Blood Units</h3><h2>{{ inventory }}</h2></div>
        <div class="card"><h3>Pending Requests</h3><h2>{{ pending }}</h2></div>
    </section>
</main>{% endblock %}
""",
    "register.html": """
{% extends "base.html" %}
{% block content %}<main class="container"><section class="form-box">
    <h1>Donor Registration</h1>
    <p>Eligibility screening uses an age range of 18–65 and a 56-day interval since the last donation.</p>
    <form method="post">
        <input name="name" placeholder="Full Name" required>
        <input name="age" type="number" min="18" max="65" placeholder="Age (18-65)" required>
        <select name="gender"><option value="">Select Gender</option>
            <option>Male</option><option>Female</option><option>Other</option></select>
        <select name="blood_group" required><option value="">Select Blood Group</option>
            {% for group in groups %}<option>{{ group }}</option>{% endfor %}</select>
        <input name="phone" type="tel" placeholder="Phone Number" required>
        <input name="location" placeholder="City / Location" required>
        <label for="last_donation_date">Last donation date (leave blank if never donated)</label>
        <input id="last_donation_date" name="last_donation_date" type="date"
               max="{{ today }}">
        <button type="submit">Register Donor</button>
    </form>
</section></main>{% endblock %}
""",
    "donors.html": """
{% extends "base.html" %}
{% block content %}<main class="container">
    <h1>{% if matching %}Compatible Donors{% else %}Registered Donors{% endif %}</h1>
    {% if matching %}<p>Only eligible donors with compatible blood groups are shown.</p>{% endif %}
    <section class="form-box">
        <form class="filters" method="get">
            <input name="q" value="{{ filters.q }}" placeholder="Search name, phone, or location">
            <select name="blood_group"><option value="">All blood groups</option>
                {% for group in groups %}<option value="{{ group }}"
                    {% if filters.blood_group == group %}selected{% endif %}>{{ group }}</option>{% endfor %}
            </select>
            <input name="location" value="{{ filters.location }}" placeholder="Filter by location">
            <button type="submit">Search / Filter</button>
        </form>
        {% if matching %}<a class="button gray" href="{{ url_for('donors') }}">Clear filters</a>{% endif %}
    </section>
    <section class="table-box"><table>
        <thead><tr><th>ID</th><th>Name</th><th>Age</th><th>Blood</th><th>Phone</th>
        <th>Location</th><th>Last Donation</th><th>Eligibility</th>
        {% if not matching %}<th>Action</th>{% endif %}</tr></thead>
        <tbody>
        {% for donor in donors %}
        <tr><td>{{ donor.id }}</td><td>{{ donor.name }}</td><td>{{ donor.age }}</td>
            <td class="blood">{{ donor.blood_group }}</td><td>{{ donor.phone }}</td>
            <td>{{ donor.location }}</td><td>{{ donor.last_donation_date or "Not provided" }}</td>
            <td>{% if donor.id in eligible_ids %}<span class="status-eligible">Eligible</span>
                {% else %}<span class="status-ineligible">Not eligible</span>{% endif %}</td>
            {% if not matching %}<td><form method="post"
                action="{{ url_for('delete_donor', donor_id=donor.id) }}">
                <button type="submit">Delete</button></form></td>{% endif %}
        </tr>
        {% else %}<tr><td colspan="{% if matching %}8{% else %}9{% endif %}">No donors found.</td></tr>
        {% endfor %}
        </tbody>
    </table></section>
</main>{% endblock %}
""",
    "requests.html": """
{% extends "base.html" %}
{% block content %}<main class="container">
    <h1>Blood Request Management</h1>
    <section class="form-box"><h2>Submit a Request</h2>
        <form method="post">
            <input name="patient_name" placeholder="Patient Name" required>
            <select name="blood_group" required><option value="">Select Blood Group</option>
                {% for group in groups %}<option>{{ group }}</option>{% endfor %}</select>
            <input name="units" type="number" min="1" max="100"
                   placeholder="Required Units" required>
            <input name="location" placeholder="Hospital / City Location" required>
            <select name="priority"><option value="Normal">Normal priority</option>
                <option value="Urgent">Urgent</option></select>
            <button type="submit">Submit Request</button>
        </form>
    </section>
    <section class="table-box"><h2>All Requests</h2><table>
        <thead><tr><th>ID</th><th>Patient</th><th>Blood</th><th>Units</th>
        <th>Location</th><th>Priority</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>{% for item in requests %}
        <tr><td>{{ item.id }}</td><td>{{ item.patient_name }}</td>
            <td class="blood">{{ item.blood_group }}</td><td>{{ item.units }}</td>
            <td>{{ item.location }}</td><td>{{ item.priority }}</td><td>{{ item.status }}</td>
            <td><a class="button blue" href="{{ url_for('match_donors', request_id=item.id) }}">Find Donors</a>
                {% if item.status == "Pending" %}
                <form class="inline-form" method="post"
                    action="{{ url_for('update_status', request_id=item.id) }}">
                    <button class="green" name="status" value="Approved">Approve</button>
                    <button name="status" value="Rejected">Reject</button>
                </form>{% endif %}
            </td></tr>
        {% else %}<tr><td colspan="8">No requests available.</td></tr>{% endfor %}</tbody>
    </table></section>
</main>{% endblock %}
""",
    "inventory.html": """
{% extends "base.html" %}
{% block content %}<main class="container">
    <h1>Blood Inventory</h1>
    <p>Only non-expired batches with a recorded expiry date can be used to approve requests.
       Blood groups in each batch are deducted from earliest expiry first.</p>
    <section class="form-box"><h2>Add a Blood Batch</h2>
        <form method="post">
            <select name="blood_group" required><option value="">Select Blood Group</option>
                {% for group in groups %}<option>{{ group }}</option>{% endfor %}</select>
            <input name="units" type="number" min="1" max="10000"
                   placeholder="Units in this batch" required>
            <label for="collected_on">Collection date</label>
            <input id="collected_on" name="collected_on" type="date"
                   value="{{ today }}" max="{{ today }}" required>
            <label for="expires_on">Expiry date</label>
            <input id="expires_on" name="expires_on" type="date" min="{{ tomorrow }}" required>
            <button type="submit">Add Batch</button>
        </form>
    </section>
    <section class="cards">{% for row in totals %}
        <div class="card"><h2>{{ row.blood_group }}</h2>
            <p>{{ row.usable }} usable units</p>
            <p>{{ row.expired }} expired units</p>
            <p>{{ row.unknown }} units with no expiry record</p></div>
    {% endfor %}</section>
    <section class="table-box"><h2>Inventory Batches</h2><table>
        <thead><tr><th>Blood</th><th>Units</th><th>Collected</th><th>Expires</th><th>Batch status</th></tr></thead>
        <tbody>{% for batch in batches %}
        <tr><td class="blood">{{ batch.blood_group }}</td><td>{{ batch.units }}</td>
            <td>{{ batch.collected_on }}</td><td>{{ batch.expires_on or "Not recorded" }}</td>
            <td>{{ batch.batch_status }}</td></tr>
        {% else %}<tr><td colspan="5">No inventory batches yet.</td></tr>{% endfor %}</tbody>
    </table></section>
</main>{% endblock %}
""",
}

app.jinja_loader = DictLoader(TEMPLATES)


def render_page(template, title, **context):
    context["title"] = title
    context.setdefault("login_page", False)
    return render_template(template, **context)


def filter_values():
    return {
        "q": request.args.get("q", "").strip(),
        "blood_group": request.args.get("blood_group", "").strip(),
        "location": request.args.get("location", "").strip(),
    }


def add_donor_filters(query, params, filters):
    if filters["q"]:
        value = "%" + filters["q"] + "%"
        query += " AND (name LIKE ? OR phone LIKE ? OR location LIKE ?)"
        params.extend((value, value, value))
    if filters["blood_group"] in BLOOD_GROUPS:
        query += " AND blood_group = ?"
        params.append(filters["blood_group"])
    if filters["location"]:
        query += " AND location LIKE ?"
        params.append("%" + filters["location"] + "%")
    return query, params


@app.route("/")
def index():
    return render_page("index.html", "Admin Login", login_page=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form.get("username") == ADMIN_USERNAME
                and request.form.get("password") == ADMIN_PASSWORD):
            session["admin"] = True
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.")
    return render_page("index.html", "Admin Login", login_page=True)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    with get_db() as conn:
        donors = conn.execute("SELECT COUNT(*) FROM donors").fetchone()[0]
        request_count = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM requests WHERE status = 'Pending'"
        ).fetchone()[0]
        total_units = conn.execute("""
            SELECT COALESCE(SUM(units), 0) FROM inventory_batches
            WHERE expires_on IS NOT NULL AND date(expires_on) >= date('now')
        """).fetchone()[0]
    return render_page(
        "dashboard.html", "Dashboard", donors=donors,
        requests_count=request_count, pending=pending, inventory=total_units
    )


@app.route("/register", methods=["GET", "POST"])
def register_donor():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age = request.form.get("age", type=int)
        gender = request.form.get("gender", "")
        blood_group = request.form.get("blood_group", "")
        phone = request.form.get("phone", "").strip()
        location = request.form.get("location", "").strip()
        last_date_text = request.form.get("last_donation_date", "").strip()

        if not name or age is None or not 18 <= age <= 65:
            flash("Enter a name and a valid age between 18 and 65.")
        elif blood_group not in BLOOD_GROUPS or not phone or not location:
            flash("Please complete all registration fields.")
        else:
            last_date = None
            if last_date_text:
                try:
                    last_date = date.fromisoformat(last_date_text)
                except ValueError:
                    flash("Enter a valid last donation date.")
                    return render_page(
                        "register.html", "Donor Registration",
                        groups=BLOOD_GROUPS, today=date.today().isoformat()
                    )
                if last_date > date.today():
                    flash("Last donation date cannot be in the future.")
                    return render_page(
                        "register.html", "Donor Registration",
                        groups=BLOOD_GROUPS, today=date.today().isoformat()
                    )

            with get_db() as conn:
                conn.execute("""
                    INSERT INTO donors
                        (name, age, gender, blood_group, phone, location, last_donation_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name, age, gender, blood_group, phone, location, last_date_text or None))

            if last_date and last_date > date.today() - timedelta(days=ELIGIBILITY_WAIT_DAYS):
                eligible_on = last_date + timedelta(days=ELIGIBILITY_WAIT_DAYS)
                flash("Donor registered. Based on the entered date, eligible again on "
                      + eligible_on.isoformat() + ".")
            else:
                flash("Donor registered and currently eligible based on the entered details.")
            return redirect(url_for("register_donor"))

    return render_page(
        "register.html", "Donor Registration",
        groups=BLOOD_GROUPS, today=date.today().isoformat()
    )


@app.route("/donors")
@login_required
def donors():
    filters = filter_values()
    query = "SELECT * FROM donors WHERE 1=1"
    query, params = add_donor_filters(query, [], filters)
    query += " ORDER BY id DESC"
    with get_db() as conn:
        donor_list = conn.execute(query, params).fetchall()
    eligible_ids = {row["id"] for row in donor_list if donor_is_eligible(row)}
    return render_page(
        "donors.html", "Donors", donors=donor_list, matching=False,
        eligible_ids=eligible_ids, groups=BLOOD_GROUPS, filters=filters
    )


@app.route("/delete_donor/<int:donor_id>", methods=["POST"])
@login_required
def delete_donor(donor_id):
    with get_db() as conn:
        result = conn.execute("DELETE FROM donors WHERE id = ?", (donor_id,))
    flash("Donor deleted." if result.rowcount else "Donor not found.")
    return redirect(url_for("donors"))


@app.route("/requests", methods=["GET", "POST"])
@login_required
def requests_page():
    if request.method == "POST":
        patient = request.form.get("patient_name", "").strip()
        blood_group = request.form.get("blood_group", "")
        units = request.form.get("units", type=int)
        location = request.form.get("location", "").strip()
        priority = request.form.get("priority", "Normal")
        if (not patient or blood_group not in BLOOD_GROUPS or units is None
                or not 1 <= units <= 100 or not location
                or priority not in ("Normal", "Urgent")):
            flash("Please enter valid blood request details.")
        else:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO requests
                        (patient_name, blood_group, units, location, priority)
                    VALUES (?, ?, ?, ?, ?)
                """, (patient, blood_group, units, location, priority))
            flash("Blood request submitted.")

    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM requests
            ORDER BY CASE WHEN priority = 'Urgent' THEN 0 ELSE 1 END, id DESC
        """).fetchall()
    return render_page(
        "requests.html", "Blood Requests", requests=rows, groups=BLOOD_GROUPS
    )


@app.route("/match/<int:request_id>")
@login_required
def match_donors(request_id):
    filters = filter_values()
    with get_db() as conn:
        blood_request = conn.execute(
            "SELECT * FROM requests WHERE id = ?", (request_id,)
        ).fetchone()
        if blood_request is None:
            flash("Blood request not found.")
            return redirect(url_for("requests_page"))

        groups = COMPATIBLE_DONORS[blood_request["blood_group"]]
        query = """
            SELECT * FROM donors
            WHERE blood_group IN ({})
              AND age BETWEEN 18 AND 65
              AND (last_donation_date IS NULL OR
                   date(last_donation_date) <= date('now', '-{} days'))
        """.format(",".join("?" for _ in groups), ELIGIBILITY_WAIT_DAYS)
        params = list(groups)
        query, params = add_donor_filters(query, params, filters)
        query += """
            ORDER BY CASE WHEN LOWER(location) = LOWER(?) THEN 0 ELSE 1 END,
                     age, id DESC
        """
        params.append(blood_request["location"])
        donor_list = conn.execute(query, params).fetchall()

    eligible_ids = {row["id"] for row in donor_list}
    return render_page(
        "donors.html", "Matching Donors", donors=donor_list, matching=True,
        eligible_ids=eligible_ids, groups=BLOOD_GROUPS, filters=filters
    )


@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory_page():
    if request.method == "POST":
        group = request.form.get("blood_group", "")
        units = request.form.get("units", type=int)
        collected_text = request.form.get("collected_on", "")
        expires_text = request.form.get("expires_on", "")
        try:
            collected = date.fromisoformat(collected_text)
            expires = date.fromisoformat(expires_text)
        except ValueError:
            collected = None
            expires = None

        if (group not in BLOOD_GROUPS or units is None or not 1 <= units <= 10000
                or collected is None or expires is None):
            flash("Enter valid blood group, units, and collection/expiry dates.")
        elif collected > date.today() or expires <= collected:
            flash("Collection date must not be in the future, and expiry must be after collection.")
        else:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO inventory_batches
                        (blood_group, units, collected_on, expires_on)
                    VALUES (?, ?, ?, ?)
                """, (group, units, collected.isoformat(), expires.isoformat()))
            flash("Inventory batch added.")

    today = date.today()
    with get_db() as conn:
        batches = conn.execute("""
            SELECT * FROM inventory_batches
            ORDER BY CASE WHEN expires_on IS NULL THEN 1 ELSE 0 END,
                     expires_on, id
        """).fetchall()
        totals = []
        for group in BLOOD_GROUPS:
            group_batches = conn.execute(
                "SELECT units, expires_on FROM inventory_batches WHERE blood_group = ?",
                (group,),
            ).fetchall()
            usable = sum(
                row["units"] for row in group_batches
                if row["expires_on"] and row["expires_on"] >= today.isoformat()
            )
            expired = sum(
                row["units"] for row in group_batches
                if row["expires_on"] and row["expires_on"] < today.isoformat()
            )
            unknown = sum(
                row["units"] for row in group_batches if not row["expires_on"]
            )
            totals.append({
                "blood_group": group,
                "usable": usable,
                "expired": expired,
                "unknown": unknown,
            })

    batch_rows = []
    for row in batches:
        item = dict(row)
        if not item["expires_on"]:
            item["batch_status"] = "Expiry unknown - not usable"
        elif item["expires_on"] < today.isoformat():
            item["batch_status"] = "Expired"
        else:
            item["batch_status"] = "Available"
        batch_rows.append(item)

    return render_page(
        "inventory.html", "Inventory", groups=BLOOD_GROUPS, totals=totals,
        batches=batch_rows, today=today.isoformat(),
        tomorrow=(today + timedelta(days=1)).isoformat()
    )


@app.route("/update_status/<int:request_id>", methods=["POST"])
@login_required
def update_status(request_id):
    status = request.form.get("status", "")
    if status not in ("Approved", "Rejected"):
        flash("Invalid request status.")
        return redirect(url_for("requests_page"))

    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        blood_request = conn.execute(
            "SELECT * FROM requests WHERE id = ?", (request_id,)
        ).fetchone()
        if blood_request is None:
            flash("Blood request not found.")
        elif blood_request["status"] != "Pending":
            flash("Only pending requests can be updated.")
        elif status == "Rejected":
            conn.execute(
                "UPDATE requests SET status = 'Rejected' WHERE id = ?",
                (request_id,),
            )
            flash("Request rejected.")
        else:
            compatible = COMPATIBLE_DONORS[blood_request["blood_group"]]
            placeholders = ",".join("?" for _ in compatible)
            stock = conn.execute(f"""
                SELECT id, units FROM inventory_batches
                WHERE blood_group IN ({placeholders})
                  AND expires_on IS NOT NULL
                  AND date(expires_on) >= date('now')
                  AND units > 0
                ORDER BY expires_on, id
            """, compatible).fetchall()
            available = sum(row["units"] for row in stock)
            needed = blood_request["units"]

            if available < needed:
                flash("Not enough unexpired compatible inventory. "
                      f"Available: {available}; required: {needed}.")
            else:
                remaining = needed
                for batch in stock:
                    if remaining == 0:
                        break
                    deducted = min(remaining, batch["units"])
                    conn.execute(
                        "UPDATE inventory_batches SET units = units - ? WHERE id = ?",
                        (deducted, batch["id"]),
                    )
                    remaining -= deducted
                conn.execute(
                    "UPDATE requests SET status = 'Approved' WHERE id = ?",
                    (request_id,),
                )
                flash("Request approved and compatible stock deducted.")

    return redirect(url_for("requests_page"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
