from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import qrcode
import os
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)
app.secret_key = "eventmanagement"


# Database Connection
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# Create Database Table
def create_table():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        venue TEXT NOT NULL
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS participants(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        event_id INTEGER
    )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return redirect("/login")


# Dashboard
@app.route("/dashboard")
def dashboard():

    conn = get_db()

    events = conn.execute("SELECT * FROM events").fetchall()

    participant_count = conn.execute("SELECT COUNT(*) FROM participants").fetchone()[0]

    conn.close()

    return render_template(
        "index.html", events=events, participant_count=participant_count
    )


# loginpage
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            return redirect("/dashboard")

        return "Invalid Username or Password"

    return render_template("login.html")


# register page
@app.route("/register/<int:event_id>", methods=["GET", "POST"])
def register(event_id):

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]

        conn = get_db()

        conn.execute(
            """
            INSERT INTO participants
            (name,email,phone,event_id)
            VALUES(?,?,?,?)
            """,
            (name, email, phone, event_id),
        )

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("register.html", event_id=event_id)


# Participants


@app.route("/participants")
def participants():

    conn = get_db()

    data = conn.execute("""
    SELECT participants.*,
           events.name AS event_name
    FROM participants
    JOIN events
    ON participants.event_id = events.id
    """).fetchall()

    conn.close()

    return render_template("participants.html", participants=data)


# Add Event
@app.route("/add", methods=["GET", "POST"])
def add_event():

    if request.method == "POST":

        name = request.form["name"]
        date = request.form["date"]
        venue = request.form["venue"]

        conn = get_db()

        conn.execute(
            """
            INSERT INTO events(name,date,venue)
            VALUES(?,?,?)
            """,
            (name, date, venue),
        )

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_event.html")


# Edit Event
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_event(id):

    conn = get_db()

    event = conn.execute("SELECT * FROM events WHERE id=?", (id,)).fetchone()

    if request.method == "POST":

        name = request.form["name"]
        date = request.form["date"]
        venue = request.form["venue"]

        conn.execute(
            """
            UPDATE events
            SET name=?, date=?, venue=?
            WHERE id=?
            """,
            (name, date, venue, id),
        )

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    conn.close()

    return render_template("edit_event.html", event=event)


# Delete Event
@app.route("/delete/<int:id>")
def delete_event(id):

    conn = get_db()

    conn.execute("DELETE FROM events WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# repots
# Reports Page
@app.route("/reports")
def reports():

    conn = get_db()

    total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    total_participants = conn.execute("SELECT COUNT(*) FROM participants").fetchone()[0]

    event_wise = conn.execute("""
    SELECT events.name,
           COUNT(participants.id) as total
    FROM events
    LEFT JOIN participants
    ON events.id = participants.event_id
    GROUP BY events.id
    """).fetchall()

    conn.close()

    return render_template(
        "reports.html",
        total_events=total_events,
        total_participants=total_participants,
        event_wise=event_wise,
    )


# certificate
# Certificate Generation
@app.route("/certificate/<int:id>")
def certificate(id):

    conn = get_db()

    participant = conn.execute(
        """
    SELECT participants.name,
           events.name AS event_name
    FROM participants
    JOIN events
    ON participants.event_id = events.id
    WHERE participants.id=?
    """,
        (id,),
    ).fetchone()

    conn.close()

    if not participant:
        return "Participant Not Found"

    # Generate QR Code
    qr = qrcode.make(
        f"Participant: {participant['name']} | Event: {participant['event_name']}"
    )

    qr_path = os.path.join(os.getcwd(), "qr.png")
    qr.save(qr_path)
    # PDF File Name
    pdf_name = f"certificate_{id}.pdf"

    # Create PDF
    c = canvas.Canvas(pdf_name)

    # Gold Border
    c.setLineWidth(5)
    c.rect(30, 30, 540, 760)
    # College Logo
    # c.drawImage("logo.png", 40, 680, width=80, height=80)
    # Title
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(300, 730, "CERTIFICATE OF PARTICIPATION")

    # Subtitle
    c.setFont("Helvetica", 16)
    c.drawCentredString(300, 670, "This Certificate is Proudly Presented To")

    # Participant Name
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(300, 620, participant["name"])

    # Description
    c.setFont("Helvetica", 16)
    c.drawCentredString(300, 570, f"For Successfully Participating In")

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(300, 540, participant["event_name"])

    # Date
    today = datetime.now().strftime("%d-%m-%Y")
    c.drawString(60, 180, f"Date: {today}")

    # Coordinator Signature
    c.line(70, 120, 180, 120)
    c.drawString(90, 100, "Coordinator")

    # Principal Signature
    c.line(400, 120, 510, 120)
    c.drawString(430, 100, "Principal")

    # QR Code
    c.drawImage(qr_path, 450, 180, width=90, height=90)
    
    # Verification Text
    c.setFont("Helvetica", 8)
    c.drawString(430, 170, "Scan For Verification")

    c.save()
    if os.path.exists(qr_path):
        os.remove(qr_path)

    return send_file(pdf_name, as_attachment=True)
    # PDF code here...


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
 
