"""
TalentHub - College Placement Management System
Main Flask Application
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import os
import hashlib
import secrets
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DATABASE = os.path.join(os.path.dirname(__file__), 'talenthub.db')


# ─────────────────────────── DATABASE HELPERS ───────────────────────────────

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS USERS (
                UserID      INTEGER PRIMARY KEY AUTOINCREMENT,
                Email       TEXT    NOT NULL UNIQUE,
                Password    TEXT    NOT NULL,
                Role        TEXT    NOT NULL CHECK(Role IN ('student','company','coordinator')),
                CreatedAt   TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS STUDENT (
                StudentID       INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID          INTEGER NOT NULL UNIQUE REFERENCES USERS(UserID),
                Name            TEXT    NOT NULL,
                Branch          TEXT    NOT NULL,
                CGPA            REAL    NOT NULL CHECK(CGPA >= 0.0 AND CGPA <= 10.0),
                ActiveBacklogs  INTEGER NOT NULL DEFAULT 0 CHECK(ActiveBacklogs >= 0),
                PlacementStatus TEXT    NOT NULL DEFAULT 'UNPLACED'
                                        CHECK(PlacementStatus IN ('UNPLACED','PLACED')),
                Phone           TEXT,
                Resume          TEXT
            );

            CREATE TABLE IF NOT EXISTS COMPANY (
                CompanyID   INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID      INTEGER NOT NULL UNIQUE REFERENCES USERS(UserID),
                CompanyName TEXT    NOT NULL,
                Industry    TEXT,
                Website     TEXT,
                Description TEXT
            );

            CREATE TABLE IF NOT EXISTS JOB (
                JobID           INTEGER PRIMARY KEY AUTOINCREMENT,
                CompanyID       INTEGER NOT NULL REFERENCES COMPANY(CompanyID),
                Role            TEXT    NOT NULL,
                Description     TEXT,
                Location        TEXT,
                Package         TEXT,
                MinCGPA         REAL    NOT NULL DEFAULT 0.0 CHECK(MinCGPA >= 0.0 AND MinCGPA <= 10.0),
                MaxActiveBacklogs INTEGER NOT NULL DEFAULT 0 CHECK(MaxActiveBacklogs >= 0),
                AllowedBranch   TEXT    NOT NULL DEFAULT 'ALL',
                Deadline        TEXT,
                IsActive        INTEGER NOT NULL DEFAULT 1,
                PostedAt        TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS APPLICATION (
                ApplicationID   INTEGER PRIMARY KEY AUTOINCREMENT,
                StudentID       INTEGER NOT NULL REFERENCES STUDENT(StudentID),
                JobID           INTEGER NOT NULL REFERENCES JOB(JobID),
                ApplicationDate TEXT    DEFAULT (datetime('now')),
                Status          TEXT    NOT NULL DEFAULT 'PENDING'
                                        CHECK(Status IN ('PENDING','SHORTLISTED','REJECTED','OFFERED','ACCEPTED','DECLINED')),
                UNIQUE(StudentID, JobID)
            );

            CREATE TABLE IF NOT EXISTS PLACEMENT_AUDIT_LOG (
                LogID       INTEGER PRIMARY KEY AUTOINCREMENT,
                EntityType  TEXT    NOT NULL,
                EntityID    INTEGER NOT NULL,
                Action      TEXT    NOT NULL,
                OldValue    TEXT,
                NewValue    TEXT,
                ChangedBy   INTEGER REFERENCES USERS(UserID),
                ChangedAt   TEXT    DEFAULT (datetime('now'))
            );

            -- Seed demo data if empty
            INSERT OR IGNORE INTO USERS(Email,Password,Role) VALUES
                ('admin@talenthub.in',   '""" + hashlib.sha256(b'admin123').hexdigest() + """', 'coordinator'),
                ('alice@student.in',     '""" + hashlib.sha256(b'student123').hexdigest() + """', 'student'),
                ('bob@student.in',       '""" + hashlib.sha256(b'student123').hexdigest() + """', 'student'),
                ('carol@student.in',     '""" + hashlib.sha256(b'student123').hexdigest() + """', 'student'),
                ('google@company.in',    '""" + hashlib.sha256(b'company123').hexdigest() + """', 'company'),
                ('microsoft@company.in', '""" + hashlib.sha256(b'company123').hexdigest() + """', 'company'),
                ('amazon@company.in',    '""" + hashlib.sha256(b'company123').hexdigest() + """', 'company');
        """)

        # Seed students if not existing
        rows = conn.execute("SELECT COUNT(*) as c FROM STUDENT").fetchone()
        if rows['c'] == 0:
            students_user_ids = conn.execute(
                "SELECT UserID FROM USERS WHERE Role='student' ORDER BY UserID"
            ).fetchall()
            demo_students = [
                (students_user_ids[0]['UserID'], 'Alice Sharma',   'CSE',  8.5, 0, 'UNPLACED', '9876543210'),
                (students_user_ids[1]['UserID'], 'Bob Patel',      'ECE',  7.2, 1, 'UNPLACED', '9876543211'),
                (students_user_ids[2]['UserID'], 'Carol Verma',    'MECH', 6.8, 2, 'UNPLACED', '9876543212'),
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO STUDENT(UserID,Name,Branch,CGPA,ActiveBacklogs,PlacementStatus,Phone) VALUES(?,?,?,?,?,?,?)",
                demo_students
            )

        # Seed companies
        rows = conn.execute("SELECT COUNT(*) as c FROM COMPANY").fetchone()
        if rows['c'] == 0:
            company_user_ids = conn.execute(
                "SELECT UserID FROM USERS WHERE Role='company' ORDER BY UserID"
            ).fetchall()
            demo_companies = [
                (company_user_ids[0]['UserID'], 'Google India',     'Technology',    'https://google.com',    'Leading tech giant'),
                (company_user_ids[1]['UserID'], 'Microsoft India',  'Technology',    'https://microsoft.com', 'Cloud & software leader'),
                (company_user_ids[2]['UserID'], 'Amazon India',     'E-Commerce',    'https://amazon.in',     'World\'s largest marketplace'),
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO COMPANY(UserID,CompanyName,Industry,Website,Description) VALUES(?,?,?,?,?)",
                demo_companies
            )

        # Seed jobs
        rows = conn.execute("SELECT COUNT(*) as c FROM JOB").fetchone()
        if rows['c'] == 0:
            companies = conn.execute("SELECT CompanyID FROM COMPANY ORDER BY CompanyID").fetchall()
            demo_jobs = [
                (companies[0]['CompanyID'], 'Software Engineer',       'Full-stack development role', 'Bangalore', '24 LPA', 7.5, 0, 'CSE',  '2026-12-31'),
                (companies[0]['CompanyID'], 'Data Analyst',            'Analytics and ML role',       'Hyderabad', '18 LPA', 7.0, 1, 'ALL',  '2026-12-31'),
                (companies[1]['CompanyID'], 'Cloud Engineer',          'Azure infrastructure role',   'Pune',      '22 LPA', 7.5, 0, 'CSE',  '2026-12-31'),
                (companies[1]['CompanyID'], 'Product Manager Intern',  'PM internship',               'Bangalore', '12 LPA', 6.5, 2, 'ALL',  '2026-12-31'),
                (companies[2]['CompanyID'], 'SDE-I',                   'Backend systems role',        'Chennai',   '20 LPA', 7.0, 1, 'ALL',  '2026-12-31'),
                (companies[2]['CompanyID'], 'Operations Analyst',      'Supply chain analysis',       'Mumbai',    '15 LPA', 6.0, 2, 'MECH', '2026-12-31'),
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO JOB(CompanyID,Role,Description,Location,Package,MinCGPA,MaxActiveBacklogs,AllowedBranch,Deadline) VALUES(?,?,?,?,?,?,?,?,?)",
                demo_jobs
            )

        conn.commit()


