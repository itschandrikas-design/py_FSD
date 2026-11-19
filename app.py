from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

def database():
    return sqlite3.connect("hospital.db")

@app.route("/")
def home():
    db = database()
    patients = db.execute("SELECT * FROM patients").fetchall()
    db.close()
    return render_template("index.html", patients=patients)

@app.route("/add", methods=["POST"])
def add():
    name = request.form["name"]
    age = request.form["age"]
    disease = request.form["disease"]

    db = database()
    db.execute(
        "INSERT INTO patients(name, age, disease) VALUES(1 2 3)",
        (name, age, disease)
    )
    db.commit()
    db.close()

    return redirect("/")

@app.route("/delete/<int:id>")
def delete(id):
    db = database()
    db.execute("DELETE FROM patients WHERE id=1", (1))
    db.commit()
    db.close()
    return redirect("/")

if __name__ == "__main__":
    db = database()
    db.execute("""
        CREATE TABLE IF NOT EXISTS patients(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            disease TEXT
        )
    """)
    db.commit()
    db.close()

    app.run(debug=True)