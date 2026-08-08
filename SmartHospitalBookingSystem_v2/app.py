from re import search
import token
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import qrcode
import os
from flask import jsonify
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import os

print("=" * 60)
print("RUNNING APP FROM:")
print(os.path.abspath(__file__))
print("=" * 60)
app = Flask(__name__)
app.config.from_object(Config)

# Secret Key (Required for Sessions)
app.secret_key = "ehealth_bhutan_secret_key_2026"

mysql = MySQL(app)

# ================= HOME ================= #

@app.route("/")
def home():
    return render_template("index.html")

# ================= ABOUT ================= #

@app.route("/about")
def about():
    return render_template("about.html")


# ================= SERVICES ================= #

@app.route("/services")
def services():
    return render_template("services.html")


# ================= CONTACT ================= #

@app.route("/contact")
def contact():
    return render_template("contact.html")

# ================= LOGIN REDIRECT ================= #

@app.route("/login")
def login():
    return redirect("/patient/login")


# ================= PATIENT REGISTER PAGE ================= #

@app.route("/patient/register", methods=["GET"])
def patient_register():
    return render_template("patient/patient_register.html")


# ================= REGISTER PATIENT ================= #

@app.route("/patient/register", methods=["GET", "POST"])
def register_patient():

    if request.method == "GET":
        return render_template("patient/patient_register.html")

    # POST starts here

    cid = request.form["cid"]
    fullname = request.form["fullname"]

    first_name = fullname.split()[0]
    last_name = " ".join(fullname.split()[1:])

    dob = request.form["dob"]
    gender = request.form["gender"]
    blood = request.form["blood_group"]

    nationality = "Bhutanese"

    dzongkhag = request.form["dzongkhag"]
    gewog = request.form["gewog"]
    village = request.form["village"]

    phone = request.form["phone"]
    email = request.form["email"]

    username = request.form["username"]

    password = generate_password_hash(request.form["password"])

    guardian = request.form["guardian_name"]
    guardian_phone = request.form["guardian_phone"]

    cur = mysql.connection.cursor()

    # Duplicate CID
    cur.execute(
        "SELECT patient_id FROM patients WHERE cid_number=%s",
        (cid,)
    )

    if cur.fetchone():

        flash("CID Number already exists.", "danger")
        cur.close()
        return redirect("/patient/register")

    # Duplicate Username
    cur.execute(
        "SELECT patient_id FROM patients WHERE username=%s",
        (username,)
    )

    if cur.fetchone():

        flash("Username already exists.", "danger")
        cur.close()
        return redirect("/patient/register")

    sql = """
    INSERT INTO patients
    (
        cid_number,
        first_name,
        last_name,
        gender,
        date_of_birth,
        blood_group,
        nationality,
        phone,
        email,
        username,
        dzongkhag,
        gewog,
        village,
        emergency_contact_name,
        emergency_contact_phone,
        password
    )

    VALUES

    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    values = (

        cid,
        first_name,
        last_name,
        gender,
        dob,
        blood,
        nationality,
        phone,
        email,
        username,
        dzongkhag,
        gewog,
        village,
        guardian,
        guardian_phone,
        password

    )

    cur.execute(sql, values)

    mysql.connection.commit()

    cur.close()

    flash("Registration Successful! Please Login.", "success")

    return redirect("/patient/login")

# ================= PATIENT LOGIN ================= #
@app.route("/patient/login", methods=["GET", "POST"])
def patient_login():

    if request.method == "GET":
        return render_template("patient/patient_login.html")

    email = request.form["email"]
    password = request.form["password"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            patient_id,
            first_name,
            email,
            password
        FROM patients
        WHERE email=%s
    """, (email,))

    patient = cur.fetchone()

    cur.close()

    if patient:

        if check_password_hash(patient[3], password):

            session["patient_id"] = patient[0]
            session["patient_name"] = patient[1]

            flash("Welcome Back!", "success")

            return redirect("/patient/dashboard")

    flash("Invalid Email or Password.", "danger")

    return redirect("/patient/login")

# ================= PATIENT DASHBOARD ================= #

@app.route("/patient/dashboard")
def patient_dashboard():

    if "patient_id" not in session:

        flash("Please login first.", "warning")

        return redirect("/patient/login")

    return render_template(
        "patient/dashboard.html",
        patient=session["patient_name"]
    )


# ================= LOGOUT ================= #
@app.route("/logout")
def logout():

    session.clear()

    flash("Logged Out Successfully.", "success")

    return redirect("/")


# ================= BOOK APPOINTMENT ================= #

@app.route("/patient/book", methods=["GET", "POST"])
def patient_book():

    if "patient_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/patient/login")

    cur = mysql.connection.cursor()

    # ---------------- GET ----------------

    if request.method == "GET":

        cur.execute("""
            SELECT hospital_id, hospital_name
            FROM hospitals
            WHERE status='Active'
            ORDER BY hospital_name
        """)

        hospitals = cur.fetchall()

        cur.close()

        return render_template(
            "patient/book.html",
            hospitals=hospitals
        )

    # ---------------- POST ----------------

    patient_id = session["patient_id"]

    hospital_id = request.form["hospital_id"]
    department_id = request.form["department_id"]
    doctor_id = request.form["doctor_id"]
    schedule_id = request.form["schedule_id"]
    appointment_type = request.form["appointment_type"]

    # Get Schedule Details

    cur.execute("""
        SELECT
            available_date,
            start_time,
            available_tokens
        FROM doctor_schedule
        WHERE schedule_id=%s
    """, (schedule_id,))

    schedule = cur.fetchone()

    if schedule is None:

        cur.close()

        flash("Invalid Schedule.", "danger")

        return redirect("/patient/book")

    appointment_date = schedule[0]
    appointment_time = schedule[1]
    available_tokens = schedule[2]

    if available_tokens <= 0:

        cur.close()

        flash("No Tokens Available.", "danger")

        return redirect("/patient/book")

    # ---------------- Insert Appointment ----------------

    cur.execute("""
        INSERT INTO appointments
        (
            patient_id,
            doctor_id,
            hospital_id,
            department_id,
            schedule_id,
            appointment_date,
            appointment_time,
            appointment_type,
            status
        )
        VALUES
        (
            %s,%s,%s,%s,%s,%s,%s,%s,'Booked'
        )
    """, (
        patient_id,
        doctor_id,
        hospital_id,
        department_id,
        schedule_id,
        appointment_date,
        appointment_time,
        appointment_type
    ))

    # Get Newly Created Appointment ID

    appointment_id = cur.lastrowid

    # ---------------- Reduce Available Tokens ----------------

    cur.execute("""
        UPDATE doctor_schedule
        SET available_tokens = available_tokens - 1
        WHERE schedule_id=%s
    """, (schedule_id,))

    # ---------------- Check Remaining Tokens ----------------

    cur.execute("""
        SELECT available_tokens
        FROM doctor_schedule
        WHERE schedule_id=%s
    """, (schedule_id,))

    remaining = cur.fetchone()[0]

    if remaining == 0:

        cur.execute("""
            UPDATE doctor_schedule
            SET status='Full'
            WHERE schedule_id=%s
        """, (schedule_id,))

    # ---------------- Commit Database ----------------

    mysql.connection.commit()

    # ---------------- Generate QR Code ----------------

    qr_data = f"""
Appointment ID : {appointment_id}
Patient ID : {patient_id}
Doctor ID : {doctor_id}
Hospital ID : {hospital_id}
Date : {appointment_date}
Time : {appointment_time}
"""

    folder = os.path.join(app.root_path, "static", "qr_codes")
    os.makedirs(folder, exist_ok=True)

    filename = f"appointment_{appointment_id}.png"

    filepath = os.path.join(folder, filename)

    img = qrcode.make(qr_data)

    img.save(filepath)

    print("=" * 50)
    print("QR Generated Successfully!")
    print("Saved To:", filepath)
    print("=" * 50)

    cur.close()

    flash("Appointment Booked Successfully!", "success")

    return redirect("/patient/my_appointments")

# ================= CONFIRM BOOKING ================= #