# ─────────────────────────── ELIGIBILITY ALGORITHM ──────────────────────────

def check_eligibility(student, job):
    """
    Comprehensive Rule Evaluation (Alt B from TalentHub design doc).
    Returns all failure reasons, not just the first one.
    """
    is_eligible = True
    failure_reasons = []

    # Rule 1: Placement policy
    if student['PlacementStatus'] == 'PLACED':
        is_eligible = False
        failure_reasons.append("You are already placed and ineligible under standard policy.")

    # Rule 2: CGPA boundary check (inclusive lower bound)
    if student['CGPA'] < job['MinCGPA']:
        is_eligible = False
        failure_reasons.append(
            f"Your CGPA ({student['CGPA']}) is below the required minimum ({job['MinCGPA']})."
        )

    # Rule 3: Active backlogs boundary check (inclusive upper bound)
    if student['ActiveBacklogs'] > job['MaxActiveBacklogs']:
        is_eligible = False
        failure_reasons.append(
            f"Your active backlogs ({student['ActiveBacklogs']}) exceed the maximum allowed ({job['MaxActiveBacklogs']})."
        )

    # Rule 4: Branch matching check
    if job['AllowedBranch'] != 'ALL' and student['Branch'] != job['AllowedBranch']:
        is_eligible = False
        failure_reasons.append(
            f"Your branch ({student['Branch']}) does not match the required branch ({job['AllowedBranch']})."
        )

    return is_eligible, failure_reasons


