import streamlit as st
from pyairtable import Api
import pandas as pd
from datetime import datetime, timedelta, timezone
import resend
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# Page config
st.set_page_config(
    page_title="Lumiere Mentor Portal",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Airtable connection
@st.cache_resource
def get_airtable_api():
    api = Api(st.secrets["AIRTABLE_API_KEY"])
    return api

@st.cache_resource
def get_tables():
    api = get_airtable_api()
    base = api.base(st.secrets["AIRTABLE_BASE_ID"])
    return {
        "students": base.table(st.secrets["STUDENT_TABLE"]),
        "deadlines": base.table(st.secrets["DEADLINES_TABLE"]),
        "mentors": base.table(st.secrets["MENTOR_TABLE"]),
        "progress": base.table(st.secrets["PROGRESS_TABLE"])
    }

# Magic Link Authentication
def get_serializer():
    return URLSafeTimedSerializer(st.secrets["MAGIC_LINK_SECRET"])

def generate_magic_token(email):
    """Generate a signed token containing the email"""
    serializer = get_serializer()
    return serializer.dumps(email, salt="magic-link")

def verify_magic_token(token, max_age=3600):
    """Verify token and return email if valid (default 1 hour expiry)"""
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt="magic-link", max_age=max_age)
        return email
    except (SignatureExpired, BadSignature):
        return None