@app.route("/patient/confirm_booking", methods=["POST"])
def confirm_booking():
    print("CONFIRM BOOKING ROUTE HIT")

    if "patient_id" not in session:

        flash("Please login first.", "warning")
        return redirect("/patient/login")

    patient_id = session["patient_id"]

    hospital_id = session["hospital_id"]
    department_id = session["department_id"]
    doctor_id = session["doctor_id"]
    appointment_type = session["appointment_type"]

    schedule_id = request.form["schedule_id"]

    print("===================================")
    print("FORM DATA:", request.form)
    print("Schedule ID:", schedule_id)
    print("Patient ID:", patient_id)
    print("Doctor ID:", doctor_id)
    print("===================================")
     
    cur = mysql.connection.cursor()

    # Get selected schedule
    cur.execute("""
        SELECT
            available_date,
            start_time,
            available_tokens
        FROM doctor_schedule
        WHERE schedule_id=%s
    """, (schedule_id,))

    schedule = cur.fetchone()

    if not schedule:

        flash("Schedule not found.", "danger")
        cur.close()
        return redirect("/patient/book")

    appointment_date = schedule[0]
    appointment_time = schedule[1]
    available_tokens = schedule[2]

    if available_tokens <= 0:

        flash("No Tokens Available.", "danger")
        cur.close()
        return redirect("/patient/book")

    # Save appointment
    cur.execute("""
        INSERT INTO appointments
        (
            patient_id,
            doctor_id,
            hospital_id,
            department_id,
            schedule_id,
            appointment_date,
            appointment_time,
            appointment_type,
            status
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (

        patient_id,
        doctor_id,
        hospital_id,
        department_id,
        schedule_id,
        appointment_date,
        appointment_time,
        appointment_type,
        "Booked"

    ))

    print("Rows inserted:", cur.rowcount)
    print("Last Row ID:", cur.lastrowid)

      # Get Appointment ID
    appointment_id = cur.lastrowid

    # ---------- Generate QR Code ----------

    qr_data = f"""
Appointment ID : {appointment_id}
Patient ID : {patient_id}
Doctor ID : {doctor_id}
Hospital ID : {hospital_id}
Date : {appointment_date}
Time : {appointment_time}
"""

    # Create QR Code folder if it doesn't exist
    folder = os.path.join(app.root_path, "static", "qr_codes")
    os.makedirs(folder, exist_ok=True)

    # QR filename
    filename = f"appointment_{appointment_id}.png"

    # Full path
    filepath = os.path.join(folder, filename)

    # Generate QR
    img = qrcode.make(qr_data)

    # Save QR
    img.save(filepath)

    print("=" * 50)
    print("QR Generated Successfully!")
    print("Saved To:", filepath)
    print("=" * 50)

    # Reduce Token
    cur.execute("""
        UPDATE doctor_schedule
        SET available_tokens = available_tokens - 1
        WHERE schedule_id=%s
    """, (schedule_id,))

    cur.execute("""
        UPDATE doctor_schedule
        SET status='Full'
        WHERE schedule_id=%s
        AND available_tokens <= 0
    """, (schedule_id,))

    print("Rows updated:", cur.rowcount)

    mysql.connection.commit()

    cur.close()

    flash("Appointment Booked Successfully!", "success")

    return redirect(f"/patient/appointment/{appointment_id}")

# ================= MY APPOINTMENTS ================= #

@app.route("/patient/my_appointments")
def my_appointments():

    if "patient_id" not in session:

        flash("Please login first.", "warning")
        return redirect("/patient/login")

    patient_id = session["patient_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT

            a.appointment_id,

            h.hospital_name,

            dep.department_name,

            d.doctor_name,

            a.appointment_date,

            a.appointment_time,

            a.appointment_type,

            a.status

        FROM appointments a

        JOIN hospitals h
        ON a.hospital_id=h.hospital_id

        JOIN departments dep
        ON a.department_id=dep.department_id

        JOIN doctors d
        ON a.doctor_id=d.doctor_id

        WHERE a.patient_id=%s

        ORDER BY
        a.appointment_date DESC,
        a.appointment_time DESC

    """,(patient_id,))

    appointments = cur.fetchall()

    cur.close()

    return render_template(
        "patient/my_appointments.html",
        appointments=appointments
    )

@app.route("/patient/token")
def queue_token():

    if "patient_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/patient/login")

    patient_id = session["patient_id"]

    cur = mysql.connection.cursor()

    # Always get the latest appointment
    cur.execute("""
        SELECT
            a.appointment_id,
            h.hospital_name,
            dep.department_name,
            d.doctor_name,
            a.doctor_id,
            a.appointment_date,
            a.appointment_time,
            a.status

        FROM appointments a

        JOIN hospitals h
            ON a.hospital_id = h.hospital_id

        JOIN departments dep
            ON a.department_id = dep.department_id

        JOIN doctors d
            ON a.doctor_id = d.doctor_id

        WHERE a.patient_id = %s

        ORDER BY a.appointment_id DESC

        LIMIT 1
    """, (patient_id,))

    token = cur.fetchone()

    if token:

        doctor_id = token[4]
        appointment_date = token[5]
        appointment_time = token[6]

        # Patients ahead in queue
        cur.execute("""
            SELECT COUNT(*)

            FROM appointments

            WHERE doctor_id=%s
            AND appointment_date=%s
            AND appointment_time < %s
            AND status IN ('Booked','Pending','Confirmed')
        """, (
            doctor_id,
            appointment_date,
            appointment_time
        ))

        patients_ahead = cur.fetchone()[0]

        queue_position = patients_ahead + 1

        waiting_time = patients_ahead * 15

    else:

        queue_position = None
        waiting_time = None

    cur.close()

    return render_template(
        "patient/queue_token.html",
        token=token,
        queue_position=queue_position,
        waiting_time=waiting_time
    )

@app.route("/patient/cancel_appointment/<int:appointment_id>")
def cancel_appointment(appointment_id):

    if "patient_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/patient/login")

    patient_id = session["patient_id"]

    cur = mysql.connection.cursor()

    # Verify appointment belongs to patient
    cur.execute("""
        SELECT
            schedule_id,
            status
        FROM appointments
        WHERE appointment_id=%s
        AND patient_id=%s
    """, (appointment_id, patient_id))

    appointment = cur.fetchone()

    if appointment is None:

        cur.close()

        flash("Appointment not found.", "danger")

        return redirect("/patient/my_appointments")

    schedule_id = appointment[0]
    status = appointment[1]

    if status == "Cancelled":

        cur.close()

        flash("Appointment already cancelled.", "warning")

        return redirect("/patient/my_appointments")

    if status == "Completed":

        cur.close()

        flash("Completed appointments cannot be cancelled.", "danger")

        return redirect("/patient/my_appointments")

    # Cancel appointment
    cur.execute("""
        UPDATE appointments
        SET status='Cancelled'
        WHERE appointment_id=%s
    """, (appointment_id,))

    # Return one token
    cur.execute("""
        UPDATE doctor_schedule
        SET available_tokens = available_tokens + 1
        WHERE schedule_id=%s
    """, (schedule_id,))

    # Reopen schedule if it was Full
    cur.execute("""
        UPDATE doctor_schedule
        SET status='Available'
        WHERE schedule_id=%s
        AND status='Full'
    """, (schedule_id,))

    mysql.connection.commit()

    cur.close()

    flash("Appointment Cancelled Successfully.", "success")

    return redirect("/patient/my_appointments")

# ================= APPOINTMENT SUCCESS ================= #

@app.route("/patient/appointment/<int:appointment_id>")
def appointment_success(appointment_id):

    if "patient_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/patient/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            a.appointment_id,
            CONCAT(p.first_name,' ',p.last_name),
            h.hospital_name,
            d.department_name,
            doc.doctor_name,
            a.appointment_date,
            a.appointment_time,
            a.appointment_type,
            a.status
        FROM appointments a
        JOIN patients p
            ON a.patient_id = p.patient_id
        JOIN hospitals h
            ON a.hospital_id = h.hospital_id
        JOIN departments d
            ON a.department_id = d.department_id
        JOIN doctors doc
            ON a.doctor_id = doc.doctor_id
        WHERE a.appointment_id=%s
    """, (appointment_id,))

    appointment = cur.fetchone()

    cur.close()

    return render_template(
        "patient/view_appointment.html",
        appointment=appointment,
        qr_image=f"qr_codes/appointment_{appointment_id}.png"
    )

# ================= DOCTOR LOGIN ================= #

@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():

    if request.method == "GET":
        return render_template("doctor/doctor_login.html")

    email = request.form["email"]
    password = request.form["password"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            doctor_id,
            doctor_name,
            email,
            password
        FROM doctors
        WHERE email=%s
    """, (email,))

    doctor = cur.fetchone()

    print("=" * 50)
    print("Entered Email:", email)
    print("Entered Password:", password)
    print("Doctor Record:", doctor)
    print("=" * 50)

    cur.close()

    if doctor:

        print("Stored Password:", doctor[3])

        try:
            result = check_password_hash(doctor[3], password)
            print("Password Check:", result)
        except Exception as e:
            print("Password Hash Error:", e)
            result = False

        if result:

            session["doctor_id"] = doctor[0]
            session["doctor_name"] = doctor[1]

            flash("Welcome Doctor!", "success")

            return redirect("/doctor/dashboard")

    flash("Invalid Email or Password", "danger")

    return redirect("/doctor/login")