# ─────────────────────────── AUTH HELPERS ───────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def log_audit(entity_type, entity_id, action, old_val, new_val):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO PLACEMENT_AUDIT_LOG(EntityType,EntityID,Action,OldValue,NewValue,ChangedBy) VALUES(?,?,?,?,?,?)",
            (entity_type, entity_id, action, old_val, new_val, session.get('user_id'))
        )
        conn.commit()


# ─────────────────────────── ROUTES ─────────────────────────────────────────

@app.route('/')
def index():
    with get_db() as conn:
        stats = {
            'students':    conn.execute("SELECT COUNT(*) as c FROM STUDENT").fetchone()['c'],
            'companies':   conn.execute("SELECT COUNT(*) as c FROM COMPANY").fetchone()['c'],
            'jobs':        conn.execute("SELECT COUNT(*) as c FROM JOB WHERE IsActive=1").fetchone()['c'],
            'placements':  conn.execute("SELECT COUNT(*) as c FROM STUDENT WHERE PlacementStatus='PLACED'").fetchone()['c'],
        }
        jobs = conn.execute("""
            SELECT J.*, C.CompanyName FROM JOB J
            JOIN COMPANY C ON J.CompanyID = C.CompanyID
            WHERE J.IsActive=1 ORDER BY J.PostedAt DESC LIMIT 6
        """).fetchall()
        companies = conn.execute("SELECT * FROM COMPANY LIMIT 6").fetchall()
    return render_template('index.html', stats=stats, jobs=jobs, companies=companies)


# ── Authentication ──

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM USERS WHERE Email=? AND Password=?",
                (email, hash_password(password))
            ).fetchone()
        if user:
            session['user_id'] = user['UserID']
            session['email']   = user['Email']
            session['role']    = user['Role']
            flash(f'Welcome back! Logged in as {user["Role"].title()}.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role     = request.form.get('role', '')
        name     = request.form.get('name', '').strip()
        branch   = request.form.get('branch', '').strip()
        cgpa     = request.form.get('cgpa', 0)
        backlogs = request.form.get('backlogs', 0)
        company_name = request.form.get('company_name', '').strip()
        industry     = request.form.get('industry', '').strip()

        if role not in ('student', 'company'):
            flash('Invalid role.', 'danger')
            return render_template('register.html')

        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO USERS(Email,Password,Role) VALUES(?,?,?)",
                    (email, hash_password(password), role)
                )
                user_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()['id']
                if role == 'student':
                    conn.execute(
                        "INSERT INTO STUDENT(UserID,Name,Branch,CGPA,ActiveBacklogs) VALUES(?,?,?,?,?)",
                        (user_id, name, branch, float(cgpa), int(backlogs))
                    )
                else:
                    conn.execute(
                        "INSERT INTO COMPANY(UserID,CompanyName,Industry) VALUES(?,?,?)",
                        (user_id, company_name, industry)
                    )
                conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered.', 'danger')
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))


# ── Dashboard ──

@app.route('/dashboard')
@login_required
def dashboard():
    role = session['role']
    if role == 'student':
        return redirect(url_for('student_dashboard'))
    elif role == 'company':
        return redirect(url_for('company_dashboard'))
    else:
        return redirect(url_for('coordinator_dashboard'))


# ── Student ──

