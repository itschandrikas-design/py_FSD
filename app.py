from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import get_db, init_db
from functools import wraps

app = Flask(__name__)
app.secret_key = "bloodbank_project_secret_2026"

init_db()

# Educational donor compatibility rules
COMPATIBLE_DONORS = {
    "A+": ["A+", "A-", "O+", "O-"],
    "A-": ["A-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "AB+": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
    "AB-": ["A-", "B-", "AB-", "O-"],
    "O+": ["O+", "O-"],
    "O-": ["O-"]
}

# Simple admin login for mini project
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("dashboard"))

        flash("Invalid username or password")

    return render_template("index.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()

    donors = conn.execute(
        "SELECT COUNT(*) FROM donors"
    ).fetchone()[0]

    requests_count = conn.execute(
        "SELECT COUNT(*) FROM requests"
    ).fetchone()[0]

    inventory = conn.execute(
        "SELECT SUM(units) FROM inventory"
    ).fetchone()[0] or 0

    pending = conn.execute(
        "SELECT COUNT(*) FROM requests WHERE status='Pending'"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        donors=donors,
        requests_count=requests_count,
        inventory=inventory,
        pending=pending
    )


@app.route("/donors")
@login_required
def donors():
    conn = get_db()
    donor_list = conn.execute(
        "SELECT * FROM donors ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template("donors.html", donors=donor_list)


@app.route("/register", methods=["GET", "POST"])
def register_donor():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age = request.form.get("age", type=int)
        gender = request.form.get("gender", "")
        blood_group = request.form.get("blood_group", "")
        phone = request.form.get("phone", "").strip()
        location = request.form.get("location", "").strip()

        valid_groups = list(COMPATIBLE_DONORS.keys())

        if not name or not age or age < 18 or age > 65:
            flash("Please enter a valid donor age (18-65).")
            return render_template("register_donor.html")

        if blood_group not in valid_groups or not phone or not location:
            flash("Please provide valid registration details.")
            return render_template("register_donor.html")

        conn = get_db()
        conn.execute("""
            INSERT INTO donors
            (name, age, gender, blood_group, phone, location)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, age, gender, blood_group, phone, location))

        conn.commit()
        conn.close()

        flash("Donor registered successfully!")
        return redirect(url_for("register_donor"))

    return render_template("register_donor.html")


@app.route("/delete_donor/<int:donor_id>")
@login_required
def delete_donor(donor_id):
    conn = get_db()
    conn.execute("DELETE FROM donors WHERE id=?", (donor_id,))
    conn.commit()
    conn.close()

    flash("Donor deleted successfully!")
    return redirect(url_for("donors"))


@app.route("/requests", methods=["GET", "POST"])
@login_required
def requests_page():
    conn = get_db()

    if request.method == "POST":
        patient = request.form.get("patient_name", "").strip()
        blood_group = request.form.get("blood_group", "")
        units = request.form.get("units", type=int)
        location = request.form.get("location", "").strip()

        if (
            not patient or blood_group not in COMPATIBLE_DONORS
            or not units or units < 1 or units > 100
            or not location
        ):
            flash("Please enter valid blood request details.")
        else:
            conn.execute("""
                INSERT INTO requests
                (patient_name, blood_group, units, location)
                VALUES (?, ?, ?, ?)
            """, (patient, blood_group, units, location))

            conn.commit()
            flash("Blood request submitted successfully!")

    request_list = conn.execute(
        "SELECT * FROM requests ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template("requests.html", requests=request_list)


@app.route("/match/<int:request_id>")
@login_required
def match_donors(request_id):
    conn = get_db()

    blood_request = conn.execute(
        "SELECT * FROM requests WHERE id=?",
        (request_id,)
    ).fetchone()

    if blood_request is None:
        conn.close()
        flash("Request not found.")
        return redirect(url_for("requests_page"))

    compatible_groups = COMPATIBLE_DONORS[blood_request["blood_group"]]

    placeholders = ",".join("?" for _ in compatible_groups)

    matched_donors = conn.execute(
        f"""
        SELECT * FROM donors
        WHERE blood_group IN ({placeholders})
        ORDER BY
        CASE WHEN LOWER(location)=LOWER(?) THEN 0 ELSE 1 END,
        age ASC
        """,
        (*compatible_groups, blood_request["location"])
    ).fetchall()

    conn.close()

    return render_template(
        "donors.html",
        donors=matched_donors,
        matching=True,
        request_id=request_id
    )


@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory_page():
    conn = get_db()

    if request.method == "POST":
        blood_group = request.form.get("blood_group", "")
        units = request.form.get("units", type=int)

        if blood_group not in COMPATIBLE_DONORS or units is None or units < 0 or units > 10000:
            flash("Please enter valid inventory details.")
        else:
            conn.execute(
                "UPDATE inventory SET units=? WHERE blood_group=?",
                (units, blood_group)
            )
            conn.commit()
            flash("Inventory updated successfully!")

    inventory_list = conn.execute(
        "SELECT * FROM inventory ORDER BY blood_group"
    ).fetchall()

    conn.close()

    return render_template(
        "inventory.html",
        inventory=inventory_list
    )


@app.route("/update_status/<int:request_id>/<status>")
@login_required
def update_status(request_id, status):
    if status not in ["Approved", "Rejected"]:
        flash("Invalid status.")
        return redirect(url_for("requests_page"))

    conn = get_db()

    conn.execute(
        "UPDATE requests SET status=? WHERE id=?",
        (status, request_id)
    )

    conn.commit()
    conn.close()

    flash("Request status updated.")
    return redirect(url_for("requests_page"))


if __name__ == "__main__":
    app.run(debug=True)