# ================= DOCTOR DASHBOARD ================= #

@app.route("/doctor/dashboard")
def doctor_dashboard():

    if "doctor_id" not in session:

        return redirect("/doctor/login")

    return render_template(
        "doctor/dashboard.html",
        doctor=session["doctor_name"]
    )
    
@app.route("/doctor/today_appointments")
def doctor_today_appointments():

    if "doctor_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/doctor/login")

    doctor_id = session["doctor_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            a.appointment_id,
            CONCAT(p.first_name,' ',p.last_name),
            dep.department_name,
            a.appointment_date,
            a.appointment_time,
            a.appointment_type,
            a.status

        FROM appointments a

        JOIN patients p
            ON a.patient_id = p.patient_id

        JOIN departments dep
            ON a.department_id = dep.department_id

        WHERE a.doctor_id=%s

        ORDER BY
            a.appointment_date,
            a.appointment_time
    """, (doctor_id,))

    appointments = cur.fetchall()

    cur.close()

    return render_template(
        "doctor/today_appointments.html",
        appointments=appointments
    )

@app.route("/doctor/view_patient/<int:id>")
def view_patient(id):

    if "doctor_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/doctor/login")

    cur = mysql.connection.cursor()

    cur.execute("""
SELECT
    a.appointment_id,

    CONCAT(p.first_name,' ',p.last_name),

    p.gender,
    p.date_of_birth,
    p.cid_number,
    p.phone,
    p.email,
    p.blood_group,
    p.nationality,

    CONCAT(
        p.dzongkhag,
        ', ',
        p.gewog,
        ', ',
        p.village
    ) AS address,

    h.hospital_name,
    dep.department_name,
    d.doctor_name,
    d.specialization,

    a.appointment_date,
    a.appointment_time,
    a.appointment_type,
    a.status,
    a.remarks

FROM appointments a

JOIN patients p
ON a.patient_id = p.patient_id

JOIN hospitals h
ON a.hospital_id = h.hospital_id

JOIN departments dep
ON a.department_id = dep.department_id

JOIN doctors d
ON a.doctor_id = d.doctor_id

WHERE a.appointment_id=%s
""",(id,))

    appointment = cur.fetchone()

    cur.close()

    return render_template(
        "doctor/view_patient.html",
        appointment=appointment
    )

@app.route("/doctor/add_record/<int:id>")
def add_record(id):

    if "doctor_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/doctor/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            a.appointment_id,
            CONCAT(p.first_name,' ',p.last_name)

        FROM appointments a

        JOIN patients p
        ON a.patient_id=p.patient_id

        WHERE a.appointment_id=%s
    """, (id,))

    appointment = cur.fetchone()

    cur.close()

    return render_template(
        "doctor/add_record.html",
        appointment=appointment
    )

@app.route("/doctor/save_record", methods=["POST"])
def save_record():

    if "doctor_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/doctor/login")

    appointment_id = request.form["appointment_id"]
    diagnosis = request.form["diagnosis"]
    prescription = request.form["prescription"]
    doctor_notes = request.form["doctor_notes"]

    doctor_id = session["doctor_id"]

    cur = mysql.connection.cursor()

    # Get patient id
    cur.execute("""
        SELECT patient_id
        FROM appointments
        WHERE appointment_id=%s
    """, (appointment_id,))

    patient_id = cur.fetchone()[0]

    # Save record
    cur.execute("""
        INSERT INTO medical_records
        (
            appointment_id,
            patient_id,
            doctor_id,
            diagnosis,
            prescription,
            doctor_notes
        )
        VALUES
        (%s,%s,%s,%s,%s,%s)
    """, (
        appointment_id,
        patient_id,
        doctor_id,
        diagnosis,
        prescription,
        doctor_notes
    ))

    # Mark appointment completed
    cur.execute("""
        UPDATE appointments
        SET status='Completed'
        WHERE appointment_id=%s
    """, (appointment_id,))

    mysql.connection.commit()

    cur.close()

    flash("Medical Record Saved Successfully!", "success")

    return redirect("/doctor/today_appointments")

@app.route("/patient/medical_records")
def patient_medical_records():

    print("PATIENT MEDICAL RECORDS ROUTE HIT")

    if "patient_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/patient/login")

    patient_id = session["patient_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT

            mr.record_id,

            a.appointment_date,

            d.doctor_name,

            h.hospital_name,

            mr.diagnosis,

            mr.prescription

        FROM medical_records mr

        JOIN appointments a
            ON mr.appointment_id = a.appointment_id

        JOIN doctors d
            ON mr.doctor_id = d.doctor_id

        JOIN hospitals h
            ON a.hospital_id = h.hospital_id

        WHERE mr.patient_id=%s

        ORDER BY mr.created_at DESC
    """, (patient_id,))

    records = cur.fetchall()

    print("=" * 50)
    print("Medical Records:")
    print(records)
    print("=" * 50)

    cur.close()

    return render_template(
        "patient/medical_records.html",
        records=records
    )

@app.route("/patient/record/<int:id>")
def patient_view_record(id):

    if "patient_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/patient/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT

            a.appointment_date,

            d.doctor_name,

            h.hospital_name,

            mr.diagnosis,

            mr.prescription,

            mr.doctor_notes

        FROM medical_records mr

        JOIN appointments a
            ON mr.appointment_id = a.appointment_id

        JOIN doctors d
            ON mr.doctor_id = d.doctor_id

        JOIN hospitals h
            ON a.hospital_id = h.hospital_id

        WHERE mr.record_id=%s
    """, (id,))

    record = cur.fetchone()

    cur.close()

    return render_template(
        "patient/view_record.html",
        record=record
    )

@app.route("/doctor/add_record/<int:id>")
def doctor_add_record(id):

    if "doctor_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/doctor/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            a.appointment_id,
            CONCAT(p.first_name,' ',p.last_name)

        FROM appointments a

        JOIN patients p
        ON a.patient_id=p.patient_id

        WHERE a.appointment_id=%s
    """, (id,))

    appointment = cur.fetchone()

    cur.close()

    return render_template(
        "doctor/add_record.html",
        appointment=appointment
    )

@app.route("/doctor/confirm/<int:id>")
def doctor_confirm(id):

    if "doctor_id" not in session:
        return redirect("/doctor/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE appointments
        SET status='Confirmed'
        WHERE appointment_id=%s
    """, (id,))

    mysql.connection.commit()

    cur.close()

    flash("Appointment Confirmed Successfully!", "success")

    return redirect("/doctor/today_appointments")

@app.route("/doctor/complete/<int:id>")
def doctor_complete(id):

    if "doctor_id" not in session:
        return redirect("/doctor/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE appointments
        SET status='Completed'
        WHERE appointment_id=%s
    """, (id,))

    mysql.connection.commit()

    cur.close()

    flash("Appointment Completed!", "success")

    return redirect("/doctor/today_appointments")

@app.route("/doctor/cancel/<int:id>")
def doctor_cancel(id):

    if "doctor_id" not in session:
        return redirect("/doctor/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE appointments
        SET status='Cancelled'
        WHERE appointment_id=%s
    """, (id,))

    mysql.connection.commit()

    cur.close()

    flash("Appointment Cancelled!", "danger")

    return redirect("/doctor/today_appointments")