@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    with get_db() as conn:
        student = conn.execute(
            "SELECT * FROM STUDENT WHERE UserID=?", (session['user_id'],)
        ).fetchone()
        if not student:
            flash('Student profile not found.', 'danger')
            return redirect(url_for('index'))
        apps = conn.execute("""
            SELECT A.*, J.Role, J.Package, J.Location, C.CompanyName
            FROM APPLICATION A
            JOIN JOB J ON A.JobID=J.JobID
            JOIN COMPANY C ON J.CompanyID=C.CompanyID
            WHERE A.StudentID=?
            ORDER BY A.ApplicationDate DESC
        """, (student['StudentID'],)).fetchall()
        jobs = conn.execute("""
            SELECT J.*, C.CompanyName FROM JOB J
            JOIN COMPANY C ON J.CompanyID=C.CompanyID
            WHERE J.IsActive=1 ORDER BY J.PostedAt DESC
        """).fetchall()
    return render_template('student_dashboard.html', student=student, applications=apps, jobs=jobs)


@app.route('/student/apply/<int:job_id>', methods=['POST'])
@login_required
@role_required('student')
def apply_job(job_id):
    with get_db() as conn:
        student = conn.execute(
            "SELECT * FROM STUDENT WHERE UserID=?", (session['user_id'],)
        ).fetchone()
        job = conn.execute("SELECT * FROM JOB WHERE JobID=?", (job_id,)).fetchone()
        if not student or not job:
            flash('Invalid request.', 'danger')
            return redirect(url_for('student_dashboard'))

        is_eligible, reasons = check_eligibility(dict(student), dict(job))
        if not is_eligible:
            flash('Not eligible: ' + '; '.join(reasons), 'danger')
            return redirect(url_for('student_dashboard'))

        try:
            conn.execute(
                "INSERT INTO APPLICATION(StudentID,JobID) VALUES(?,?)",
                (student['StudentID'], job_id)
            )
            conn.commit()
            log_audit('APPLICATION', job_id, 'SUBMIT', None, f'StudentID={student["StudentID"]}')
            flash(f'Successfully applied for {job["Role"]}!', 'success')
        except sqlite3.IntegrityError:
            flash('You have already applied for this job.', 'warning')
    return redirect(url_for('student_dashboard'))


@app.route('/student/check-eligibility/<int:job_id>')
@login_required
@role_required('student')
def check_eligibility_route(job_id):
    with get_db() as conn:
        student = conn.execute(
            "SELECT * FROM STUDENT WHERE UserID=?", (session['user_id'],)
        ).fetchone()
        job = conn.execute("SELECT * FROM JOB WHERE JobID=?", (job_id,)).fetchone()
    if not student or not job:
        return jsonify({'eligible': False, 'reasons': ['Invalid data']})
    is_eligible, reasons = check_eligibility(dict(student), dict(job))
    return jsonify({'eligible': is_eligible, 'reasons': reasons})


@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_profile():
    with get_db() as conn:
        student = conn.execute(
            "SELECT * FROM STUDENT WHERE UserID=?", (session['user_id'],)
        ).fetchone()
        if request.method == 'POST':
            name     = request.form.get('name', '').strip()
            phone    = request.form.get('phone', '').strip()
            cgpa     = float(request.form.get('cgpa', student['CGPA']))
            backlogs = int(request.form.get('backlogs', student['ActiveBacklogs']))
            conn.execute(
                "UPDATE STUDENT SET Name=?,Phone=?,CGPA=?,ActiveBacklogs=? WHERE StudentID=?",
                (name, phone, cgpa, backlogs, student['StudentID'])
            )
            conn.commit()
            flash('Profile updated!', 'success')
            return redirect(url_for('student_profile'))
    return render_template('student_profile.html', student=student)


# ── Company ──

@app.route('/company/dashboard')
@login_required
@role_required('company')
def company_dashboard():
    with get_db() as conn:
        company = conn.execute(
            "SELECT * FROM COMPANY WHERE UserID=?", (session['user_id'],)
        ).fetchone()
        jobs = conn.execute(
            "SELECT * FROM JOB WHERE CompanyID=? ORDER BY PostedAt DESC",
            (company['CompanyID'],)
        ).fetchall()
        apps = conn.execute("""
            SELECT A.*, S.Name, S.CGPA, S.Branch, S.ActiveBacklogs, S.Phone,
                   J.Role, J.JobID
            FROM APPLICATION A
            JOIN STUDENT S ON A.StudentID=S.StudentID
            JOIN JOB J ON A.JobID=J.JobID
            WHERE J.CompanyID=?
            ORDER BY A.ApplicationDate DESC
        """, (company['CompanyID'],)).fetchall()
    return render_template('company_dashboard.html', company=company, jobs=jobs, applications=apps)


