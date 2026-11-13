# ⚡ TalentHub — Campus Placement Management Portal

> A beautiful, full-featured college placement management system built with **Python + Flask + SQLite**. Connects students, companies, and placement coordinators in one elegant platform.

---

## 🌟 Features

### 👩‍🎓 For Students
- Register and build your profile (CGPA, branch, backlogs)
- Browse all active job listings with live eligibility checks
- **Instant eligibility feedback** — see exactly why you qualify or don't
- Apply to jobs with one click
- Track all application statuses in real-time (Pending → Shortlisted → Offered)

### 🏢 For Companies
- Post jobs with custom eligibility criteria (min CGPA, backlogs, branch)
- Review all applicants with their academic profiles
- **Direct action buttons** — Shortlist, Reject, or Send Offer per applicant
- Filter applications by status (Pending / Shortlisted / Offered / Rejected)
- Extending an offer automatically marks the student as PLACED

### 🛡️ For Coordinators (Admin)
- Full oversight: view all students, companies, jobs, and applications
- Activate / deactivate job listings
- Complete **Audit Log** — append-only trail of every status change for dispute resolution

---

## 🗄️ Database Schema (SQLite — 3NF Normalized)

```
USERS          → UserID, Email, Password, Role
STUDENT        → StudentID, UserID(FK), Name, Branch, CGPA, ActiveBacklogs, PlacementStatus
COMPANY        → CompanyID, UserID(FK), CompanyName, Industry, Website, Description
JOB            → JobID, CompanyID(FK), Role, MinCGPA, MaxActiveBacklogs, AllowedBranch, ...
APPLICATION    → ApplicationID, StudentID(FK), JobID(FK), Status, ApplicationDate
PLACEMENT_AUDIT_LOG → LogID, EntityType, EntityID, Action, OldValue, NewValue, ChangedBy
```

---

## 🔐 Eligibility Algorithm

Based on **Comprehensive Rule Evaluation** — checks ALL rules and returns every failure reason:

| Rule | Check |
|------|-------|
| Placement Policy | Student must not already be PLACED |
| CGPA | Student CGPA ≥ Job MinCGPA |
| Backlogs | Student ActiveBacklogs ≤ Job MaxActiveBacklogs |
| Branch | Student Branch matches Job AllowedBranch (or job allows ALL) |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Flask (install below)

### Installation

```bash
# 1. Navigate to project folder
cd Talenthub_anti

# 2. Install dependencies
pip install flask

# 3. Run the app
python app.py
```

### Or just double-click `run.bat` *(Windows)*

---

## 🌐 Open in Browser

```
http://127.0.0.1:5000
```

Press **Ctrl + C** in the terminal to stop the server.

---

## 🔑 Demo Login Credentials

| Role | Email | Password |
|------|-------|----------|
| **Student** | `alice@student.in` | `student123` |
| **Student** | `bob@student.in` | `student123` |
| **Company** | `google@company.in` | `company123` |
| **Company** | `microsoft@company.in` | `company123` |
| **Coordinator** | `admin@talenthub.in` | `admin123` |

---

## 📁 Project Structure

```
Talenthub_anti/
│
├── app.py                      # Main Flask application (all routes + logic)
├── talenthub.db                # SQLite database (auto-created on first run)
├── requirements.txt            # Python dependencies
├── run.bat                     # One-click Windows launcher
├── README.md                   # This file
│
└── templates/
    ├── base.html               # Base layout (navbar, footer, global CSS)
    ├── index.html              # Landing page (hero, stats, job cards)
    ├── login.html              # Sign in page
    ├── register.html           # Student / Company registration
    ├── jobs.html               # Public job board with filters
    ├── job_detail.html         # Job detail + live eligibility check
    ├── student_dashboard.html  # Student: browse jobs, apply, track applications
    ├── student_profile.html    # Student: edit profile
    ├── company_dashboard.html  # Company: manage jobs + accept/reject applicants
    ├── post_job.html           # Company: post a new job
    └── coordinator_dashboard.html  # Admin: full oversight + audit log
```

---

## 🏢 How to Accept / Reject Applications (Company)

1. Login as a Company
2. Go to **Dashboard → Applications tab**
3. Each applicant card shows clear action buttons:
   - 🔵 **Shortlist** — Move to shortlist round
   - ❌ **Reject** — Decline the application
   - 🏆 **Send Offer** *(appears after Shortlisting)* — Extend a formal offer; student is auto-marked as **PLACED**
   - ↩️ **Undo Rejection** — Reset a rejected application back to Pending

---

## 🔒 Security Design

| Feature | Implementation |
|---------|---------------|
| Authentication | Session-based with SHA-256 password hashing |
| Authorization | Role-based access control (RBAC) via decorators |
| Data Protection | Service-layer field masking — companies see only academic data |
| Audit Trail | Append-only `PLACEMENT_AUDIT_LOG` table for dispute resolution |
| DB Integrity | Foreign key constraints, CHECK constraints, UNIQUE constraints |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3 + Flask 3.x |
| Database | SQLite 3 (via Python `sqlite3` stdlib) |
| Frontend | Bootstrap 5.3 + Bootstrap Icons |
| Fonts | Inter + Syne (Google Fonts) |
| Animations | Animate.css |
| Auth | Flask Sessions + SHA-256 |

> No Docker. No external database server. Just Python.

---

## 📝 License

Built for educational purposes — TalentHub Campus Placement Portal © 2026.