@app.route("/doctor/schedule")
def doctor_schedule():

    if "doctor_id" not in session:
        return redirect("/doctor/login")

    doctor_id = session["doctor_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
    SELECT
        schedule_id,
        available_date,
        start_time,
        end_time,
        appointment_type,
        available_tokens
    FROM doctor_schedule
    WHERE doctor_id=%s
    AND status='Available'
    ORDER BY available_date
""", (doctor_id,))

    schedules = cur.fetchall()

    cur.close()

    return render_template(
        "doctor/schedule.html",
        schedules=schedules
    )

@app.route("/doctor/add_schedule", methods=["POST"])
def add_schedule():

    if "doctor_id" not in session:
        return redirect("/doctor/login")

    doctor_id = session["doctor_id"]

    available_date = request.form["available_date"]
    start_time = request.form["start_time"]
    end_time = request.form["end_time"]
    appointment_type = request.form["appointment_type"]
    available_tokens = request.form["available_tokens"]

    cur = mysql.connection.cursor()

    # Get doctor's hospital and department
    cur.execute("""
        SELECT hospital_id, department_id
        FROM doctors
        WHERE doctor_id=%s
    """, (doctor_id,))

    doctor = cur.fetchone()

    if doctor is None:
        flash("Doctor not found!", "danger")
        cur.close()
        return redirect("/doctor/schedule")

    hospital_id = doctor[0]
    department_id = doctor[1]

    # Insert schedule
    cur.execute("""
INSERT INTO doctor_schedule
(
    doctor_id,
    hospital_id,
    department_id,
    available_date,
    start_time,
    end_time,
    max_tokens,
    available_tokens,
    appointment_type
)
VALUES
(%s,%s,%s,%s,%s,%s,%s,%s,%s)
""", (
    doctor_id,
    hospital_id,
    department_id,
    available_date,
    start_time,
    end_time,
    available_tokens,   # max_tokens
    available_tokens,   # available_tokens
    appointment_type
))
    mysql.connection.commit()

    cur.close()

    flash("Schedule Added Successfully!", "success")

    return redirect("/doctor/schedule")

@app.route("/doctor/delete_schedule/<int:id>")
def delete_schedule(id):

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE doctor_schedule
        SET status='Closed'
        WHERE schedule_id=%s
    """, (id,))

    mysql.connection.commit()

    cur.close()

    flash("Schedule closed successfully!", "success")

    return redirect("/doctor/schedule")

@app.route("/doctor/edit_schedule/<int:id>", methods=["GET", "POST"])
def edit_schedule(id):

    if "doctor_id" not in session:
        return redirect("/doctor/login")

    cur = mysql.connection.cursor()

    if request.method == "POST":

        available_date = request.form["available_date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        appointment_type = request.form["appointment_type"]
        available_tokens = request.form["available_tokens"]

        cur.execute("""
            UPDATE doctor_schedule
            SET
                available_date=%s,
                start_time=%s,
                end_time=%s,
                appointment_type=%s,
                available_tokens=%s
            WHERE schedule_id=%s
        """, (
            available_date,
            start_time,
            end_time,
            appointment_type,
            available_tokens,
            id
        ))

        mysql.connection.commit()
        cur.close()

        flash("Schedule Updated Successfully!", "success")
        return redirect("/doctor/schedule")

    cur.execute("""
        SELECT
            schedule_id,
            available_date,
            start_time,
            end_time,
            appointment_type,
            available_tokens
        FROM doctor_schedule
        WHERE schedule_id=%s
    """, (id,))

    schedule = cur.fetchone()

    cur.close()

    return render_template(
        "doctor/edit_schedule.html",
        schedule=schedule
    )

@app.route("/doctor/confirmed_appointments")
def doctor_confirmed_appointments():

    if "doctor_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/doctor/login")

    doctor_id = session["doctor_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT

            a.appointment_id,

            CONCAT(p.first_name,' ',p.last_name),

            dep.department_name,

            a.appointment_date,

            a.appointment_time,

            a.appointment_type,

            a.status

        FROM appointments a

        JOIN patients p
            ON a.patient_id = p.patient_id

        JOIN departments dep
            ON a.department_id = dep.department_id

        WHERE a.doctor_id=%s
        AND a.status='Booked'

        ORDER BY
        a.appointment_date,
        a.appointment_time
    """, (doctor_id,))

    appointments = cur.fetchall()

    cur.close()

    return render_template(
        "doctor/confirmed_appointments.html",
        appointments=appointments
    )

@app.route("/doctor/completed_appointments")
def doctor_completed_appointments():

    if "doctor_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/doctor/login")

    doctor_id = session["doctor_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT

            a.appointment_id,
            CONCAT(p.first_name,' ',p.last_name),
            dep.department_name,
            a.appointment_date,
            a.appointment_time,
            a.appointment_type,
            a.status

        FROM appointments a

        JOIN patients p
            ON a.patient_id = p.patient_id

        JOIN departments dep
            ON a.department_id = dep.department_id

        WHERE a.doctor_id=%s
        AND a.status='Completed'

        ORDER BY
            a.appointment_date DESC,
            a.appointment_time DESC
    """, (doctor_id,))

    appointments = cur.fetchall()

    cur.close()

    return render_template(
        "doctor/completed_appointments.html",
        appointments=appointments
    )

@app.route("/doctor/cancelled_appointments")
def doctor_cancelled_appointments():

    if "doctor_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/doctor/login")

    doctor_id = session["doctor_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT

            a.appointment_id,
            CONCAT(p.first_name,' ',p.last_name),
            dep.department_name,
            a.appointment_date,
            a.appointment_time,
            a.appointment_type,
            a.status

        FROM appointments a

        JOIN patients p
            ON a.patient_id = p.patient_id

        JOIN departments dep
            ON a.department_id = dep.department_id

        WHERE a.doctor_id=%s
        AND a.status='Cancelled'

        ORDER BY
            a.appointment_date DESC,
            a.appointment_time DESC
    """, (doctor_id,))

    appointments = cur.fetchall()

    cur.close()

    return render_template(
        "doctor/cancelled_appointments.html",
        appointments=appointments
    )

@app.route("/doctor/medical_records")
def doctor_medical_records():

    if "doctor_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/doctor/login")

    doctor_id = session["doctor_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT

            mr.record_id,

            CONCAT(p.first_name,' ',p.last_name),

            h.hospital_name,

            a.appointment_date,

            mr.diagnosis,

            mr.created_at

        FROM medical_records mr

        JOIN patients p
            ON mr.patient_id = p.patient_id

        JOIN appointments a
            ON mr.appointment_id = a.appointment_id

        JOIN hospitals h
            ON a.hospital_id = h.hospital_id

        WHERE mr.doctor_id=%s

        ORDER BY mr.created_at DESC
    """, (doctor_id,))

    records = cur.fetchall()

    cur.close()

    return render_template(
        "doctor/medical_records.html",
        records=records
    )

