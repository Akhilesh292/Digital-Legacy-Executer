"""
DIGITAL LEGACY EXECUTOR — COMPLETE SINGLE-FILE APPLICATION
============================================================

HOW TO RUN LOCALLY:
1. Install dependencies:
   pip install flask flask-login flask-sqlalchemy cryptography gunicorn

2. Run the app:
   python app.py

3. Open your browser to:
   http://localhost:5000

FOR RENDER DEPLOYMENT:
- Build Command: pip install -r requirements.txt
- Start Command: gunicorn app:app
- Add environment variable: SECRET_KEY = any_random_string
"""

import os
import secrets
import json
from datetime import datetime, timedelta

from flask import Flask, render_template_string, request, redirect, url_for, flash, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

# ============================================================
# APP SETUP
# ============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///legacy.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Encryption key — auto-generated on first run
KEY_FILE = "secret.key"
if os.environ.get("FERNET_KEY"):
    FERNET_KEY = os.environ["FERNET_KEY"].encode()
elif os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f:
        FERNET_KEY = f.read()
else:
    FERNET_KEY = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(FERNET_KEY)

fernet = Fernet(FERNET_KEY)

# ============================================================
# DATABASE MODELS
# ============================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LegacyPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    encrypted_data = db.Column(db.Text, nullable=False)
    contact_email = db.Column(db.String(150), nullable=False)
    inactivity_days = db.Column(db.Integer, default=180)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="active")
    confirmation_token = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='plans')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================================================
# ENCRYPTION HELPERS
# ============================================================

def encrypt_plan(data: dict) -> str:
    return fernet.encrypt(json.dumps(data).encode()).decode()

def decrypt_plan(encrypted: str) -> dict:
    return json.loads(fernet.decrypt(encrypted.encode()).decode())

# ============================================================
# BASE HTML TEMPLATE
# ============================================================