def send_magic_link(email, mentor_name):
    """Send magic link email to mentor"""
    resend.api_key = st.secrets["RESEND_API_KEY"]

    token = generate_magic_token(email)
    # Get the base URL from secrets or construct from request
    base_url = st.secrets.get("APP_URL", "http://localhost:8501")
    magic_link = f"{base_url}?token={token}"

    try:
        r = resend.Emails.send({
            "from": st.secrets.get("FROM_EMAIL", "Mentor Portal <onboarding@resend.dev>"),
            "to": [email],
            "subject": "Your Mentor Portal Login Link",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #BE1E2D;">Welcome to the Lumiere Mentor Portal</h2>
                <p>Hi {mentor_name},</p>
                <p>Click the button below to access your mentor dashboard:</p>
                <p style="margin: 30px 0;">
                    <a href="{magic_link}"
                       style="background: linear-gradient(135deg, #BE1E2D 0%, #8B1520 100%);
                              color: white;
                              padding: 12px 30px;
                              text-decoration: none;
                              border-radius: 6px;
                              display: inline-block;">
                        Access Portal
                    </a>
                </p>
                <p style="color: #64748B; font-size: 14px;">
                    This link will expire in 1 hour for security reasons.<br>
                    If you didn't request this link, you can safely ignore this email.
                </p>
            </div>
            """
        })
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# Field mappings (adjust these to match your exact Airtable field names)
STUDENT_FIELDS = {
    "name": "Student Cohort Application Tracker",
    "mentor": "Mentor Name",
    "research_area": "Research Area - First Preference",
    "city": "City of Residence",
    "graduation_year": "Graduation Year",
    "mentor_confirmation": "Mentor Confirmation",
    "background_shared": "OB: Mentor Background Shared",
    "expected_meetings": "Number of Expected Meetings - Student/Mentor",
    "completed_meetings": "Total No. of Meetings Completed (Accounted for 1 No Show)",
    "notes_summary": "Mentor-Student Notes Summary",
    "hours_recorded": "[Current + Archived] No. of Hours Recorded",
    "foundation_student": "Foundation Student",
    "tuition_paid": "OB: Full Tuition Paid",
    "program_manager_email": "Program Manager Email",
    "program_manager_name": "Program Manager (Text)",
    "revised_final_paper_due": "PM: Student's Revised Final Paper - Due date",
    "student_no_shows": "[Current + Archived] No. of Student No Shows in Mentor Meetings",
    "reason_for_interest": "Reason for Interest in Areas",
    "white_label": "White Label or Partner Payment Program",
    "previous_coursework": "Previous Coursework",
    "interview_notes": "Interview Notes For The Mentor",
    "preferred_name": "Preferred Name",
    "student_status": "PM: Student Status in Program",
    "current_grade": "Current Grade in School",
    "country": "Country of Residence (single select)",
    "writing_coach_name": "Writing Coach Name (Text)",
    "writing_coach_email": "Writing Coach Email",
    "publication_specialist_name": "Publication Specialist (Text)",
    "publication_specialist_email": "Publication Specialist Email",
    "publication_marker": "publication marker",
    "publication_status": "PS: Latest Publication Outcome - Latest",
    "mentor_hourly_rate": "FN: Mentor Hourly Base Rate",
    "evaluation_form_link": "Evaluation form link",
    "revised_paper_upload": "Revised Final Paper upload (from Mentor-Student Progress Up Date)",
    "mentor_payment_status": "FN: Mentor Payment Status (Total)",
    "payment_date_1": "FN: 1st Payment date to Mentor",
    "payment_date_2": "FN: 2nd Payment date to Mentor",
    "payment_date_3": "FN: 3rd Pay Date"
}

# Only fetch the fields actually used by _parse_student_record.
# This prevents Airtable from returning every column and dramatically reduces payload size.
_STUDENT_FETCH_FIELDS = ["Mentor Email"] + list(STUDENT_FIELDS.values())

DEADLINE_FIELDS = {
    "name": "Deadline Name",
    "type": "Deadline Type",
    "due_date": "Due Date (in use, updated to reflect student's timeline)",
    "status": "Deadline Status",
    "date_submitted": "Date Submitted",
    "student_link": "Student Application & Cohort Tracker"
}

# Submission file fields (these may be attachments or lookups)
SUBMISSION_FIELDS = [
    "Syllabus Submission (From Mentor)",
    "Research Question",
    "Research Proposal",
    "Research Outline",
    "Milestone",
    "Final Paper",
    "Revised Final Paper",
    "Target Publication Submission"
]

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #333333;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666666;
        margin-bottom: 2rem;
    }
    .student-card {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
        border-left: 4px solid #BE1E2D;
    }
    .status-confirmed {
        background-color: #ECFDF5;
        color: #065F46;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .status-pending {
        background-color: #FFFBEB;
        color: #92400E;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .status-not-sent {
        background-color: #FEF2F2;
        color: #991B1B;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .metric-card {
        background: linear-gradient(135deg, #BE1E2D 0%, #8B1520 100%);
        border-radius: 12px;
        padding: 1.5rem;
        color: white;
    }
    .deadline-submitted {
        background-color: #ECFDF5;
        border-left: 4px solid #10B981;
    }
    .deadline-pending {
        background-color: #FFFBEB;
        border-left: 4px solid #F59E0B;
    }
    .deadline-overdue {
        background-color: #FEF2F2;
        border-left: 4px solid #EF4444;
    }
    .preview-banner {
        background-color: #FFFBEB;
        border: 1px solid #F59E0B;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        color: #92400E;
    }
    /* Dark sidebar */
    [data-testid="stSidebar"] {
        background-color: #1A1A2E;
        color: #FFFFFF;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stCaption p {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.2);
    }
    [data-testid="stSidebar"] .stButton button {
        background-color: rgba(255,255,255,0.1);
        color: #FFFFFF !important;
        border: 1px solid rgba(255,255,255,0.3);
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: rgba(255,255,255,0.2);
        border-color: rgba(255,255,255,0.5);
    }
    /* Rectangular nav style for sidebar radio */
    [data-testid="stSidebar"] .stRadio > div {
        gap: 0.25rem !important;
    }
    [data-testid="stSidebar"] .stRadio > div > label {
        background-color: transparent !important;
        border-radius: 6px !important;
        padding: 0.6rem 1rem !important;
        margin: 0 !important;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    [data-testid="stSidebar"] .stRadio > div > label:hover {
        background-color: rgba(255,255,255,0.1) !important;
    }
    [data-testid="stSidebar"] .stRadio > div > label[data-checked="true"] {
        background-color: rgba(255,255,255,0.15) !important;
        border-left: 3px solid #DC1E35 !important;
    }
    /* Hide radio circle */
    [data-testid="stSidebar"] .stRadio > div > label > div:first-child {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "mentor_name" not in st.session_state:
    st.session_state.mentor_name = None
if "mentor_email" not in st.session_state:
    st.session_state.mentor_email = None
if "is_preview" not in st.session_state:
    st.session_state.is_preview = False
if "magic_link_sent" not in st.session_state:
    st.session_state.magic_link_sent = False
if "team_unlocked" not in st.session_state:
    st.session_state.team_unlocked = False
if "selected_student_name" not in st.session_state:
    st.session_state.selected_student_name = None
if "selected_prospective_student" not in st.session_state:
    st.session_state.selected_prospective_student = None

# Helper functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_mentor_by_email(email):
    """Find mentor by email in Mentor Table"""
    tables = get_tables()
    try:
        records = tables["mentors"].all(formula=f"LOWER({{Email}}) = LOWER('{email}')")
        if records:
            record = records[0]
            contractor_status = record["fields"].get("Contractor/Volunteer Status", [])
            if not isinstance(contractor_status, list):
                contractor_status = [contractor_status]
            return {
                "id": record["id"],
                "name": record["fields"].get("Name") or record["fields"].get("Mentor Name", ""),
                "email": record["fields"].get("Email", ""),
                "is_foundation_volunteer": "Foundation Volunteer" in contractor_status
            }
    except Exception as e:
        st.error(f"Error fetching mentor: {e}")
    return None

def _parse_student_record(record):
    """Parse a raw Airtable student record into a dict. Returns None if parsing fails."""
    def unwrap(val, default=""):
        if isinstance(val, list):
            val = val[0] if val else default
        val = val if val is not None else default
        if isinstance(val, str):
            val = val.strip("[]'\"")
        return val

    fields = record["fields"]
    mentor_emails_raw = fields.get("Mentor Email", [])
    if not isinstance(mentor_emails_raw, list):
        mentor_emails_raw = [mentor_emails_raw]

    return {
        "id": record["id"],
        "_mentor_emails": [e.strip().lower() for e in mentor_emails_raw if e],
        "name": fields.get(STUDENT_FIELDS["name"], "Unknown"),
        "research_area": fields.get(STUDENT_FIELDS["research_area"], ""),
        "city": fields.get(STUDENT_FIELDS["city"], ""),
        "graduation_year": fields.get(STUDENT_FIELDS["graduation_year"], ""),
        "mentor_confirmation": fields.get(STUDENT_FIELDS["mentor_confirmation"], ""),
        "background_shared": fields.get(STUDENT_FIELDS["background_shared"], ""),
        "expected_meetings": fields.get(STUDENT_FIELDS["expected_meetings"], 0),
        "completed_meetings": fields.get(STUDENT_FIELDS["completed_meetings"], 0),
        "notes_summary": fields.get(STUDENT_FIELDS["notes_summary"], ""),
        "hours_recorded": fields.get(STUDENT_FIELDS["hours_recorded"], ""),
        "foundation_student": fields.get(STUDENT_FIELDS["foundation_student"], ""),
        "tuition_paid": fields.get(STUDENT_FIELDS["tuition_paid"], ""),
        "program_manager_email": unwrap(fields.get(STUDENT_FIELDS["program_manager_email"], "")),
        "program_manager_name": unwrap(fields.get(STUDENT_FIELDS["program_manager_name"], "")),
        "revised_final_paper_due": unwrap(fields.get(STUDENT_FIELDS["revised_final_paper_due"], "")),
        "student_no_shows": unwrap(fields.get(STUDENT_FIELDS["student_no_shows"], 0), default=0),
        "reason_for_interest": unwrap(fields.get(STUDENT_FIELDS["reason_for_interest"], "")),
        "white_label": unwrap(fields.get(STUDENT_FIELDS["white_label"], "")),
        "previous_coursework": unwrap(fields.get(STUDENT_FIELDS["previous_coursework"], "")),
        "interview_notes": unwrap(fields.get(STUDENT_FIELDS["interview_notes"], "")),
        "preferred_name": fields.get(STUDENT_FIELDS["preferred_name"], ""),
        "student_status": fields.get(STUDENT_FIELDS["student_status"], ""),
        "current_grade": fields.get(STUDENT_FIELDS["current_grade"], ""),
        "country": unwrap(fields.get(STUDENT_FIELDS["country"], "")),
        "writing_coach_name": fields.get(STUDENT_FIELDS["writing_coach_name"], ""),
        "writing_coach_email": unwrap(fields.get(STUDENT_FIELDS["writing_coach_email"], "")),
        "publication_specialist_name": fields.get(STUDENT_FIELDS["publication_specialist_name"], ""),
        "publication_specialist_email": unwrap(fields.get(STUDENT_FIELDS["publication_specialist_email"], "")),
        "publication_marker": unwrap(fields.get(STUDENT_FIELDS["publication_marker"], "")),
        "publication_status": unwrap(fields.get(STUDENT_FIELDS["publication_status"], "")),
        "mentor_hourly_rate": fields.get(STUDENT_FIELDS["mentor_hourly_rate"], None),
        "evaluation_form_link": unwrap(fields.get(STUDENT_FIELDS["evaluation_form_link"], "")),
        "revised_paper_upload": fields.get(STUDENT_FIELDS["revised_paper_upload"], []),
        "mentor_payment_status": unwrap(fields.get(STUDENT_FIELDS["mentor_payment_status"], "")),
        "payment_date_1": unwrap(fields.get(STUDENT_FIELDS["payment_date_1"], "")),
        "payment_date_2": unwrap(fields.get(STUDENT_FIELDS["payment_date_2"], "")),
        "payment_date_3": unwrap(fields.get(STUDENT_FIELDS["payment_date_3"], ""))
    }

@st.cache_data(ttl=300)
def get_students_for_mentor(mentor_email):
    """Fetch confirmed students for a specific mentor directly from Airtable."""
    tables = get_tables()
    email_lower = mentor_email.strip().lower()
    try:
        formula = (
            f'AND('
            f'{{Student Confirmed & Launched}} = "Yes", '
            f'FIND("{email_lower}", LOWER(ARRAYJOIN({{Mentor Email}}, ",")))'
            f')'
        )
        records = tables["students"].all(formula=formula, fields=_STUDENT_FETCH_FIELDS)
        return [_parse_student_record(r) for r in records]
    except Exception as e:
        st.error(f"Error fetching students: {e}")
        return []

@st.cache_data(ttl=300)
def get_prospective_students(mentor_email):
    """Fetch prospective students for a specific mentor directly from Airtable."""
    tables = get_tables()
    email_lower = mentor_email.strip().lower()
    try:
        formula = (
            f'AND('
            f'{{Written Confirmation/Participation Decision}} != "No", '
            f'FIND("True", ARRAYJOIN({{Upcoming Cohort (Cohort Table)}})), '
            f'FIND("{email_lower}", LOWER(ARRAYJOIN({{Mentor Email}}, ",")))'
            f')'
        )
        records = tables["students"].all(formula=formula, fields=_STUDENT_FETCH_FIELDS)
        return [_parse_student_record(r) for r in records]
    except Exception as e:
        st.error(f"Error fetching prospective students: {e}")
        return []

@st.cache_data(ttl=300)
def get_deadlines_for_student(student_name):
    """Get all deadlines for a specific student"""
    tables = get_tables()
    try:
        # Search for student name in Deadline Name field
        formula = f"FIND('{student_name.split('|')[0].strip()}', {{Deadline Name}})"
        records = tables["deadlines"].all(formula=formula)

        deadlines = []
        for record in records:
            fields = record["fields"]

            # Collect submission files
            submissions = {}
            for field in SUBMISSION_FIELDS:
                value = fields.get(field)
                if value:
                    submissions[field] = value

            deadlines.append({
                "id": record["id"],
                "name": fields.get(DEADLINE_FIELDS["name"], ""),
                "type": fields.get(DEADLINE_FIELDS["type"], ""),
                "due_date": fields.get(DEADLINE_FIELDS["due_date"], ""),
                "status": fields.get(DEADLINE_FIELDS["status"], ""),
                "date_submitted": fields.get(DEADLINE_FIELDS["date_submitted"], ""),
                "submissions": submissions
            })

        # Sort by due date
        deadlines.sort(key=lambda x: x["due_date"] or "9999-99-99")
        return deadlines
    except Exception as e:
        st.error(f"Error fetching deadlines: {e}")
        return []

@st.cache_data(ttl=300)
def get_meeting_notes_for_student(student_name):
    """Get meeting notes from the progress/evaluations table for a student"""
    tables = get_tables()
    try:
        name_part = student_name.split('|')[0].strip()
        formula = f"AND(FIND('{name_part}', {{Mentor Student Meeting Key}}), {{Type of Record}} = 'Mentor Update')"
        records = tables["progress"].all(formula=formula)

        notes = []
        for record in records:
            fields = record["fields"]
            notes.append({
                "date": fields.get("Date of meeting", ""),
                "notes": fields.get("Meeting Notes Between Mentor & Student", "")
            })

        notes.sort(key=lambda x: x["date"] or "0000-00-00", reverse=True)
        return notes
    except Exception as e:
        st.error(f"Error fetching meeting notes: {e}")
        return []

@st.cache_data(ttl=300)
def get_eval_feedback_for_student(student_name):
    """Get Evaluation & Feedback records from the progress table for a student"""
    tables = get_tables()
    try:
        name_part = student_name.split('|')[0].strip()
        formula = f"AND(FIND('{name_part}', {{Mentor Student Meeting Key}}), {{Type of Record}} = 'Evaluation & Feedback')"
        records = tables["progress"].all(formula=formula)

        items = []
        for record in records:
            fields = record["fields"]
            created_time = record.get("createdTime", "")

            # Get attachment from "MFFF - Evaluation form" field
            attachments = []
            eval_form = fields.get("MFFF - Evaluation form")
            if isinstance(eval_form, list):
                for att in eval_form:
                    if isinstance(att, dict) and att.get("url"):
                        attachments.append({"filename": att.get("filename", "Download"), "url": att["url"]})

            items.append({
                "created_time": created_time,
                "attachments": attachments,
            })

        items.sort(key=lambda x: x["created_time"] or "0000-00-00", reverse=True)
        return items
    except Exception as e:
        st.error(f"Error fetching evaluations: {e}")
        return []

def format_duration(value):
    """Format a duration value (seconds from Airtable API) as h:mm"""
    if not value and value != 0:
        return "N/A"
    # If already a formatted string like "1:40", return as-is
    if isinstance(value, str):
        return value if value else "N/A"
    # Airtable returns duration fields as seconds
    try:
        total_seconds = int(value)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}:{minutes:02d}"
    except (ValueError, TypeError):
        return str(value)

def format_date(date_str):
    """Format date string for display"""
    if not date_str:
        return "Not set"
    # Handle list values (e.g. from Airtable lookup fields)
    if isinstance(date_str, list):
        date_str = date_str[0] if date_str else ""
    if not date_str:
        return "Not set"
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        day = date_obj.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"{date_obj.strftime('%B')} {day}{suffix}, {date_obj.year}"
    except:
        return date_str

def format_datetime_ist(date_str):
    """Format an ISO datetime string to a friendly format in IST (UTC+5:30)"""
    if not date_str:
        return "Not set"
    # Handle list values (e.g. from Airtable lookup fields)
    if isinstance(date_str, list):
        date_str = date_str[0] if date_str else ""
    if not date_str:
        return "Not set"
    try:
        # Parse ISO format (e.g. '2026-01-31T18:49:57.000Z')
        date_str = date_str.strip("'\"")
        date_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        # Convert from UTC to IST (UTC+5:30)
        ist = timezone(timedelta(hours=5, minutes=30))
        date_obj = date_obj.replace(tzinfo=timezone.utc).astimezone(ist)
        return date_obj.strftime("%b %#d, %Y %#I:%M %p IST")
    except:
        # Fallback: try plain date format
        return format_date(date_str)

def format_notes_summary(text):
    """Parse and format notes summary text for better display"""
    if not text:
        return ""

    import re

    lines = text.strip().split('\n')
    formatted_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect headers (ALL CAPS lines or lines ending with colon)
        if line.isupper() and len(line) > 2:
            # Convert ALL CAPS to Title Case for headers
            formatted_lines.append(f"**{line.title()}**")
        elif line.endswith(':') and len(line) < 50:
            # Lines ending with colon are likely section headers
            formatted_lines.append(f"**{line}**")
        elif line.startswith(('-', '•', '*', '–')):
            # Already a bullet point
            formatted_lines.append(line)
        elif re.match(r'^\d+[\.\)]\s', line):
            # Numbered list item
            formatted_lines.append(line)
        else:
            formatted_lines.append(line)

    return '\n\n'.join(formatted_lines)

def due_date_sort_key(s):
    """Sort key: upcoming soonest first, then overdue, then no date."""
    today = datetime.now().date()
    raw = s.get("revised_final_paper_due")
    if not raw:
        return (2, "9999-99-99")
    try:
        d = datetime.strptime(raw, "%Y-%m-%d").date()
        if d >= today:
            return (0, raw)   # upcoming → top
        else:
            return (1, raw)   # overdue → middle
    except:
        return (2, "9999-99-99")

def normalize_tuition_paid(value):
    """Collapse various tuition paid values to Yes or No"""
    if not value or value == "—":
        return value
    v = value.strip().lower()
    if v == "yes":
        return "Yes"
    if v == "no":
        return "No"
    # Check negative signals before positive (so "pending payment" doesn't hit "pay")
    if "pending" in v or "clarification" in v:
        return "No"
    # Positive signals: paid, will pay, etc.
    if "paid" in v or "pay" in v:
        return "Yes"
    return "No"

def is_overdue(due_date_str, status):
    """Check if deadline is overdue"""
    if status == "Submitted":
        return False
    if not due_date_str:
        return False
    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
        return due_date < datetime.now()
    except:
        return False

# Check for magic link token in URL
def check_magic_link_token():
    query_params = st.query_params
    if "token" in query_params and not st.session_state.authenticated:
        token = query_params["token"]
        email = verify_magic_token(token)
        if email:
            mentor = get_mentor_by_email(email)
            if mentor:
                st.session_state.authenticated = True
                st.session_state.mentor_name = mentor["name"]
                st.session_state.mentor_email = mentor["email"]
                st.session_state.is_foundation_volunteer = mentor.get("is_foundation_volunteer", False)
                st.session_state.is_preview = False
                # Clear the token from URL
                st.query_params.clear()
                st.rerun()
        else:
            st.error("This login link has expired or is invalid. Please request a new one.")
            st.query_params.clear()

# LOGIN PAGE
def show_login_page():
    st.markdown("""
    <style>
        .stApp {
            background-color: #1A1A2E;
        }
        /* Hide Streamlit chrome */
        #MainMenu, header, footer { visibility: hidden; }
        /* Push card down for vertical centering */
        .block-container {
            padding-top: 10vh !important;
            max-width: 100% !important;
        }
        /* White card on the middle column
           Covers both old ("column") and new ("stColumn") Streamlit testid values */
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2),
        [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2) {
            background: white !important;
            border-radius: 16px !important;
            padding: 2.5rem !important;
            box-shadow: 0 20px 60px rgba(0,0,0,0.4) !important;
        }
        /* Text colours inside card */
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) p,
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) label,
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) span,
        [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2) p,
        [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2) label,
        [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2) span {
            color: #1A1A2E !important;
        }
        /* Input field */
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) input,
        [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2) input {
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            color: #1A1A2E !important;
            background: white !important;
        }
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) input::placeholder,
        [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2) input::placeholder {
            color: #94A3B8 !important;
        }
        /* Buttons — broad fallback covers both variants */
        [data-testid="stFormSubmitButton"] > button,
        .stButton > button {
            background-color: #DC1E35 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }
        [data-testid="stFormSubmitButton"] > button:hover,
        .stButton > button:hover {
            background-color: #B01829 !important;
        }
        [data-testid="stFormSubmitButton"] > button p,
        .stButton > button p {
            color: white !important;
        }
        /* Divider inside card */
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) hr,
        [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2) hr {
            border-color: #E2E8F0 !important;
        }
        /* Expander (Team Access) inside card */
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) details,
        [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2) details {
            background: #F8FAFC !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
        }
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) details summary,
        [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:nth-child(2) details summary *,
        [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2) details summary,
        [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2) details summary * {
            color: #1A1A2E !important;
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Logo + header inside the card
        import base64
        with open("assets/lumiere_logo.png", "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<div style="text-align:center; margin-bottom:0.5rem;">'
            f'<img src="data:image/png;base64,{logo_b64}" width="220">'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<h2 style="text-align:center; color:#1A1A2E; font-size:1.5rem; font-weight:700; margin:0.5rem 0 0.25rem;">Mentor Portal</h2>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<p style="text-align:center; color:#94A3B8; font-size:0.82rem; margin-bottom:1.5rem; line-height:1.5;">Track your matched students, stay on top of their deadlines and submissions, and get a clear view of everything happening across your program.</p>',
            unsafe_allow_html=True
        )

        # Check if magic link was just sent
        if st.session_state.magic_link_sent:
            st.success("Check your email! We've sent you a magic link to access the portal.")
            st.info("The link will expire in 1 hour.")
            if st.button("Send another link"):
                st.session_state.magic_link_sent = False
                st.rerun()
        else:
            # Email label + form
            st.markdown(
                '<p style="font-size:0.75rem; font-weight:600; letter-spacing:0.08em; color:#64748B; margin-bottom:0.25rem; text-transform:uppercase;">EMAIL ADDRESS</p>',
                unsafe_allow_html=True
            )
            st.markdown(
                '<p style="font-size:0.8rem; color:#94A3B8; margin-bottom:0.5rem;">Enter the email address that you\'ve shared with our team.</p>',
                unsafe_allow_html=True
            )
            with st.form("login_form"):
                email = st.text_input("Email Address", label_visibility="collapsed", placeholder="your.email@example.com")
                submitted = st.form_submit_button("Send Magic Link", use_container_width=True)

                if submitted and email:
                    mentor = get_mentor_by_email(email)
                    if mentor:
                        if send_magic_link(mentor["email"], mentor["name"]):
                            st.session_state.magic_link_sent = True
                            st.rerun()
                    else:
                        st.error("Email not found. Please check your email address.")

        # Team preview access - small link that gates behind admin key
        st.markdown("---")
        if st.session_state.team_unlocked:
            st.markdown("#### Team Preview Mode")
            st.caption("Preview any mentor's portal view")
            with st.form("preview_form"):
                preview_email = st.text_input("Mentor's Email", placeholder="Enter mentor email to preview")
                preview_submitted = st.form_submit_button("Preview as Mentor", use_container_width=True)

                if preview_submitted:
                    mentor = get_mentor_by_email(preview_email)
                    if mentor:
                        st.session_state.authenticated = True
                        st.session_state.mentor_name = mentor["name"]
                        st.session_state.mentor_email = mentor["email"]
                        st.session_state.is_foundation_volunteer = mentor.get("is_foundation_volunteer", False)
                        st.session_state.is_preview = True
                        st.rerun()
                    else:
                        st.error("Mentor email not found.")
        else:
            with st.expander("Team Access"):
                st.markdown(
                    '<p style="font-size:0.8rem; color:#64748B; margin-bottom:0.75rem;">For Lumiere team members only. Enter your admin key to preview the portal as any mentor.</p>',
                    unsafe_allow_html=True
                )
                with st.form("team_unlock_form"):
                    admin_key = st.text_input("Admin Key", type="password", placeholder="Enter admin key")
                    unlock_submitted = st.form_submit_button("Unlock", use_container_width=True)

                    if unlock_submitted:
                        if admin_key == st.secrets["ADMIN_KEY"]:
                            st.session_state.team_unlocked = True
                            st.rerun()
                        else:
                            st.error("Invalid admin key.")

# MAIN DASHBOARD
def show_dashboard():
    # Sidebar
    with st.sidebar:
        st.image("assets/lumiere_logo_symbol.png", width=80)
        st.markdown(f"### Welcome, {st.session_state.mentor_name}")
        st.markdown(f'<p style="color:#FFFFFF; font-size:0.85rem; margin-top:-0.75rem;">{st.session_state.mentor_email}</p>', unsafe_allow_html=True)

        if st.session_state.is_preview:
            st.warning("👁️ Preview Mode")

        st.markdown("---")

        view = st.radio(
            "Select View",
            ["✅ Confirmed Students", "📋 Prospective Students", "📚 Resources"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.mentor_name = None
            st.session_state.mentor_email = None
            st.session_state.is_preview = False
            st.rerun()

    # Preview mode banner
    if st.session_state.is_preview:
        st.markdown(
            '<div class="preview-banner">👁️ <strong>Preview Mode:</strong> You are viewing this portal as ' +
            st.session_state.mentor_name + '</div>',
            unsafe_allow_html=True
        )

    if view == "📋 Prospective Students":
        prospective = get_prospective_students(st.session_state.mentor_email)
        show_assigned_students(prospective)
    elif view == "✅ Confirmed Students":
        students = get_students_for_mentor(st.session_state.mentor_email)
        show_confirmed_students(students)
    else:
        show_resources()

# RESOURCES PAGE
def show_resources():
    st.markdown('<p class="main-header">Resources</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Everything you need to run a great research program with your students.</p>', unsafe_allow_html=True)

    def resource_card(title, description, url, label="Open →"):
        return (
            f'<a href="{url}" target="_blank" style="text-decoration:none;">'
            f'<div style="background:#FFFFFF;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;'
            f'box-shadow:0 2px 8px rgba(0,0,0,0.06);border-left:4px solid #BE1E2D;'
            f'transition:box-shadow 0.2s;cursor:pointer;">'
            f'<div style="font-size:1rem;font-weight:700;color:#1A1A2E;margin-bottom:0.3rem;">{title}</div>'
            f'<div style="font-size:0.88rem;color:#64748B;margin-bottom:0.75rem;line-height:1.5;">{description}</div>'
            f'<div style="font-size:0.85rem;font-weight:600;color:#BE1E2D;">{label}</div>'
            f'</div></a>'
        )

    def link_item(title, url):
        return (
            f'<div style="padding:0.6rem 0;border-bottom:1px solid #F1F5F9;">'
            f'<a href="{url}" target="_blank" style="font-size:0.9rem;font-weight:600;color:#BE1E2D;text-decoration:none;">'
            f'{title} →</a></div>'
        )

    # Section 1: Key Actions
    st.markdown("#### Key Actions")
    col1, col2 = st.columns(2)
    with col1:
        is_foundation_volunteer = st.session_state.get("is_foundation_volunteer", False)
        guidebook_url = (
            "https://misty-music-eb4.notion.site/Volunteer-Mentor-Guidebook-26ea0d4fb23a8097b9e3fd34146ba1e3"
            if is_foundation_volunteer else
            "https://misty-music-eb4.notion.site/Lumiere-Mentor-Guidebook-2fd9c2704a104f86b97564620aca6874"
        )
        st.markdown(
            resource_card(
                "Mentor Guidebook",
                "Your go-to guide covering mentorship best practices, expectations, and program procedures.",
                guidebook_url
            ),
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            resource_card(
                "Meeting Update Form",
                "Fill this out after every meeting with your student to log progress and notes.",
                "https://airtable.com/appK9HemdsQBzVefU/shrKPtNpRyPI9eLuu"
            ),
            unsafe_allow_html=True
        )

    st.markdown(
        resource_card(
            "Mentor Submission Portal",
            "Submit your syllabus and final evaluation for your students here.",
            "https://airtable.com/appK9HemdsQBzVefU/shr9fSMhucWi2PSox"
        ),
        unsafe_allow_html=True
    )

    # Section 2: Syllabus Templates
    st.markdown("#### Syllabus Templates")
    st.markdown(
        '<div style="background:#FFFFFF;border-radius:12px;padding:1.25rem 1.5rem;'
        'box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:1rem;">'
        '<div style="font-size:0.85rem;color:#64748B;margin-bottom:0.75rem;">Base your syllabus on one of the templates below depending on your student\'s program.</div>'
        + link_item("Syllabus Outline — Individual & Premium Research Program", "https://docs.google.com/document/d/1g-vjJRawgWTKEpgDoKqPpOs6fUYA0_AG5ytJ0Dvywzo/edit?usp=sharing")
        + link_item("Syllabus Outline — Research Fellowship", "https://docs.google.com/spreadsheets/d/1KE9xVF78F6g0J1LcpyzPLt5vp1he7NRBFUEBc_AucaI/edit#gid=0")
        + link_item("Non-Branded Syllabus — Partner Programs (Individual & Premium)", "https://docs.google.com/document/d/1ZOsMZiBEGlKgvP8tfU1wVtKR3AVhE48K/edit?usp=sharing&ouid=115965191483790562336&rtpof=true&sd=true")
        + '</div>',
        unsafe_allow_html=True
    )

# VIEW A: ASSIGNED STUDENTS
def show_assigned_students(students):
    st.markdown('<p class="main-header">Prospective Students</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">These are your prospective students for the upcoming cohort, and where they are in the onboarding pipeline. As a reminder, once you\'ve confirmed that you\'d like to work with a student, the student needs to confirm — then we kick off!</p>', unsafe_allow_html=True)

    if not students:
        st.info("No students assigned to you yet.")
        return

    students = sorted(students, key=due_date_sort_key)

    # If a prospective student is selected, show their profile
    if st.session_state.selected_prospective_student:
        selected = next(
            (s for s in students if s["name"] == st.session_state.selected_prospective_student),
            None
        )
        if selected:
            if st.button("← Back to Student List"):
                st.session_state.selected_prospective_student = None
                st.rerun()

            st.markdown(f"## {selected['name']}")
            st.markdown("---")

            # Confirmation form banner
            st.markdown(
                '<a href="https://airtable.com/appK9HemdsQBzVefU/shrRxeL631pDNaAy5" target="_blank" style="text-decoration:none;">'
                '<div style="background:#ECFDF5;border:1px solid #6EE7B7;border-radius:10px;padding:1rem 1.25rem;'
                'margin-bottom:1.25rem;display:flex;align-items:center;justify-content:space-between;">'
                '<div>'
                '<div style="font-size:0.9rem;font-weight:700;color:#065F46;margin-bottom:0.2rem;">✅ Ready to work with this student?</div>'
                '<div style="font-size:0.85rem;color:#047857;">Fill out the confirmation form to let us know you\'d like to move forward.</div>'
                '</div>'
                '<div style="font-size:0.85rem;font-weight:700;color:#065F46;white-space:nowrap;margin-left:1rem;">Confirm Interest →</div>'
                '</div></a>',
                unsafe_allow_html=True
            )

            show_prospective_student_background(selected)
            return

        # Student not found in list (e.g. after data refresh), reset
        st.session_state.selected_prospective_student = None

    st.markdown(f"**Your Prospective Students** — {len(students)} student{'s' if len(students) != 1 else ''}")

    # Student filter
    student_names = ["All Students"] + [s["name"] for s in students]
    selected = st.selectbox("Filter by student", student_names, label_visibility="collapsed", key="assigned_filter")
    filtered = students if selected == "All Students" else [s for s in students if s["name"] == selected]

    for student in filtered:
        def status_badge(value):
            if value == "Yes":
                return f'<span style="background:#ECFDF5; color:#065F46; padding:0.2rem 0.65rem; border-radius:20px; font-size:0.8rem; font-weight:600;">✓ Yes</span>'
            elif value and value != "—":
                return f'<span style="background:#FFFBEB; color:#92400E; padding:0.2rem 0.65rem; border-radius:20px; font-size:0.8rem; font-weight:600;">{value}</span>'
            else:
                return f'<span style="background:#F1F5F9; color:#64748B; padding:0.2rem 0.65rem; border-radius:20px; font-size:0.8rem; font-weight:600;">—</span>'

        confirmation = student["mentor_confirmation"] or "—"
        shared = student["background_shared"] or "—"
        foundation = student.get("foundation_student", "") or "—"
        tuition = normalize_tuition_paid(student.get("tuition_paid", "") or "—")
        white_label = student.get("white_label", "") or "—"

        card_col, btn_col = st.columns([6, 1])
        with card_col:
            st.markdown(
                f"""
                <div style="background:#FFFFFF; border-radius:12px; padding:1.25rem 1.5rem;
                            margin-bottom:1.5rem; box-shadow:0 2px 8px rgba(0,0,0,0.06);
                            border-left:4px solid #BE1E2D;">
                    <div style="font-size:1rem; font-weight:700; color:#1A1A2E; margin-bottom:1rem;">
                        {student["name"]}
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem 2rem;">
                        <div>
                            <div style="font-size:0.72rem; font-weight:600; color:#94A3B8;
                                        text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.3rem;">
                                Have you indicated interest to work with this student?
                            </div>
                            {status_badge(confirmation)}
                        </div>
                        <div>
                            <div style="font-size:0.72rem; font-weight:600; color:#94A3B8;
                                        text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.3rem;">
                                Has your bio been shared with the student?
                            </div>
                            {status_badge(shared)}
                        </div>
                        <div>
                            <div style="font-size:0.72rem; font-weight:600; color:#94A3B8;
                                        text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.3rem;">
                                Is this a Foundation student?
                            </div>
                            {status_badge(foundation)}
                        </div>
                        <div>
                            <div style="font-size:0.72rem; font-weight:600; color:#94A3B8;
                                        text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.3rem;">
                                Has the student confirmed this match?
                            </div>
                            {status_badge(tuition)}
                        </div>
                        <div>
                            <div style="font-size:0.72rem; font-weight:600; color:#94A3B8;
                                        text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.3rem;">
                                Is this a white label student?
                            </div>
                            {status_badge(white_label)}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with btn_col:
            st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
            if st.button("View →", key=f"prospective_{student['id']}", use_container_width=True):
                st.session_state.selected_prospective_student = student["name"]
                st.rerun()

# VIEW B: CONFIRMED STUDENTS
def show_confirmed_students(students):
    st.markdown('<p class="main-header">Confirmed Students</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">These are the students you\'re actively working with or have worked with in the past. Click into any student to view their background, track deadlines and submissions, and review meeting notes.</p>', unsafe_allow_html=True)

    confirmed_students = students

    if not confirmed_students:
        st.info("No confirmed students yet. Students will appear here once they confirm the mentor match.")
        return

    # Sort: upcoming due dates soonest first, overdue/empty dates at the bottom
    confirmed_students.sort(key=due_date_sort_key)

    # If a student is selected, show their profile
    if "selected_student_name" in st.session_state and st.session_state.selected_student_name:
        selected = next(
            (s for s in confirmed_students if s["name"] == st.session_state.selected_student_name),
            None
        )
        if selected:
            if st.button("← Back to Student List"):
                st.session_state.selected_student_name = None
                st.rerun()

            st.markdown(f"## {selected['name']}")

            if selected.get("white_label"):
                partner = selected["white_label"]
                st.markdown(
                    f'<div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;padding:1rem 1.25rem;margin:0.75rem 0 1rem 0;">'
                    f'<div style="font-size:0.85rem;font-weight:700;color:#1E40AF;margin-bottom:0.3rem;">🤝 White Label Student — {partner}</div>'
                    f'<div style="font-size:0.85rem;color:#1E3A8A;line-height:1.6;">'
                    f'This student is enrolled through a partner program. While Lumiere runs the research program on the backend, the student receives all program resources, communications, and branding through <strong>{partner}</strong> — not directly from Lumiere. '
                    f'<strong>Please refrain from mentioning Lumiere in your communication with this student.</strong>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown("---")

            is_foundation_volunteer = st.session_state.get("is_foundation_volunteer", False)
            if is_foundation_volunteer:
                tab1, tab2, tab3, tab4 = st.tabs(["🎓 Student Background", "📋 Meeting Summary", "📅 Student Deadlines & Submissions", "📝 Your Submissions"])
                with tab1:
                    show_student_background(selected)
                with tab2:
                    show_mentor_meeting_summary(selected)
                with tab3:
                    show_student_deadlines_and_submissions(selected)
                with tab4:
                    show_mentor_submissions(selected)
            else:
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎓 Student Background", "📋 Meeting Summary", "📅 Student Deadlines & Submissions", "📝 Your Submissions", "💳 Payment Information"])
                with tab1:
                    show_student_background(selected)
                with tab2:
                    show_mentor_meeting_summary(selected)
                with tab3:
                    show_student_deadlines_and_submissions(selected)
                with tab4:
                    show_mentor_submissions(selected)
                with tab5:
                    show_payment_information(selected)
            return

    # Filter by student name
    student_names = ["All Students"] + [s["name"] for s in confirmed_students]
    selected_filter = st.selectbox("🔍 Search by student name", student_names, key="confirmed_search")
    if selected_filter != "All Students":
        confirmed_students = [s for s in confirmed_students if s["name"] == selected_filter]

    st.markdown(f"**{len(confirmed_students)}** student{'s' if len(confirmed_students) != 1 else ''}")

    # Student list
    for student in confirmed_students:
        pm_name = student.get("program_manager_name") or "—"
        pm_email = student.get("program_manager_email") or "—"
        due = format_date(student.get("revised_final_paper_due", ""))
        white_label = student.get("white_label", "") or "—"
        preferred_name = student.get("preferred_name", "") or "—"

        card_col, btn_col = st.columns([6, 1])
        with card_col:
            st.markdown(
                f"""
                <div style="background:#FFFFFF; border-radius:12px; padding:1.25rem 1.5rem;
                            margin-bottom:1.5rem; box-shadow:0 2px 8px rgba(0,0,0,0.06);
                            border-left:4px solid #BE1E2D;">
                    <div style="font-size:1rem; font-weight:700; color:#1A1A2E; margin-bottom:0.6rem;">
                        {student["name"]}
                    </div>
                    <div style="display:flex; gap:3rem; flex-wrap:wrap;">
                        <div>
                            <div style="font-size:0.72rem; font-weight:600; color:#94A3B8;
                                        text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.2rem;">
                                Preferred Name
                            </div>
                            <div style="font-size:0.88rem; color:#334155;">{preferred_name}</div>
                        </div>
                        <div>
                            <div style="font-size:0.72rem; font-weight:600; color:#94A3B8;
                                        text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.2rem;">
                                Program Manager
                            </div>
                            <div style="font-size:0.88rem; color:#334155;">{pm_name}</div>
                            <div style="font-size:0.82rem; color:#64748B;">{pm_email}</div>
                        </div>
                        <div>
                            <div style="font-size:0.72rem; font-weight:600; color:#94A3B8;
                                        text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.2rem;">
                                Revised Final Paper Due
                            </div>
                            <div style="font-size:0.88rem; color:#334155;">{due}</div>
                        </div>
                        <div>
                            <div style="font-size:0.72rem; font-weight:600; color:#94A3B8;
                                        text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.2rem;">
                                Is this a white label student?
                            </div>
                            <div style="font-size:0.88rem; color:#334155;">{white_label}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with btn_col:
            st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
            if st.button("View →", key=f"student_{student['id']}", use_container_width=True):
                st.session_state.selected_student_name = student["name"]
                st.rerun()

def show_mentor_meeting_summary(student):
    st.markdown("### Meeting Summary")

    st.markdown(
        '<a href="https://airtable.com/appK9HemdsQBzVefU/shrKPtNpRyPI9eLuu" target="_blank" style="text-decoration:none;">'
        '<div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;padding:1rem 1.25rem;'
        'margin-bottom:1.25rem;display:flex;align-items:center;justify-content:space-between;">'
        '<div>'
        '<div style="font-size:0.9rem;font-weight:700;color:#C2410C;margin-bottom:0.2rem;">📝 Just had a meeting?</div>'
        '<div style="font-size:0.85rem;color:#9A3412;">Fill out the Meeting Update Form to log your notes and progress.</div>'
        '</div>'
        '<div style="font-size:0.85rem;font-weight:700;color:#C2410C;white-space:nowrap;margin-left:1rem;">Open Form →</div>'
        '</div></a>',
        unsafe_allow_html=True
    )

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

    with col_m1:
        st.markdown("**📊 Meetings Completed**")
        completed = student.get("completed_meetings", 0) or 0
        expected = student.get("expected_meetings", 0) or 0
        if expected > 0:
            st.progress(min(completed / expected, 1.0))
            st.caption(f"{completed} of {expected} meetings completed")
        else:
            st.markdown("No meetings scheduled")

    with col_m2:
        st.markdown("**📋 Required Meetings for Program**")
        st.markdown(str(student.get("expected_meetings", 0) or 0))

    with col_m3:
        st.markdown("**⏱️ Hours Recorded**")
        st.markdown(format_duration(student.get("hours_recorded", "")))

    with col_m4:
        st.markdown("**🚫 Number of Student No Shows**")
        st.markdown(str(student.get("student_no_shows", 0) or 0))

    st.markdown("---")
    st.markdown("### Your Meeting Notes with the Student")

    meeting_notes = get_meeting_notes_for_student(student["name"])

    if not meeting_notes:
        st.info("No meeting notes found for this student.")
    else:
        for note in meeting_notes:
            date_str = format_date(note["date"]) if note["date"] else "No date"
            with st.expander(f"📅 {date_str}"):
                st.markdown(note["notes"] or "No notes recorded.")

def show_student_background(student):
    city = student["city"] or ""
    country = student.get("country") or ""
    location = ", ".join(filter(None, [city, country])) or "Not specified"
    pm_name = student.get("program_manager_name") or "Not specified"
    pm_email = student.get("program_manager_email") or "Not specified"

    def fb(label, value):
        v = value or "Not specified"
        return (f'<div style="margin-bottom:0.1rem;">'
                f'<div style="font-size:0.72rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem;">{label}</div>'
                f'<div style="font-size:0.95rem;color:#1A1A2E;font-weight:500;">{v}</div>'
                f'</div>')

    grad_year = str(student["graduation_year"]) if student["graduation_year"] else None

    # Section 1: Student Overview
    st.markdown("#### Student Overview")
    st.markdown(
        '<div style="background:#FFFFFF;border-radius:12px;padding:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:1.25rem;">'
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.25rem;">'
        + fb("Preferred Name", student.get("preferred_name"))
        + fb("Location", location)
        + fb("Graduation Year", grad_year)
        + fb("Current Grade in School", student.get("current_grade"))
        + fb("Research Area", student.get("research_area"))
        + fb("Status in Program", student.get("student_status"))
        + (fb("Publication Status", student.get("publication_status")) if student.get("publication_marker", "").strip().lower() == "yes" else "")
        + '</div></div>',
        unsafe_allow_html=True
    )

    # Section 2: Program Details
    wc_name = student.get("writing_coach_name") or ""
    wc_email = student.get("writing_coach_email") or ""
    ps_name = student.get("publication_specialist_name") or ""
    ps_email = student.get("publication_specialist_email") or ""

    def person_row(role, name, email, border=True):
        border_style = "border-bottom:1px solid #F1F5F9;padding-bottom:1rem;margin-bottom:1rem;" if border else ""
        return (
            f'<div style="{border_style}display:grid;grid-template-columns:1fr 1fr;gap:1rem;">'
            + fb(role, name)
            + fb(f"{role} Email", email)
            + '</div>'
        )

    details_html = (
        '<div style="background:#FFFFFF;border-radius:12px;padding:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:1.25rem;">'
        + person_row("Program Manager", pm_name, pm_email, border=bool(wc_name or ps_name))
    )
    if wc_name:
        details_html += person_row("Writing Coach", wc_name, wc_email, border=bool(ps_name))
    if ps_name:
        details_html += person_row("Publication Specialist", ps_name, ps_email, border=False)
    details_html += (
        '<div style="border-top:1px solid #F1F5F9;padding-top:1rem;margin-top:0.25rem;display:grid;grid-template-columns:1fr 1fr;gap:1rem;">'
        + fb("Revised Final Paper Due", format_date(student.get("revised_final_paper_due", "")))
        + fb("Is this student part of a white label program?", student.get("white_label") or "No")
        + '</div></div>'
    )
    st.markdown("#### Program Details")
    st.markdown(details_html, unsafe_allow_html=True)

    # Section 3: Coursework, Notes & Reason for Interest
    bg_items = [
        ("Reason for interest in research areas", student.get("reason_for_interest")),
        ("Student has completed coursework in", student.get("previous_coursework")),
        ("Notes from our team for this student", student.get("interview_notes")),
    ]
    bg_items = [(label, val) for label, val in bg_items if val and val.strip()]
    if bg_items:
        st.markdown("#### Background & Notes")
        inner = ""
        for i, (label, val) in enumerate(bg_items):
            border = "border-top:1px solid #F1F5F9;padding-top:1.25rem;" if i > 0 else ""
            bottom = "margin-bottom:1.25rem;" if i < len(bg_items) - 1 else ""
            inner += (
                f'<div style="{border}{bottom}">'
                f'<div style="font-size:0.72rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">{label}</div>'
                f'<div style="font-size:0.92rem;color:#1A1A2E;line-height:1.6;">{val}</div>'
                f'</div>'
            )
        st.markdown(
            '<div style="background:#FFFFFF;border-radius:12px;padding:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:1.25rem;">'
            + inner + '</div>',
            unsafe_allow_html=True
        )

def show_prospective_student_background(student):
    city = student["city"] or ""
    country = student.get("country") or ""
    location = ", ".join(filter(None, [city, country])) or "Not specified"

    def fb(label, value):
        v = value or "Not specified"
        return (f'<div style="margin-bottom:0.1rem;">'
                f'<div style="font-size:0.72rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem;">{label}</div>'
                f'<div style="font-size:0.95rem;color:#1A1A2E;font-weight:500;">{v}</div>'
                f'</div>')

    grad_year = str(student["graduation_year"]) if student["graduation_year"] else None

    # Student Overview (no Status in Program)
    st.markdown("#### Student Overview")
    st.markdown(
        '<div style="background:#FFFFFF;border-radius:12px;padding:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:1.25rem;">'
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.25rem;">'
        + fb("Preferred Name", student.get("preferred_name"))
        + fb("Location", location)
        + fb("Graduation Year", grad_year)
        + fb("Current Grade in School", student.get("current_grade"))
        + fb("Research Area", student.get("research_area"))
        + '</div></div>',
        unsafe_allow_html=True
    )

    # Background & Notes
    bg_items = [
        ("Reason for interest in research areas", student.get("reason_for_interest")),
        ("Student has completed coursework in", student.get("previous_coursework")),
        ("Notes from our team for this student", student.get("interview_notes")),
    ]
    bg_items = [(label, val) for label, val in bg_items if val and val.strip()]
    if bg_items:
        st.markdown("#### Background & Notes")
        inner = ""
        for i, (label, val) in enumerate(bg_items):
            border = "border-top:1px solid #F1F5F9;padding-top:1.25rem;" if i > 0 else ""
            bottom = "margin-bottom:1.25rem;" if i < len(bg_items) - 1 else ""
            inner += (
                f'<div style="{border}{bottom}">'
                f'<div style="font-size:0.72rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">{label}</div>'
                f'<div style="font-size:0.92rem;color:#1A1A2E;line-height:1.6;">{val}</div>'
                f'</div>'
            )
        st.markdown(
            '<div style="background:#FFFFFF;border-radius:12px;padding:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:1.25rem;">'
            + inner + '</div>',
            unsafe_allow_html=True
        )

def show_payment_information(student):
    st.markdown("### Payment Information")

    def fb(label, value):
        v = value or "Not specified"
        return (f'<div style="margin-bottom:0.1rem;">'
                f'<div style="font-size:0.72rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem;">{label}</div>'
                f'<div style="font-size:0.95rem;color:#1A1A2E;font-weight:500;">{v}</div>'
                f'</div>')

    def yes_no_badge(label, is_yes):
        if is_yes:
            badge = '<span style="background:#ECFDF5;color:#065F46;padding:0.2rem 0.65rem;border-radius:20px;font-size:0.8rem;font-weight:600;">✓ Yes</span>'
        else:
            badge = '<span style="background:#FEF2F2;color:#991B1B;padding:0.2rem 0.65rem;border-radius:20px;font-size:0.8rem;font-weight:600;">✗ No</span>'
        return (f'<div style="margin-bottom:0.1rem;">'
                f'<div style="font-size:0.72rem;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.25rem;">{label}</div>'
                f'{badge}'
                f'</div>')

    # Mentor Hourly Base Rate — safely handle list/string/number
    rate_raw = student.get("mentor_hourly_rate")
    if isinstance(rate_raw, list):
        rate_raw = rate_raw[0] if rate_raw else None
    try:
        rate_display = f"${float(rate_raw):g}/hr" if rate_raw is not None and rate_raw != "" else "Not specified"
    except (TypeError, ValueError):
        rate_display = str(rate_raw) if rate_raw else "Not specified"

    # Evaluation & Feedback Submitted? — Yes if link field is non-empty
    eval_link = student.get("evaluation_form_link") or ""
    eval_submitted = bool(eval_link.strip()) if isinstance(eval_link, str) else bool(eval_link)

    # Revised Final Paper Submitted? — Yes if attachment field has content
    upload_raw = student.get("revised_paper_upload")
    paper_submitted = bool(upload_raw) if not isinstance(upload_raw, list) else len(upload_raw) > 0

    # Publication marker & status
    pub_marker = student.get("publication_marker") or "No"
    pub_status = student.get("publication_status") or ""

    includes_publication = pub_marker.strip().lower() == "yes"

    st.markdown(
        '<div style="background:#FFFFFF;border-radius:12px;padding:1.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:1.25rem;">'
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1.25rem;">'
        + fb("Hourly Base Rate", rate_display)
        + yes_no_badge("Have you submitted the evaluation & feedback for this student?", eval_submitted)
        + yes_no_badge("Has the student submitted the revised final paper?", paper_submitted)
        + fb("Total Number of Meetings Completed (Accounted for 1 No Show)", str(student.get("completed_meetings") or 0))
        + fb("Payment Status", student.get("mentor_payment_status") or "Not specified")
        + (fb("1st Payment Date", format_date(student.get("payment_date_1", ""))) if student.get("payment_date_1") else "")
        + (fb("2nd Payment Date", format_date(student.get("payment_date_2", ""))) if student.get("payment_date_2") else "")
        + (fb("3rd Payment Date", format_date(student.get("payment_date_3", ""))) if student.get("payment_date_3") else "")
        + (fb("What's the student's publication status?", pub_status) if includes_publication else "")
        + '</div></div>',
        unsafe_allow_html=True
    )

def show_student_deadlines_and_submissions(student):
    st.markdown("### Student Deadlines & Submissions")

    all_deadlines = get_deadlines_for_student(student["name"])
    # Filter out Syllabus — those are shown in Mentor Submissions
    deadlines = [d for d in all_deadlines if d["type"] != "Syllabus"]

    if not deadlines:
        st.info("No deadlines found for this student.")
        return

    # Show overdue and next upcoming deadline banners
    try:
        now = datetime.now()
        pending = [d for d in deadlines if d["status"] != "Submitted" and d["due_date"]]
        overdue = [d for d in pending if datetime.strptime(d["due_date"], "%Y-%m-%d") < now]
        future = [d for d in pending if datetime.strptime(d["due_date"], "%Y-%m-%d") >= now]

        if overdue:
            overdue_list = ", ".join(f"{d['type']} ({format_date(d['due_date'])})" for d in overdue)
            st.markdown(
                f'<div style="background: rgba(239,68,68,0.1); border: 1px solid #EF4444; '
                f'border-radius: 10px; padding: 1rem; margin-bottom: 0.75rem;">'
                f'<strong>⚠️ Overdue:</strong> {overdue_list}'
                f'</div>',
                unsafe_allow_html=True,
            )

        if future:
            next_deadline = future[0]
            days_left = (datetime.strptime(next_deadline["due_date"], "%Y-%m-%d") - now).days
            st.markdown(
                f'<div style="background: rgba(220,30,53,0.1); border: 1px solid #DC1E35; '
                f'border-radius: 10px; padding: 1rem; margin-bottom: 1rem;">'
                f'<strong>⏰ Next Deadline:</strong> {next_deadline["type"]} — '
                f'due {format_date(next_deadline["due_date"])} ({days_left} day{"s" if days_left != 1 else ""} away)'
                f'</div>',
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    for deadline in deadlines:
        status = deadline["status"]
        due_date = deadline["due_date"]
        overdue = is_overdue(due_date, status)

        # Determine icon
        if status == "Submitted":
            icon = "✅"
        elif overdue:
            icon = "⚠️"
        else:
            icon = "📅"

        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(f"{icon} **{deadline['type']}**")

            with col2:
                st.markdown(f"**Due:** {format_date(due_date)}")

            with col3:
                if status == "Submitted":
                    st.success(f"Submitted {format_datetime_ist(deadline['date_submitted'])}")
                elif overdue:
                    st.error("Overdue")
                else:
                    st.warning("Not Submitted")

            # Show attachments inline if any
            if deadline.get("submissions"):
                for field_name, value in deadline["submissions"].items():
                    if isinstance(value, list):
                        for attachment in value:
                            if isinstance(attachment, dict):
                                url = attachment.get("url", "")
                                filename = attachment.get("filename", "Download")
                                if url:
                                    st.markdown(f"  📎 [{filename}]({url})")
                            else:
                                st.markdown(f"  📎 {attachment}")
                    elif isinstance(value, str) and value.startswith("http"):
                        st.markdown(f"  📎 [View Submission]({value})")
                    else:
                        st.markdown(f"  📄 {value}")

            st.markdown("---")

def show_mentor_submissions(student):
    st.markdown("### Mentor Submissions")

    all_deadlines = get_deadlines_for_student(student["name"])
    syllabus_deadlines = [d for d in all_deadlines if d["type"] == "Syllabus"]
    eval_deadlines = [d for d in all_deadlines if d["type"] == "Evaluation & Feedback"]

    def render_mentor_deadline(deadline, label):
        status = deadline["status"]
        due_date = deadline["due_date"]
        overdue = is_overdue(due_date, status)

        if status == "Submitted":
            icon = "✅"
        elif overdue:
            icon = "⚠️"
        else:
            icon = "📅"

        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"{icon} **{label}**")
            with col2:
                st.markdown(f"**Due:** {format_date(due_date)}")
            with col3:
                if status == "Submitted":
                    st.success(f"Submitted {format_datetime_ist(deadline['date_submitted'])}")
                elif overdue:
                    st.error("Overdue")
                else:
                    st.warning("Not Submitted")

            if deadline.get("submissions"):
                for field_name, value in deadline["submissions"].items():
                    if isinstance(value, list):
                        for attachment in value:
                            if isinstance(attachment, dict):
                                url = attachment.get("url", "")
                                filename = attachment.get("filename", "Download")
                                if url:
                                    st.markdown(f"  📎 [{filename}]({url})")
                            else:
                                st.markdown(f"  📎 {attachment}")
                    elif isinstance(value, str) and value.startswith("http"):
                        st.markdown(f"  📎 [View Submission]({value})")
                    else:
                        st.markdown(f"  📄 {value}")

    # Syllabus
    if not syllabus_deadlines:
        st.info("No syllabus deadline found for this student.")
    else:
        for deadline in syllabus_deadlines:
            render_mentor_deadline(deadline, "Syllabus")

    st.markdown("---")

    # Evaluation & Feedback
    if not eval_deadlines:
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown("📅 **Evaluation & Feedback**")
            with col2:
                st.markdown("**Due:** Not set")
            with col3:
                st.warning("Not Submitted")
    else:
        for deadline in eval_deadlines:
            render_mentor_deadline(deadline, "Evaluation & Feedback")

# Main app logic
def main():
    # Check for magic link token first
    check_magic_link_token()

    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