#-------------- ADMIN LOGIN PAGE ---------------- #
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "GET":
        return render_template("admin/admin_login.html")

    username = request.form["username"]
    password = request.form["password"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            admin_id,
            full_name,
            password
        FROM admins
        WHERE username=%s
    """, (username,))

    admin = cur.fetchone()

    cur.close()

    if admin:

        # Plain-text password check (temporary)
        if check_password_hash(admin[2], password):

            session["admin_id"] = admin[0]
            session["admin_name"] = admin[1]

            flash("Welcome Administrator!", "success")

            return redirect("/admin/dashboard")

    flash("Invalid Username or Password", "danger")

    return redirect("/admin/login")

@app.route("/admin/dashboard")
def admin_dashboard():

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    # Dashboard Counts
    cur.execute("SELECT COUNT(*) FROM patients")
    total_patients = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM doctors")
    total_doctors = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM hospitals")
    total_hospitals = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM departments")
    total_departments = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date=CURDATE()")
    today = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments WHERE status='Completed'")
    completed = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM appointments WHERE status='Cancelled'")
    cancelled = cur.fetchone()[0]

    # Monthly Appointments
    cur.execute("""
SELECT
    MONTHNAME(appointment_date) AS month,
    COUNT(*) AS total
FROM appointments
GROUP BY
    MONTH(appointment_date),
    MONTHNAME(appointment_date)
ORDER BY
    MONTH(appointment_date)
""")

    chart = cur.fetchall()

    months = [row[0] for row in chart]
    counts = [row[1] for row in chart]

    cur.close()

    print("Months:", months)
    print("Counts:", counts)

    return render_template(
        "admin/admin_dashboard.html",
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_hospitals=total_hospitals,
        total_departments=total_departments,
        today=today,
        completed=completed,
        cancelled=cancelled,
        months=months,
        counts=counts
    )

@app.route("/admin/departments")
def admin_departments():

    if "admin_id" not in session:
        return redirect("/admin/login")

    search = request.args.get("search", "")

    cur = mysql.connection.cursor()

    if search:

        cur.execute("""
            SELECT
                department_id,
                department_name,
                description
            FROM departments
            WHERE
                department_name LIKE %s
                OR description LIKE %s
            ORDER BY department_id DESC
        """, (
            "%" + search + "%",
            "%" + search + "%"
        ))

    else:

        cur.execute("""
            SELECT
                department_id,
                department_name,
                description
            FROM departments
            ORDER BY department_id DESC
        """)

    departments = cur.fetchall()

    cur.close()

    return render_template(
        "admin/departments.html",
        departments=departments,
        search=search
    )

@app.route("/admin/view_patient/<int:id>")
def admin_view_patient(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    cur.execute("""
SELECT
    patient_id,
    CONCAT(first_name,' ',IFNULL(last_name,'')),
    gender,
    date_of_birth,
    phone,
    email,
    address,
    created_at,
    cid_number,
    blood_group,
    nationality,
    dzongkhag,
    gewog,
    village
FROM patients
WHERE patient_id=%s
""", (id,))

    patient = cur.fetchone()

    cur.close()

    return render_template(
        "admin/view_patient.html",
        patient=patient
    )


@app.route("/admin/doctors")
def admin_doctors():

    if "admin_id" not in session:
        return redirect("/admin/login")

    search = request.args.get("search", "")

    cur = mysql.connection.cursor()

    if search:

        cur.execute("""
            SELECT
                doctor_id,
                doctor_name,
                specialization,
                phone,
                email,
                status
            FROM doctors
            WHERE
                doctor_name LIKE %s
                OR specialization LIKE %s
                OR phone LIKE %s
                OR email LIKE %s
            ORDER BY doctor_id DESC
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        ))

    else:

        cur.execute("""
            SELECT
                doctor_id,
                doctor_name,
                specialization,
                phone,
                email,
                status
            FROM doctors
            ORDER BY doctor_id DESC
        """)

    doctors = cur.fetchall()

    cur.close()

    return render_template(
        "admin/doctors.html",
        doctors=doctors,
        search=search
    )

@app.route("/admin/patients")
def admin_patients():

    if "admin_id" not in session:
        return redirect("/admin/login")

    search = request.args.get("search", "")

    cur = mysql.connection.cursor()

    if search:

        cur.execute("""
            SELECT
                patient_id,
                CONCAT(first_name,' ',last_name),
                gender,
                phone,
                email,
                created_at
            FROM patients
            WHERE
                first_name LIKE %s
                OR last_name LIKE %s
                OR phone LIKE %s
                OR email LIKE %s
            ORDER BY patient_id DESC
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        ))

    else:

        cur.execute("""
            SELECT
                patient_id,
                CONCAT(first_name,' ',last_name),
                gender,
                phone,
                email,
                created_at
            FROM patients
            ORDER BY patient_id DESC
        """)

    patients = cur.fetchall()

    cur.close()

    return render_template(
        "admin/patients.html",
        patients=patients,
        search=search
    )


@app.route("/admin/appointments")
def admin_appointments():

    if "admin_id" not in session:
        return redirect("/admin/login")

    search = request.args.get("search", "")

    cur = mysql.connection.cursor()

    if search:

        cur.execute("""
            SELECT
                a.appointment_id,
                CONCAT(p.first_name,' ',p.last_name),
                d.doctor_name,
                h.hospital_name,
                a.appointment_date,
                a.appointment_time,
                a.status
            FROM appointments a
            JOIN patients p
                ON a.patient_id=p.patient_id
            JOIN doctors d
                ON a.doctor_id=d.doctor_id
            JOIN hospitals h
                ON a.hospital_id=h.hospital_id
            WHERE
                p.first_name LIKE %s
                OR p.last_name LIKE %s
                OR d.doctor_name LIKE %s
                OR a.status LIKE %s
            ORDER BY a.appointment_date DESC
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        ))

    else:

        cur.execute("""
            SELECT
                a.appointment_id,
                CONCAT(p.first_name,' ',p.last_name),
                d.doctor_name,
                h.hospital_name,
                a.appointment_date,
                a.appointment_time,
                a.status
            FROM appointments a
            JOIN patients p
                ON a.patient_id=p.patient_id
            JOIN doctors d
                ON a.doctor_id=d.doctor_id
            JOIN hospitals h
                ON a.hospital_id=h.hospital_id
            ORDER BY a.appointment_date DESC
        """)

    appointments = cur.fetchall()

    cur.close()

    return render_template(
        "admin/appointments.html",
        appointments=appointments,
        search=search
    )

@app.route("/admin/medical_records")
def admin_medical_records():

    if "admin_id" not in session:
        return redirect("/admin/login")

    search = request.args.get("search", "")

    cur = mysql.connection.cursor()

    if search:

        cur.execute("""
            SELECT
                mr.record_id,
                CONCAT(p.first_name,' ',p.last_name),
                d.doctor_name,
                mr.diagnosis,
                mr.prescription,
                mr.created_at
            FROM medical_records mr
            JOIN patients p
                ON mr.patient_id = p.patient_id
            JOIN doctors d
                ON mr.doctor_id = d.doctor_id
            WHERE
                p.first_name LIKE %s
                OR p.last_name LIKE %s
                OR d.doctor_name LIKE %s
                OR mr.diagnosis LIKE %s
            ORDER BY mr.record_id DESC
        """,(
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        ))

    else:

        cur.execute("""
            SELECT
                mr.record_id,
                CONCAT(p.first_name,' ',p.last_name),
                d.doctor_name,
                mr.diagnosis,
                mr.prescription,
                mr.created_at
            FROM medical_records mr
            JOIN patients p
                ON mr.patient_id = p.patient_id
            JOIN doctors d
                ON mr.doctor_id = d.doctor_id
            ORDER BY mr.record_id DESC
        """)

    records = cur.fetchall()

    cur.close()

    return render_template(
        "admin/medical_records.html",
        records=records,
        search=search
    )

@app.route("/admin/view_record/<int:id>")
def admin_view_record(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT

            mr.record_id,

            CONCAT(p.first_name,' ',p.last_name),

            doc.doctor_name,

            h.hospital_name,

            mr.diagnosis,

            mr.prescription,

            mr.doctor_notes,

            mr.created_at

        FROM medical_records mr

        LEFT JOIN patients p
            ON mr.patient_id=p.patient_id

        LEFT JOIN doctors doc
            ON mr.doctor_id=doc.doctor_id

        LEFT JOIN appointments a
            ON mr.appointment_id=a.appointment_id

        LEFT JOIN hospitals h
            ON a.hospital_id=h.hospital_id

        WHERE mr.record_id=%s
    """,(id,))

    record = cur.fetchone()

    cur.close()

    return render_template(
        "admin/view_record.html",
        record=record
    )

@app.route("/admin/hospitals")
def admin_hospitals():

    if "admin_id" not in session:
        return redirect("/admin/login")

    search = request.args.get("search", "")

    cur = mysql.connection.cursor()

    if search:

        cur.execute("""
            SELECT
                hospital_id,
                hospital_name,
                hospital_type,
                phone,
                email
            FROM hospitals
            WHERE status='Active'
            AND (
                hospital_name LIKE %s
                OR hospital_type LIKE %s
                OR phone LIKE %s
                OR email LIKE %s
            )
            ORDER BY hospital_id DESC
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        ))

    else:

        cur.execute("""
            SELECT
                hospital_id,
                hospital_name,
                hospital_type,
                phone,
                email
            FROM hospitals
            WHERE status='Active'
            ORDER BY hospital_id DESC
        """)

    hospitals = cur.fetchall()

    cur.close()

    return render_template(
        "admin/hospitals.html",
        hospitals=hospitals,
        search=search
    )