# NOTE: The {% block content %} has been REMOVED from the base template
# to fix the "block 'content' defined twice" error.
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Digital Legacy Executor</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f0f2f5; color: #1a1a1a; }
    nav { background: #1a252f; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; display: flex; align-items: center; flex-wrap: wrap; }
    nav .brand { color: #4ade80; font-weight: bold; font-size: 1.2em; margin-right: 30px; }
    nav a { color: #cbd5e1; margin-right: 18px; text-decoration: none; font-size: 0.95em; }
    nav a:hover { color: white; }
    .card { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }
    h1 { color: #1a252f; margin-top: 0; }
    h2 { color: #334155; font-size: 1.2em; }
    label { display: block; margin: 12px 0 4px; font-weight: 600; font-size: 0.9em; color: #475569; }
    input, select { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 1em; }
    input:focus, select:focus { outline: none; border-color: #4ade80; box-shadow: 0 0 0 3px rgba(74,222,128,0.1); }
    button, .btn { display: inline-block; padding: 11px 22px; background: #1a252f; color: white; border: none; border-radius: 6px; font-size: 0.95em; cursor: pointer; text-decoration: none; margin-top: 12px; }
    button:hover, .btn:hover { background: #0f1720; }
    .btn-green { background: #16a34a; }
    .btn-green:hover { background: #15803d; }
    .flash { padding: 12px 16px; border-radius: 6px; margin-bottom: 15px; font-size: 0.9em; }
    .flash.success { background: #dcfce7; color: #166534; border-left: 4px solid #16a34a; }
    .flash.error { background: #fee2e2; color: #991b1b; border-left: 4px solid #dc2626; }
    .flash.info { background: #dbeafe; color: #1e40af; border-left: 4px solid #3b82f6; }
    .plan-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #e2e8f0; flex-wrap: wrap; gap: 10px; }
    .plan-row:last-child { border-bottom: none; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 600; }
    .badge-active { background: #dcfce7; color: #166534; }
    .badge-pending_verification { background: #fef3c7; color: #92400e; }
    .badge-executed { background: #dbeafe; color: #1e40af; }
    .badge-confirmed { background: #e0e7ff; color: #3730a3; }
    pre { background: #1a252f; color: #e2e8f0; padding: 18px; border-radius: 6px; overflow-x: auto; font-size: 0.85em; line-height: 1.5; }
    .account-block { background: #f8fafc; padding: 12px; border-radius: 6px; margin-bottom: 8px; border: 1px solid #e2e8f0; }
    .muted { color: #64748b; font-size: 0.85em; }
  </style>
</head>
<body>
  <nav>
    <span class="brand">Digital Legacy</span>
    <a href="/">Home</a>
    {% if current_user.is_authenticated %}
      <a href="/dashboard">Dashboard</a>
      <a href="/create_plan">Create Plan</a>
      <a href="/logout">Logout</a>
    {% else %}
      <a href="/signup">Sign Up</a>
      <a href="/login">Login</a>
    {% endif %}
  </nav>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, message in messages %}
      <div class="flash {{ category }}">{{ message }}</div>
    {% endfor %}
  {% endwith %}
"""

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1>Digital Legacy Executor</h1>
      <p>Protect your digital life after you're gone. Set up a plan while you're alive, and we'll handle the rest — with your trusted contact's confirmation.</p>
      <p class="muted">This is a working demonstration application. Plans are stored encrypted.</p>
      {% if not current_user.is_authenticated %}
        <a href="/signup" class="btn btn-green">Create an Account</a>
        <a href="/login" class="btn">Log In</a>
      {% else %}
        <a href="/create_plan" class="btn btn-green">Create a Plan</a>
        <a href="/dashboard" class="btn">Go to Dashboard</a>
      {% endif %}
    </div>
    """)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        name = request.form['name'].strip()
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('signup'))

        user = User(email=email, name=name, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1>Create Account</h1>
      <form method="POST">
        <label>Full Name</label>
        <input name="name" required placeholder="e.g., Priya Sharma">
        <label>Email</label>
        <input name="email" type="email" required placeholder="you@example.com">
        <label>Password (min 6 characters)</label>
        <input name="password" type="password" required minlength="6">
        <button type="submit">Sign Up</button>
      </form>
      <p class="muted" style="margin-top:15px;">Already have an account? <a href="/login">Log in</a></p>
    </div>
    """)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f'Welcome back, {user.name}.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'error')

    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1>Log In</h1>
      <form method="POST">
        <label>Email</label>
        <input name="email" type="email" required>
        <label>Password</label>
        <input name="password" type="password" required>
        <button type="submit">Log In</button>
      </form>
      <p class="muted" style="margin-top:15px;">New here? <a href="/signup">Create an account</a></p>
    </div>
    """)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    plans = LegacyPlan.query.filter_by(user_id=current_user.id).all()
    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1>Your Dashboard</h1>
      <p>Hello, {{ current_user.name }}. Here are your legacy plans.</p>
      {% if plans %}
        {% for plan in plans %}
          <div class="plan-row">
            <div>
              <strong>Plan #{{ plan.id }}</strong><br>
              <span class="muted">Contact: {{ plan.contact_email }} | Threshold: {{ plan.inactivity_days }} days | Last activity: {{ plan.last_activity.strftime('%Y-%m-%d') }}</span>
            </div>
            <span class="badge badge-{{ plan.status }}">{{ plan.status }}</span>
          </div>
        {% endfor %}
      {% else %}
        <p class="muted">You haven't created any plans yet.</p>
      {% endif %}
      <a href="/create_plan" class="btn btn-green">Create a New Plan</a>
      {% if plans %}
        <a href="/run_check" class="btn">Run Inactivity Check (Demo)</a>
      {% endif %}
    </div>
    """, plans=plans)

@app.route('/create_plan', methods=['GET', 'POST'])
@login_required
def create_plan():
    if request.method == 'POST':
        contact_email = request.form['contact_email'].strip().lower()
        inactivity_days = int(request.form['inactivity_days'])

        platforms = request.form.getlist('platform[]')
        actions = request.form.getlist('action[]')
        filters = request.form.getlist('filter[]')

        accounts = []
        for p, a, f in zip(platforms, actions, filters):
            if p and a:
                entry = {"platform": p, "action": a}
                if f.strip():
                    entry["filter"] = f.strip()
                accounts.append(entry)

        plan_data = {
            "userName": current_user.name,
            "accounts": accounts,
            "createdAt": datetime.utcnow().isoformat()
        }

        plan = LegacyPlan(
            user_id=current_user.id,
            encrypted_data=encrypt_plan(plan_data),
            contact_email=contact_email,
            inactivity_days=inactivity_days,
            last_activity=datetime.utcnow(),
            status="active"
        )
        db.session.add(plan)
        db.session.commit()
        flash('Plan created and encrypted successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1>Create a Legacy Plan</h1>
      <p class="muted">All data is encrypted before storage.</p>
      <form method="POST">
        <label>Emergency Contact Email</label>
        <input name="contact_email" type="email" required placeholder="trusted@example.com">

        <label>Inactivity Threshold (days)</label>
        <input name="inactivity_days" type="number" value="180" required min="30" max="3650">

        <h2 style="margin-top:25px;">Accounts to Handle</h2>
        <div id="accounts">
          <div class="account-block">
            <label>Platform</label>
            <select name="platform[]">
              <option>Facebook</option>
              <option>Google Photos</option>
              <option>Email</option>
              <option>Instagram</option>
            </select>
            <label>Action</label>
            <select name="action[]">
              <option>Delete</option>
              <option>Transfer to contact</option>
              <option>Archive privately</option>
            </select>
            <label>Filter (optional)</label>
            <input name="filter[]" placeholder="e.g., album: Family">
          </div>
        </div>
        <button type="button" onclick="addRow()">+ Add Another Account</button>
        <br>
        <button type="submit" class="btn-green">Save Encrypted Plan</button>
      </form>
    </div>
    <script>
    function addRow() {
      const div = document.getElementById('accounts');
      const row = document.createElement('div');
      row.className = 'account-block';
      row.innerHTML = `
        <label>Platform</label>
        <select name="platform[]">
          <option>Facebook</option>
          <option>Google Photos</option>
          <option>Email</option>
          <option>Instagram</option>
        </select>
        <label>Action</label>
        <select name="action[]">
          <option>Delete</option>
          <option>Transfer to contact</option>
          <option>Archive privately</option>
        </select>
        <label>Filter (optional)</label>
        <input name="filter[]" placeholder="e.g., album: Family">
      `;
      div.appendChild(row);
    }
    </script>
    """)

@app.route('/run_check')
@login_required
def run_check():
    plans = LegacyPlan.query.filter_by(user_id=current_user.id, status="active").all()
    results = []

    for plan in plans:
        days_inactive = (datetime.utcnow() - plan.last_activity).days
        if days_inactive >= plan.inactivity_days:
            token = secrets.token_urlsafe(32)
            plan.confirmation_token = token
            plan.status = "pending_verification"
            db.session.commit()
            results.append({
                "plan_id": plan.id,
                "action": "Verification email sent",
                "contact": plan.contact_email,
                "token": token
            })
        else:
            results.append({
                "plan_id": plan.id,
                "action": "Still active",
                "days_left": plan.inactivity_days - days_inactive
            })

    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1>Inactivity Check Results</h1>
      {% if results %}
        {% for r in results %}
          <div class="plan-row">
            <div>
              <strong>Plan #{{ r.plan_id }}</strong><br>
              <span class="muted">{{ r.action }}</span>
              {% if r.get('contact') %}
                <br><span class="muted">Sent to: {{ r.contact }}</span>
                <br><span class="muted">Confirmation link: <a href="/confirm/{{ r.token }}">/confirm/{{ r.token[:16] }}...</a></span>
              {% endif %}
              {% if r.get('days_left') %}
                <br><span class="muted">Days until threshold: {{ r.days_left }}</span>
              {% endif %}
            </div>
          </div>
        {% endfor %}
      {% else %}
        <p class="muted">No active plans to check.</p>
      {% endif %}
      <a href="/dashboard" class="btn">Back to Dashboard</a>
    </div>
    """, results=results)

@app.route('/confirm/<token>')
def confirm(token):
    plan = LegacyPlan.query.filter_by(confirmation_token=token).first()
    if not plan:
        flash('Invalid or expired confirmation link.', 'error')
        return redirect(url_for('index'))

    if plan.status in ("confirmed", "executed"):
        return render_template_string(BASE_TEMPLATE + """
        <div class="card">
          <h1>Already Confirmed</h1>
          <p>This plan has already been confirmed and executed.</p>
        </div>
        """)

    plan.status = "confirmed"
    db.session.commit()

    plan_data = decrypt_plan(plan.encrypted_data)
    actions = []
    for acc in plan_data.get("accounts", []):
        platform = acc["platform"]
        action = acc["action"]
        filter_val = acc.get("filter", "")

        if platform == "Facebook" and action == "Delete":
            detail = "Submit account deletion request via Facebook Memorialization Settings."
            status = "REQUEST_GENERATED"
        elif platform == "Google Photos" and action == "Transfer to contact":
            detail = f"Export {filter_val or 'all photos'} via Google Takeout. Share with {plan.contact_email}."
            status = "EXPORT_READY"
        elif platform == "Google Photos" and action == "Archive privately":
            detail = f"Export {filter_val or 'all photos'} to encrypted archive. Do not share."
            status = "ARCHIVE_READY"
        elif platform == "Email" and action == "Delete":
            detail = "Submit account closure request with death certificate."
            status = "REQUEST_GENERATED"
        else:
            detail = f"Manual action: {action} for {platform}."
            status = "PENDING_MANUAL"

        actions.append({"platform": platform, "filter": filter_val, "action": action, "detail": detail, "status": status})

    plan.status = "executed"
    db.session.commit()

    report_text = f"""
DIGITAL LEGACY EXECUTION REPORT
User: {plan_data.get('userName')}
Contact: {plan.contact_email}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}
Status: EXECUTION COMPLETE

ACTIONS:
"""
    for i, a in enumerate(actions, 1):
        report_text += f"\n{i}. {a['platform']} ({a['filter'] or 'no filter'})\n   Action: {a['action']}\n   Detail: {a['detail']}\n   Status: {a['status']}\n"

    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1>Confirmation Successful</h1>
      <p>The plan has been executed. Here is the report:</p>
      <pre>{{ report }}</pre>
    </div>
    """, report=report_text)

# ============================================================
# INITIALIZE AND RUN
# ============================================================

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)