"""
app.py
Smart CGPA Planner - Main Flask Application
Run with: python app.py
Then open: http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from database import get_db_connection, init_db
from calculations import calculate_sgpa, calculate_cgpa, calculate_required_sgpa, GRADE_POINTS

app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"  # used to secure session cookies


# ---------- Helper: login required decorator ----------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ---------- AUTH ROUTES ----------

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return redirect(url_for("register"))

        conn = get_db_connection()
        existing_user = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing_user:
            flash("An account with this email already exists.", "error")
            conn.close()
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        conn.commit()
        conn.close()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------- DASHBOARD ----------

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    semesters = conn.execute(
        "SELECT * FROM semesters WHERE user_id = ? ORDER BY semester_number",
        (session["user_id"],)
    ).fetchall()

    semester_list = []
    overall_semesters_for_cgpa = []

    for sem in semesters:
        subjects = conn.execute(
            "SELECT * FROM subjects WHERE semester_id = ?", (sem["id"],)
        ).fetchall()
        total_credits = sum(s["credits"] for s in subjects)
        semester_list.append({
            "id": sem["id"],
            "semester_number": sem["semester_number"],
            "sgpa": sem["sgpa"],
            "total_credits": total_credits,
            "subject_count": len(subjects)
        })
        if total_credits > 0:
            overall_semesters_for_cgpa.append({"sgpa": sem["sgpa"], "total_credits": total_credits})

    conn.close()

    cgpa = calculate_cgpa(overall_semesters_for_cgpa)
    total_credits_overall = sum(s["total_credits"] for s in overall_semesters_for_cgpa)

    return render_template(
        "dashboard.html",
        semesters=semester_list,
        cgpa=cgpa,
        total_credits=total_credits_overall,
        user_name=session.get("user_name")
    )


# ---------- SEMESTER ROUTES ----------

@app.route("/semester/add", methods=["POST"])
@login_required
def add_semester():
    semester_number = request.form.get("semester_number", type=int)

    if not semester_number or semester_number < 1:
        flash("Please enter a valid semester number.", "error")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT id FROM semesters WHERE user_id = ? AND semester_number = ?",
        (session["user_id"], semester_number)
    ).fetchone()

    if existing:
        flash(f"Semester {semester_number} already exists.", "error")
    else:
        conn.execute(
            "INSERT INTO semesters (user_id, semester_number, sgpa) VALUES (?, ?, 0)",
            (session["user_id"], semester_number)
        )
        conn.commit()
        flash(f"Semester {semester_number} added.", "success")

    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/semester/<int:semester_id>")
@login_required
def view_semester(semester_id):
    conn = get_db_connection()
    semester = conn.execute(
        "SELECT * FROM semesters WHERE id = ? AND user_id = ?",
        (semester_id, session["user_id"])
    ).fetchone()

    if not semester:
        flash("Semester not found.", "error")
        conn.close()
        return redirect(url_for("dashboard"))

    subjects = conn.execute(
        "SELECT * FROM subjects WHERE semester_id = ?", (semester_id,)
    ).fetchall()
    conn.close()

    return render_template(
        "semester.html",
        semester=semester,
        subjects=subjects,
        grade_options=list(GRADE_POINTS.keys())
    )


@app.route("/semester/<int:semester_id>/delete", methods=["POST"])
@login_required
def delete_semester(semester_id):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM semesters WHERE id = ? AND user_id = ?",
        (semester_id, session["user_id"])
    )
    conn.commit()
    conn.close()
    flash("Semester deleted.", "success")
    return redirect(url_for("dashboard"))


# ---------- SUBJECT ROUTES ----------

@app.route("/semester/<int:semester_id>/subject/add", methods=["POST"])
@login_required
def add_subject(semester_id):
    conn = get_db_connection()
    # verify ownership
    semester = conn.execute(
        "SELECT * FROM semesters WHERE id = ? AND user_id = ?",
        (semester_id, session["user_id"])
    ).fetchone()

    if not semester:
        flash("Semester not found.", "error")
        conn.close()
        return redirect(url_for("dashboard"))

    subject_name = request.form.get("subject_name", "").strip()
    credits = request.form.get("credits", type=float)
    grade = request.form.get("grade", "")

    if not subject_name or credits is None or grade not in GRADE_POINTS:
        flash("Please fill all subject fields correctly.", "error")
        conn.close()
        return redirect(url_for("view_semester", semester_id=semester_id))

    grade_point = GRADE_POINTS[grade]

    conn.execute(
        "INSERT INTO subjects (semester_id, subject_name, credits, grade_point) VALUES (?, ?, ?, ?)",
        (semester_id, subject_name, credits, grade_point)
    )
    conn.commit()

    _recalculate_sgpa(conn, semester_id)
    conn.close()

    flash("Subject added.", "success")
    return redirect(url_for("view_semester", semester_id=semester_id))


@app.route("/subject/<int:subject_id>/delete", methods=["POST"])
@login_required
def delete_subject(subject_id):
    conn = get_db_connection()
    subject = conn.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()

    if not subject:
        conn.close()
        flash("Subject not found.", "error")
        return redirect(url_for("dashboard"))

    semester_id = subject["semester_id"]
    # verify the semester belongs to the logged-in user
    semester = conn.execute(
        "SELECT * FROM semesters WHERE id = ? AND user_id = ?",
        (semester_id, session["user_id"])
    ).fetchone()

    if not semester:
        conn.close()
        flash("Not authorized.", "error")
        return redirect(url_for("dashboard"))

    conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    conn.commit()

    _recalculate_sgpa(conn, semester_id)
    conn.close()

    flash("Subject removed.", "success")
    return redirect(url_for("view_semester", semester_id=semester_id))


def _recalculate_sgpa(conn, semester_id):
    """Recalculates and stores SGPA for a semester after subject changes."""
    subjects = conn.execute(
        "SELECT credits, grade_point FROM subjects WHERE semester_id = ?", (semester_id,)
    ).fetchall()
    subject_list = [{"credits": s["credits"], "grade_point": s["grade_point"]} for s in subjects]
    sgpa = calculate_sgpa(subject_list)
    conn.execute("UPDATE semesters SET sgpa = ? WHERE id = ?", (sgpa, semester_id))
    conn.commit()


# ---------- TARGET CGPA PLANNER ----------

@app.route("/planner", methods=["GET", "POST"])
@login_required
def planner():
    conn = get_db_connection()
    semesters = conn.execute(
        "SELECT * FROM semesters WHERE user_id = ? ORDER BY semester_number",
        (session["user_id"],)
    ).fetchall()

    overall_semesters = []
    for sem in semesters:
        subjects = conn.execute(
            "SELECT credits FROM subjects WHERE semester_id = ?", (sem["id"],)
        ).fetchall()
        total_credits = sum(s["credits"] for s in subjects)
        if total_credits > 0:
            overall_semesters.append({"sgpa": sem["sgpa"], "total_credits": total_credits})
    conn.close()

    current_cgpa = calculate_cgpa(overall_semesters)
    completed_credits = sum(s["total_credits"] for s in overall_semesters)

    result = None
    if request.method == "POST":
        target_cgpa = request.form.get("target_cgpa", type=float)
        remaining_semesters = request.form.get("remaining_semesters", type=int)
        credits_per_semester = request.form.get("credits_per_semester", type=float)

        if target_cgpa and remaining_semesters and credits_per_semester:
            result = calculate_required_sgpa(
                current_cgpa, completed_credits, target_cgpa,
                remaining_semesters, credits_per_semester
            )
        else:
            flash("Please fill in all planner fields.", "error")

    return render_template(
        "planner.html",
        current_cgpa=current_cgpa,
        completed_credits=completed_credits,
        result=result
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