@app.route("/admin/add_hospital", methods=["GET", "POST"])
def add_hospital():

    if "admin_id" not in session:
        return redirect("/admin/login")

    if request.method == "POST":

        hospital_name = request.form["hospital_name"]
        hospital_type = request.form["hospital_type"]
        district = request.form["district"]
        address = request.form["address"]
        phone = request.form["phone"]
        email = request.form["email"]

        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO hospitals
            (
                hospital_name,
                hospital_type,
                district,
                address,
                phone,
                email
            )

            VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (
            hospital_name,
            hospital_type,
            district,
            address,
            phone,
            email
        ))

        mysql.connection.commit()

        cur.close()

        flash("Hospital Added Successfully!", "success")

        return redirect("/admin/hospitals")

    return render_template("admin/add_hospital.html")

@app.route("/admin/edit_hospital/<int:id>", methods=["GET", "POST"])
def edit_hospital(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    if request.method == "POST":

        hospital_name = request.form["hospital_name"]
        hospital_type = request.form["hospital_type"]
        district = request.form["district"]
        address = request.form["address"]
        phone = request.form["phone"]
        email = request.form["email"]
        status = request.form["status"]

        cur.execute("""
            UPDATE hospitals

            SET
                hospital_name=%s,
                hospital_type=%s,
                district=%s,
                address=%s,
                phone=%s,
                email=%s,
                status=%s

            WHERE hospital_id=%s
        """,
        (
            hospital_name,
            hospital_type,
            district,
            address,
            phone,
            email,
            status,
            id
        ))

        mysql.connection.commit()

        cur.close()

        flash("Hospital Updated Successfully!", "success")

        return redirect("/admin/hospitals")

    cur.execute("""
        SELECT
            hospital_id,
            hospital_name,
            hospital_type,
            district,
            address,
            phone,
            email,
            status

        FROM hospitals

        WHERE hospital_id=%s
    """, (id,))

    hospital = cur.fetchone()

    cur.close()

    return render_template(
        "admin/edit_hospital.html",
        hospital=hospital
    )

@app.route("/admin/delete_hospital/<int:id>")
def delete_hospital(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    # Soft delete instead of deleting the row
    cur.execute("""
        UPDATE hospitals
        SET status='Inactive'
        WHERE hospital_id=%s
    """, (id,))

    mysql.connection.commit()
    cur.close()

    flash("Hospital removed successfully!", "success")

    return redirect("/admin/hospitals")

@app.route("/admin/add_department", methods=["GET", "POST"])
def add_department():

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    if request.method == "POST":

        hospital_id = request.form["hospital_id"]
        department_name = request.form["department_name"]
        description = request.form["description"]

        cur.execute("""
            INSERT INTO departments
            (
                hospital_id,
                department_name,
                description
            )
            VALUES
            (%s,%s,%s)
        """, (
            hospital_id,
            department_name,
            description
        ))

        mysql.connection.commit()

        cur.close()

        flash("Department Added Successfully!", "success")

        return redirect("/admin/departments")

    # Load hospitals for dropdown
    cur.execute("""
        SELECT hospital_id, hospital_name
        FROM hospitals
        WHERE status='Active'
        ORDER BY hospital_name
    """)

    hospitals = cur.fetchall()

    cur.close()

    return render_template(
        "admin/add_department.html",
        hospitals=hospitals
    )

@app.route("/admin/edit_department/<int:id>", methods=["GET", "POST"])
def edit_department(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    if request.method == "POST":

        department_name = request.form["department_name"]
        description = request.form["description"]
        status = request.form["status"]

        cur.execute("""
            UPDATE departments

            SET
                department_name=%s,
                description=%s,
                status=%s

            WHERE department_id=%s
        """,
        (
            department_name,
            description,
            status,
            id
        ))

        mysql.connection.commit()

        flash("Department Updated Successfully!", "success")

        return redirect("/admin/departments")

    cur.execute("""
        SELECT
            department_id,
            department_name,
            description,
            status

        FROM departments

        WHERE department_id=%s
    """, (id,))

    department = cur.fetchone()

    cur.close()

    return render_template(
        "admin/edit_department.html",
        department=department
    )

@app.route("/admin/delete_department/<int:id>")
def delete_department(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE departments
        SET status='Inactive'
        WHERE department_id=%s
    """, (id,))

    mysql.connection.commit()

    cur.close()

    flash("Department Deactivated Successfully!", "success")

    return redirect("/admin/departments")

@app.route("/admin/add_doctor", methods=["GET", "POST"])
def add_doctor():

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    if request.method == "POST":

        hospital_id = request.form["hospital_id"]
        department_id = request.form["department_id"]

        doctor_name = request.form["doctor_name"]
        gender = request.form["gender"]
        qualification = request.form["qualification"]
        specialization = request.form["specialization"]
        experience = request.form["experience"]
        license_no = request.form["license_no"]
        phone = request.form["phone"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        cur.execute("""
            INSERT INTO doctors(
                hospital_id,
                department_id,
                doctor_name,
                gender,
                qualification,
                specialization,
                experience,
                license_no,
                phone,
                email,
                password
            )
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            hospital_id,
            department_id,
            doctor_name,
            gender,
            qualification,
            specialization,
            experience,
            license_no,
            phone,
            email,
            password
        ))

        mysql.connection.commit()

        flash("Doctor Added Successfully!", "success")
        return redirect("/admin/doctors")

    # ----------------------------
    # Hospitals
    # ----------------------------
    cur.execute("""
        SELECT hospital_id, hospital_name
        FROM hospitals
        WHERE status='Active'
        ORDER BY hospital_name
    """)

    hospitals = cur.fetchall()

    # ----------------------------
    # Default Hospital
    # ----------------------------
    selected_hospital = request.args.get("hospital_id")

    if not selected_hospital:

        if hospitals:
            selected_hospital = hospitals[0][0]
        else:
            selected_hospital = 0

    # ----------------------------
    # Departments of Selected Hospital
    # ----------------------------
    cur.execute("""
        SELECT department_id, department_name
        FROM departments
        WHERE hospital_id=%s
        AND status='Active'
        ORDER BY department_name
    """, (selected_hospital,))

    departments = cur.fetchall()

    cur.close()

    return render_template(
        "admin/add_doctor.html",
        hospitals=hospitals,
        departments=departments,
        selected_hospital=selected_hospital
    )

@app.route("/get_departments/<int:hospital_id>")
def get_departments(hospital_id):

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT department_id, department_name
        FROM departments
        WHERE hospital_id=%s
        AND status='Active'
        ORDER BY department_name
    """, (hospital_id,))

    departments = cur.fetchall()

    cur.close()

    return jsonify([
        {
            "id": d[0],
            "name": d[1]
        }
        for d in departments
    ])



@app.route("/get_doctors/<int:department_id>")
def get_doctors(department_id):

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            doctor_id,
            doctor_name
        FROM doctors
        WHERE department_id = %s
        AND status = 'Active'
        ORDER BY doctor_name
    """, (department_id,))

    doctors = cur.fetchall()

    cur.close()

    data = []

    for doctor in doctors:
        data.append({
            "id": doctor[0],
            "name": doctor[1]
        })

    return jsonify(data)

@app.route("/get_schedules/<int:doctor_id>")
def get_schedules(doctor_id):

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            schedule_id,
            available_date,
            start_time,
            end_time,
            available_tokens
        FROM doctor_schedule
        WHERE doctor_id=%s
        AND status='Available'
        AND available_tokens > 0
        ORDER BY available_date,start_time
    """, (doctor_id,))

    schedules = cur.fetchall()

    cur.close()

    data = []

    for s in schedules:
        data.append({
            "id": s[0],
            "date": str(s[1]),
            "start": str(s[2]),
            "end": str(s[3]),
            "tokens": s[4]
        })

    return jsonify(data)

@app.route("/patient/my_appointments")
def patient_my_appointments():

    if "patient_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/patient/login")

    patient_id = session["patient_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT

            a.appointment_id,
            h.hospital_name,
            d.department_name,
            doc.doctor_name,
            a.appointment_date,
            a.appointment_time,
            a.appointment_type,
            a.status

        FROM appointments a

        JOIN hospitals h
        ON a.hospital_id = h.hospital_id

        JOIN departments d
        ON a.department_id = d.department_id

        JOIN doctors doc
        ON a.doctor_id = doc.doctor_id

        WHERE a.patient_id=%s

        ORDER BY
        a.appointment_date DESC,
        a.appointment_time DESC

    """, (patient_id,))

    appointments = cur.fetchall()

    cur.close()

    return render_template(
        "patient/my_appointments.html",
        appointments=appointments
    )