@app.route('/company/post-job', methods=['GET', 'POST'])
@login_required
@role_required('company')
def post_job():
    with get_db() as conn:
        company = conn.execute(
            "SELECT * FROM COMPANY WHERE UserID=?", (session['user_id'],)
        ).fetchone()
        if request.method == 'POST':
            conn.execute("""
                INSERT INTO JOB(CompanyID,Role,Description,Location,Package,
                                MinCGPA,MaxActiveBacklogs,AllowedBranch,Deadline)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (
                company['CompanyID'],
                request.form.get('role'),
                request.form.get('description'),
                request.form.get('location'),
                request.form.get('package'),
                float(request.form.get('min_cgpa', 0)),
                int(request.form.get('max_backlogs', 0)),
                request.form.get('allowed_branch', 'ALL'),
                request.form.get('deadline')
            ))
            conn.commit()
            flash('Job posted successfully!', 'success')
            return redirect(url_for('company_dashboard'))
    return render_template('post_job.html', company=company)


@app.route('/company/update-application/<int:app_id>', methods=['POST'])
@login_required
@role_required('company')
def update_application(app_id):
    new_status = request.form.get('status')
    valid = ('SHORTLISTED', 'REJECTED', 'OFFERED', 'PENDING')
    if new_status not in valid:
        flash('Invalid status.', 'danger')
        return redirect(url_for('company_dashboard') + '#appsTab')
    with get_db() as conn:
        app_row = conn.execute("SELECT * FROM APPLICATION WHERE ApplicationID=?", (app_id,)).fetchone()
        if not app_row:
            flash('Application not found.', 'danger')
            return redirect(url_for('company_dashboard') + '#appsTab')
        old_status = app_row['Status']
        conn.execute(
            "UPDATE APPLICATION SET Status=? WHERE ApplicationID=?",
            (new_status, app_id)
        )
        conn.commit()
        log_audit('APPLICATION', app_id, 'STATUS_CHANGE', old_status, new_status)
        # Auto-mark placed if offered
        if new_status == 'OFFERED':
            conn.execute(
                "UPDATE STUDENT SET PlacementStatus='PLACED' WHERE StudentID=?",
                (app_row['StudentID'],)
            )
            conn.commit()
        # Revert placement status if un-offering
        if old_status == 'OFFERED' and new_status != 'OFFERED':
            conn.execute(
                "UPDATE STUDENT SET PlacementStatus='UNPLACED' WHERE StudentID=?",
                (app_row['StudentID'],)
            )
            conn.commit()

    status_labels = {
        'SHORTLISTED': '✅ Shortlisted',
        'OFFERED':     '🎉 Offer Extended',
        'REJECTED':    '❌ Rejected',
        'PENDING':     '🔄 Reset to Pending',
    }
    flash(f'{status_labels.get(new_status, new_status)} successfully.', 'success')
    return redirect(url_for('company_dashboard') + '#appsTab')


# ── Coordinator ──

@app.route('/coordinator/dashboard')
@login_required
@role_required('coordinator')
def coordinator_dashboard():
    with get_db() as conn:
        students  = conn.execute("SELECT * FROM STUDENT ORDER BY Name").fetchall()
        companies = conn.execute("SELECT * FROM COMPANY ORDER BY CompanyName").fetchall()
        jobs      = conn.execute("""
            SELECT J.*, C.CompanyName FROM JOB J
            JOIN COMPANY C ON J.CompanyID=C.CompanyID
            ORDER BY J.PostedAt DESC
        """).fetchall()
        apps = conn.execute("""
            SELECT A.*, S.Name as StudentName, S.CGPA, S.Branch,
                   J.Role, C.CompanyName
            FROM APPLICATION A
            JOIN STUDENT S ON A.StudentID=S.StudentID
            JOIN JOB J ON A.JobID=J.JobID
            JOIN COMPANY C ON J.CompanyID=C.CompanyID
            ORDER BY A.ApplicationDate DESC
        """).fetchall()
        audit_log = conn.execute("""
            SELECT L.*, U.Email FROM PLACEMENT_AUDIT_LOG L
            LEFT JOIN USERS U ON L.ChangedBy=U.UserID
            ORDER BY L.ChangedAt DESC LIMIT 50
        """).fetchall()
        stats = {
            'total_students':  conn.execute("SELECT COUNT(*) as c FROM STUDENT").fetchone()['c'],
            'placed_students': conn.execute("SELECT COUNT(*) as c FROM STUDENT WHERE PlacementStatus='PLACED'").fetchone()['c'],
            'total_companies': conn.execute("SELECT COUNT(*) as c FROM COMPANY").fetchone()['c'],
            'active_jobs':     conn.execute("SELECT COUNT(*) as c FROM JOB WHERE IsActive=1").fetchone()['c'],
            'total_apps':      conn.execute("SELECT COUNT(*) as c FROM APPLICATION").fetchone()['c'],
        }
    return render_template(
        'coordinator_dashboard.html',
        students=students, companies=companies, jobs=jobs,
        applications=apps, audit_log=audit_log, stats=stats
    )


@app.route('/coordinator/toggle-job/<int:job_id>', methods=['POST'])
@login_required
@role_required('coordinator')
def toggle_job(job_id):
    with get_db() as conn:
        job = conn.execute("SELECT IsActive FROM JOB WHERE JobID=?", (job_id,)).fetchone()
        new_val = 0 if job['IsActive'] else 1
        conn.execute("UPDATE JOB SET IsActive=? WHERE JobID=?", (new_val, job_id))
        conn.commit()
    flash('Job status toggled.', 'info')
    return redirect(url_for('coordinator_dashboard'))


# ── Public Jobs ──

@app.route('/jobs')
def jobs():
    branch_filter = request.args.get('branch', '')
    min_cgpa      = request.args.get('min_cgpa', '')
    search        = request.args.get('search', '')
    with get_db() as conn:
        query = """
            SELECT J.*, C.CompanyName, C.Industry FROM JOB J
            JOIN COMPANY C ON J.CompanyID=C.CompanyID
            WHERE J.IsActive=1
        """
        params = []
        if branch_filter:
            query += " AND (J.AllowedBranch='ALL' OR J.AllowedBranch=?)"
            params.append(branch_filter)
        if min_cgpa:
            query += " AND J.MinCGPA <= ?"
            params.append(float(min_cgpa))
        if search:
            query += " AND (J.Role LIKE ? OR C.CompanyName LIKE ? OR J.Location LIKE ?)"
            params += [f'%{search}%', f'%{search}%', f'%{search}%']
        query += " ORDER BY J.PostedAt DESC"
        jobs_list = conn.execute(query, params).fetchall()
    return render_template('jobs.html', jobs=jobs_list, branch_filter=branch_filter,
                           min_cgpa=min_cgpa, search=search)


@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
    with get_db() as conn:
        job = conn.execute("""
            SELECT J.*, C.CompanyName, C.Industry, C.Website, C.Description as CompanyDesc
            FROM JOB J JOIN COMPANY C ON J.CompanyID=C.CompanyID
            WHERE J.JobID=?
        """, (job_id,)).fetchone()
        if not job:
            flash('Job not found.', 'danger')
            return redirect(url_for('jobs'))
        student = None
        already_applied = False
        is_eligible = None
        reasons = []
        if session.get('role') == 'student':
            student = conn.execute(
                "SELECT * FROM STUDENT WHERE UserID=?", (session['user_id'],)
            ).fetchone()
            if student:
                is_eligible, reasons = check_eligibility(dict(student), dict(job))
                already_applied = conn.execute(
                    "SELECT 1 FROM APPLICATION WHERE StudentID=? AND JobID=?",
                    (student['StudentID'], job_id)
                ).fetchone() is not None
    return render_template(
        'job_detail.html', job=job, student=student,
        is_eligible=is_eligible, reasons=reasons, already_applied=already_applied
    )


@app.context_processor
def inject_helpers():
    return dict(check_eligibility=check_eligibility)


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
