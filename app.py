from flask import Flask, render_template, request, redirect, session
import os
import psycopg2
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")

DATABASE_URL = os.environ.get("DATABASE_URL")

# ---------------- SAFE DB CONNECTION ----------------
def db():
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL)

# ---------------- INIT DB (SAFE) ----------------
def init_db():
    if not DATABASE_URL:
        print("No DATABASE_URL found, skipping DB init")
        return

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS websites (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        url TEXT,
        status TEXT DEFAULT 'UNKNOWN'
    )
    """)

    conn.commit()
    conn.close()

# run only if DB exists
init_db()

# ---------------- ROUTES ----------------
@app.route("/")
def login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    if not DATABASE_URL:
        return "Database not configured"

    u = request.form["user"]
    p = request.form["password"]

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, role FROM users WHERE username=%s AND password=%s", (u, p))
    user = cur.fetchone()
    conn.close()

    if user:
        session["user_id"] = user[0]
        session["role"] = user[1]
        return redirect("/admin" if user[1] == "admin" else "/client")

    return "Invalid login"


@app.route("/admin")
def admin():
    if not DATABASE_URL:
        return "Database not configured"

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM websites")
    data = cur.fetchall()
    conn.close()
    return render_template("admin.html", sites=data)


@app.route("/client")
def client():
    if not DATABASE_URL:
        return "Database not configured"

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM websites WHERE user_id=%s", (session.get("user_id"),))
    data = cur.fetchall()
    conn.close()
    return render_template("client.html", sites=data)


@app.route("/add", methods=["POST"])
def add():
    if not DATABASE_URL:
        return "Database not configured"

    url = request.form["url"]

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO websites (user_id, url) VALUES (%s,%s)",
        (session.get("user_id"), url)
    )
    conn.commit()
    conn.close()

    return redirect("/admin")


@app.route("/scan")
def scan():
    if not DATABASE_URL:
        return "Database not configured"

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id, url FROM websites")
    sites = cur.fetchall()

    for s in sites:
        try:
            r = requests.get(s[1], timeout=3)
            status = "UP" if r.status_code == 200 else "DOWN"
        except:
            status = "DOWN"

        cur.execute("UPDATE websites SET status=%s WHERE id=%s", (status, s[0]))

    conn.commit()
    conn.close()

    return redirect("/admin")


if __name__ == "__main__":
    app.run()