@app.route("/admin/reports")
def admin_reports():

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    # Appointments by Status
    cur.execute("""
        SELECT status, COUNT(*)
        FROM appointments
        GROUP BY status
    """)
    status_report = cur.fetchall()

    # Patients by Gender
    cur.execute("""
        SELECT gender, COUNT(*)
        FROM patients
        GROUP BY gender
    """)
    gender_report = cur.fetchall()

    # Doctors by Department
    cur.execute("""
        SELECT departments.department_name,
               COUNT(doctors.doctor_id)
        FROM departments
        LEFT JOIN doctors
        ON departments.department_id = doctors.department_id
        GROUP BY departments.department_name
    """)
    department_report = cur.fetchall()

    cur.close()

    return render_template(
        "admin/reports.html",
        status_report=status_report,
        gender_report=gender_report,
        department_report=department_report
    )

@app.route("/admin/report/patients")
def patient_report():

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            patient_id,
            first_name,
            last_name,
            gender,
            phone,
            email
        FROM patients
        ORDER BY patient_id
    """)

    patients = cur.fetchall()
    cur.close()

    filename = "Patients_Report.pdf"

    c = canvas.Canvas(filename, pagesize=letter)

    width, height = letter

    y = height - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(180, y, "eHealth Bhutan")
    y -= 30

    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, y, "Patients Report")
    y -= 40

    c.setFont("Helvetica-Bold", 10)

    c.drawString(30, y, "ID")
    c.drawString(70, y, "Name")
    c.drawString(220, y, "Gender")
    c.drawString(300, y, "Phone")
    c.drawString(420, y, "Email")

    y -= 20

    c.setFont("Helvetica", 10)

    for p in patients:

        c.drawString(30, y, str(p[0]))
        c.drawString(70, y, f"{p[1]} {p[2]}")
        c.drawString(220, y, p[3])
        c.drawString(300, y, p[4] or "")
        c.drawString(420, y, p[5] or "")

        y -= 20

        if y < 50:

            c.showPage()

            y = height - 50

            c.setFont("Helvetica", 10)

    c.save()

    return send_file(
        filename,
        as_attachment=True
    )

@app.route("/admin/report/doctors")
def doctor_report():

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            doctor_id,
            doctor_name,
            specialization,
            phone,
            email
        FROM doctors
        ORDER BY doctor_id
    """)

    doctors = cur.fetchall()
    cur.close()

    filename = "Doctors_Report.pdf"

    c = canvas.Canvas(filename, pagesize=letter)

    width, height = letter
    y = height - 50

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(180, y, "eHealth Bhutan")
    y -= 30

    c.setFont("Helvetica-Bold", 14)
    c.drawString(195, y, "Doctors Report")
    y -= 40

    # Headers
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30, y, "ID")
    c.drawString(70, y, "Doctor")
    c.drawString(220, y, "Specialization")
    c.drawString(360, y, "Phone")
    c.drawString(470, y, "Email")

    y -= 20

    c.setFont("Helvetica", 10)

    for d in doctors:

        c.drawString(30, y, str(d[0]))
        c.drawString(70, y, d[1] or "")
        c.drawString(220, y, d[2] or "")
        c.drawString(360, y, d[3] or "")
        c.drawString(470, y, d[4] or "")

        y -= 20

        if y < 50:
            c.showPage()
            y = height - 50

            c.setFont("Helvetica-Bold", 10)
            c.drawString(30, y, "ID")
            c.drawString(70, y, "Doctor")
            c.drawString(220, y, "Specialization")
            c.drawString(360, y, "Phone")
            c.drawString(470, y, "Email")

            y -= 20
            c.setFont("Helvetica", 10)

    c.save()

    return send_file(
        filename,
        as_attachment=True
    )

@app.route("/admin/report/appointments")
def appointment_report():

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            a.appointment_id,
            CONCAT(p.first_name,' ',p.last_name),
            d.doctor_name,
            a.appointment_date,
            a.appointment_time,
            a.status
        FROM appointments a
        JOIN patients p
            ON a.patient_id = p.patient_id
        JOIN doctors d
            ON a.doctor_id = d.doctor_id
        ORDER BY a.appointment_date DESC
    """)

    appointments = cur.fetchall()
    cur.close()

    filename = "Appointments_Report.pdf"

    c = canvas.Canvas(filename, pagesize=letter)

    width, height = letter
    y = height - 50

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(170, y, "eHealth Bhutan")
    y -= 30

    c.setFont("Helvetica-Bold", 14)
    c.drawString(170, y, "Appointments Report")
    y -= 40

    # Headers
    c.setFont("Helvetica-Bold", 10)

    c.drawString(20, y, "ID")
    c.drawString(55, y, "Patient")
    c.drawString(180, y, "Doctor")
    c.drawString(310, y, "Date")
    c.drawString(390, y, "Time")
    c.drawString(470, y, "Status")

    y -= 20

    c.setFont("Helvetica", 10)

    for a in appointments:

        c.drawString(20, y, str(a[0]))
        c.drawString(55, y, str(a[1]))
        c.drawString(180, y, str(a[2]))
        c.drawString(310, y, str(a[3]))
        c.drawString(390, y, str(a[4]))
        c.drawString(470, y, str(a[5]))

        y -= 20

        if y < 50:

            c.showPage()

            y = height - 50

            c.setFont("Helvetica-Bold", 10)

            c.drawString(20, y, "ID")
            c.drawString(55, y, "Patient")
            c.drawString(180, y, "Doctor")
            c.drawString(310, y, "Date")
            c.drawString(390, y, "Time")
            c.drawString(470, y, "Status")

            y -= 20
            c.setFont("Helvetica", 10)

    c.save()

    return send_file(
        filename,
        as_attachment=True
    )

@app.route("/admin/report/medical_records")
def medical_record_report():

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            mr.record_id,
            CONCAT(p.first_name,' ',p.last_name),
            d.doctor_name,
            mr.diagnosis,
            mr.prescription,
            mr.created_at
        FROM medical_records mr
        JOIN patients p
            ON mr.patient_id = p.patient_id
        JOIN doctors d
            ON mr.doctor_id = d.doctor_id
        ORDER BY mr.record_id DESC
    """)

    records = cur.fetchall()

    cur.close()

    filename = "Medical_Records_Report.pdf"

    c = canvas.Canvas(filename, pagesize=letter)

    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold",18)
    c.drawString(170,y,"eHealth Bhutan")
    y -= 30

    c.setFont("Helvetica-Bold",14)
    c.drawString(150,y,"Medical Records Report")
    y -= 40

    c.setFont("Helvetica-Bold",10)

    c.drawString(20,y,"ID")
    c.drawString(45,y,"Patient")
    c.drawString(150,y,"Doctor")
    c.drawString(260,y,"Diagnosis")
    c.drawString(390,y,"Prescription")
    c.drawString(510,y,"Created")

    y -= 20

    c.setFont("Helvetica",8)

    for r in records:

        c.drawString(20,y,str(r[0]))
        c.drawString(45,y,str(r[1])[:18])
        c.drawString(150,y,str(r[2])[:18])
        c.drawString(260,y,str(r[3])[:20])
        c.drawString(390,y,str(r[4])[:18])
        c.drawString(510,y,str(r[5])[:10])

        y -= 18

        if y < 50:

            c.showPage()

            y = height - 50

            c.setFont("Helvetica-Bold",10)

            c.drawString(20,y,"ID")
            c.drawString(45,y,"Patient")
            c.drawString(150,y,"Doctor")
            c.drawString(260,y,"Diagnosis")
            c.drawString(390,y,"Prescription")
            c.drawString(510,y,"Created")

            y -= 20

            c.setFont("Helvetica",8)

    c.save()

    return send_file(
        filename,
        as_attachment=True
    )

from werkzeug.security import generate_password_hash

@app.route("/hash_doctors")
def hash_doctors():

    cur = mysql.connection.cursor()

    hash1 = generate_password_hash("123456")
    hash2 = generate_password_hash("doctor123")

    cur.execute("""
        UPDATE doctors
        SET password=%s
        WHERE password='123456'
    """, (hash1,))

    cur.execute("""
        UPDATE doctors
        SET password=%s
        WHERE password='doctor123'
    """, (hash2,))

    mysql.connection.commit()

    cur.close()

    return "✅ Doctor passwords hashed successfully!"

#--------Profile Route for Patient---------#
@app.route("/patient/profile")
def patient_profile():

    if "patient_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/patient/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            cid_number,
            first_name,
            last_name,
            gender,
            date_of_birth,
            blood_group,
            nationality,
            phone,
            email,
            dzongkhag,
            gewog,
            village,
            emergency_contact_name,
            emergency_contact_phone
        FROM patients
        WHERE patient_id=%s
    """, (session["patient_id"],))

    patient = cur.fetchone()

    cur.close()

    return render_template(
        "patient/profile.html",
        patient=patient
    )

@app.route("/admin/delete_patient/<int:id>")
def delete_patient(id):

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE patients
        SET status='Inactive'
        WHERE patient_id=%s
    """, (id,))

    mysql.connection.commit()
    cur.close()

    flash("Patient deactivated successfully.", "success")

    return redirect("/admin/patients")

@app.route("/admin/delete_doctor/<int:id>")
def delete_doctor(id):

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE doctors
        SET status='Inactive'
        WHERE doctor_id=%s
    """,(id,))

    mysql.connection.commit()

    cur.close()

    flash("Doctor deactivated successfully!", "success")

    return redirect("/admin/doctors")

@app.route("/admin/view_appointment/<int:id>")
def view_appointment(id):

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT

            a.appointment_id,

            CONCAT(p.first_name,' ',p.last_name) AS patient_name,
            p.gender,
            p.date_of_birth,
            p.cid_number,
            p.phone,
            p.email,
            p.blood_group,
            p.nationality,
            CONCAT(p.dzongkhag, ', ', p.gewog, ', ', p.village) AS address,

            h.hospital_name,

            d.department_name,

            doc.doctor_name,
            doc.specialization,

            a.appointment_date,
            a.appointment_time,
            a.appointment_type,
            a.status,
            a.remarks

        FROM appointments a

        JOIN patients p
            ON a.patient_id = p.patient_id

        JOIN hospitals h
            ON a.hospital_id = h.hospital_id

        JOIN departments d
            ON a.department_id = d.department_id

        JOIN doctors doc
            ON a.doctor_id = doc.doctor_id

        WHERE a.appointment_id=%s
    """, (id,))

    appointment = cur.fetchone()

    cur.close()

    return render_template(
        "admin/view_appointment.html",
        appointment=appointment
    )

@app.route("/admin/edit_doctor/<int:id>", methods=["GET", "POST"])
def edit_doctor(id):

    if "admin_id" not in session:
        return redirect("/admin/login")

    cur = mysql.connection.cursor()

    # ------------------------------
    # UPDATE DOCTOR
    # ------------------------------
    if request.method == "POST":

        hospital_id = request.form["hospital_id"]
        department_id = request.form["department_id"]
        doctor_name = request.form["doctor_name"]
        gender = request.form["gender"]
        qualification = request.form["qualification"]
        specialization = request.form["specialization"]
        experience = request.form["experience"]
        license_no = request.form["license_no"]
        phone = request.form["phone"]
        email = request.form["email"]
        status = request.form["status"]

        cur.execute("""
            UPDATE doctors
            SET
                hospital_id=%s,
                department_id=%s,
                doctor_name=%s,
                gender=%s,
                qualification=%s,
                specialization=%s,
                experience=%s,
                license_no=%s,
                phone=%s,
                email=%s,
                status=%s
            WHERE doctor_id=%s
        """, (
            hospital_id,
            department_id,
            doctor_name,
            gender,
            qualification,
            specialization,
            experience,
            license_no,
            phone,
            email,
            status,
            id
        ))

        mysql.connection.commit()

        cur.close()

        flash("Doctor updated successfully!", "success")

        return redirect("/admin/doctors")

    # ------------------------------
    # LOAD HOSPITALS
    # ------------------------------
    cur.execute("""
        SELECT hospital_id, hospital_name
        FROM hospitals
        WHERE status='Active'
        ORDER BY hospital_name
    """)
    hospitals = cur.fetchall()

    # ------------------------------
    # LOAD DEPARTMENTS
    # ------------------------------
    cur.execute("""
        SELECT department_id, department_name
        FROM departments
        ORDER BY department_name
    """)
    departments = cur.fetchall()

    # ------------------------------
    # LOAD DOCTOR DETAILS
    # ------------------------------
    cur.execute("""
        SELECT *
        FROM doctors
        WHERE doctor_id=%s
    """, (id,))

    doctor = cur.fetchone()

    cur.close()

    if not doctor:
        flash("Doctor not found!", "danger")
        return redirect("/admin/doctors")

    return render_template(
        "admin/edit_doctor.html",
        doctor=doctor,
        hospitals=hospitals,
        departments=departments
    )

@app.route("/patient/edit_profile", methods=["GET", "POST"])
def patient_edit_profile():

    if "patient_id" not in session:
        return redirect("/patient/login")

    cur = mysql.connection.cursor()

    if request.method == "POST":

        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        phone = request.form["phone"]
        email = request.form["email"]
        dzongkhag = request.form["dzongkhag"]
        gewog = request.form["gewog"]
        village = request.form["village"]
        emergency_contact_name = request.form["emergency_contact_name"]
        emergency_contact_phone = request.form["emergency_contact_phone"]

        cur.execute("""
            UPDATE patients
            SET
                first_name=%s,
                last_name=%s,
                phone=%s,
                email=%s,
                dzongkhag=%s,
                gewog=%s,
                village=%s,
                emergency_contact_name=%s,
                emergency_contact_phone=%s
            WHERE patient_id=%s
        """,(
            first_name,
            last_name,
            phone,
            email,
            dzongkhag,
            gewog,
            village,
            emergency_contact_name,
            emergency_contact_phone,
            session["patient_id"]
        ))

        mysql.connection.commit()

        flash("Profile Updated Successfully!","success")

        cur.close()

        return redirect("/patient/profile")

    cur.execute("""
        SELECT *
        FROM patients
        WHERE patient_id=%s
    """,(session["patient_id"],))

    patient=cur.fetchone()

    cur.close()

    return render_template(
        "patient/edit_profile.html",
        patient=patient
    )

@app.route("/patient/change_password", methods=["GET","POST"])
def patient_change_password():

    if "patient_id" not in session:
        return redirect("/patient/login")

    if request.method=="POST":

        old_password=request.form["old_password"]
        new_password=request.form["new_password"]
        confirm_password=request.form["confirm_password"]

        cur=mysql.connection.cursor()

        cur.execute("""
            SELECT password
            FROM patients
            WHERE patient_id=%s
        """,(session["patient_id"],))

        patient=cur.fetchone()

        if patient[0]!=old_password:

            flash("Old Password Incorrect","danger")

        elif new_password!=confirm_password:

            flash("Passwords do not match","danger")

        else:

            cur.execute("""
                UPDATE patients
                SET password=%s
                WHERE patient_id=%s
            """,(new_password,session["patient_id"]))

            mysql.connection.commit()

            flash("Password Changed Successfully","success")

        cur.close()

        return redirect("/patient/change_password")

    return render_template("patient/change_password.html")

@app.route("/doctor/change_password", methods=["GET", "POST"])
def doctor_change_password():

    if "doctor_id" not in session:
        flash("Please login first.", "warning")
        return redirect("/doctor/login")

    if request.method == "POST":

        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT password
            FROM doctors
            WHERE doctor_id=%s
        """, (session["doctor_id"],))

        doctor = cur.fetchone()

        if not check_password_hash(doctor[0], old_password):
            flash("Old password is incorrect.", "danger")
            return redirect("/doctor/change_password")

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect("/doctor/change_password")

        hashed = generate_password_hash(new_password)

        cur.execute("""
            UPDATE doctors
            SET password=%s
            WHERE doctor_id=%s
        """, (hashed, session["doctor_id"]))

        mysql.connection.commit()
        cur.close()

        flash("Password changed successfully.", "success")
        return redirect("/doctor/dashboard")

    return render_template("doctor/change_password.html")
@app.route("/patient/logout")
def patient_logout():
    session.pop("patient_id", None)
    session.pop("patient_name", None)
    flash("Logged out successfully!", "success")
    return redirect("/")


@app.route("/doctor/logout")
def doctor_logout():
    session.pop("doctor_id", None)
    session.pop("doctor_name", None)
    flash("Logged out successfully!", "success")
    return redirect("/")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    flash("Logged out successfully!", "success")
    return redirect("/")
# ================= RUN ================= #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)