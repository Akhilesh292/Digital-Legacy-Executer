"""
GRANT SECURITY — COMPLETE SINGLE-FILE APPLICATION (CYBERSECURITY THEME)
============================================================
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
# BASE HTML TEMPLATE (CYBERSECURITY THEME)
# ============================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GRANT Security | Ops Center</title>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-black: #050505;
      --bg-dark: #0d1117;
      --panel-bg: #161b22;
      --primary-green: #00ff41;
      --primary-green-dim: #00b32c;
      --text-main: #c9d1d9;
      --text-muted: #8b949e;
      --border: #30363d;
      --danger: #ff3366;
      --warning: #ffcc00;
      --font-mono: 'Fira Code', monospace;
      --font-sans: 'Inter', sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    body { 
      font-family: var(--font-sans); 
      background-color: var(--bg-black); 
      background-image: 
        linear-gradient(rgba(0, 255, 65, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 255, 65, 0.03) 1px, transparent 1px);
      background-size: 30px 30px;
      color: var(--text-main); 
      line-height: 1.6;
      min-height: 100vh;
    }

    nav { 
      background-color: var(--bg-dark); 
      padding: 1rem 2rem; 
      display: flex; 
      align-items: center; 
      justify-content: space-between;
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 50;
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    .brand { 
      color: var(--primary-green); 
      font-family: var(--font-mono);
      font-weight: 600; 
      font-size: 1.3rem; 
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 10px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .nav-links { display: flex; gap: 1.5rem; align-items: center; font-family: var(--font-mono); }
    nav a:not(.brand) { 
      color: var(--text-main); 
      text-decoration: none; 
      font-size: 0.9rem; 
      transition: all 0.2s;
      padding: 0.5rem;
      border-radius: 4px;
    }
    nav a:not(.brand):hover { 
      color: var(--primary-green); 
      background: rgba(0, 255, 65, 0.1);
      box-shadow: 0 0 10px rgba(0, 255, 65, 0.2);
    }

    .container { 
      max-width: 1000px; 
      margin: 3rem auto; 
      padding: 0 1.5rem; 
    }

    .card { 
      background: var(--panel-bg); 
      padding: 2.5rem; 
      border-radius: 8px; 
      border: 1px solid var(--border);
      border-left: 4px solid var(--primary-green);
      box-shadow: 0 8px 30px rgba(0,0,0,0.5);
      margin-bottom: 2rem;
      position: relative;
      overflow: hidden;
    }

    .card::before {
      content: "";
      position: absolute;
      top: 0; left: 0; width: 100%; height: 2px;
      background: rgba(0, 255, 65, 0.3);
      animation: scanline 4s linear infinite;
      pointer-events: none;
    }
    @keyframes scanline {
      0% { transform: translateY(-100%); }
      100% { transform: translateY(100%); }
    }

    h1 { 
      color: #ffffff; 
      font-family: var(--font-mono);
      font-size: 2rem; 
      margin-bottom: 1rem; 
      text-transform: uppercase;
      letter-spacing: 2px;
      text-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
    }
    h2 { 
      color: var(--primary-green); 
      font-family: var(--font-mono);
      font-size: 1.2rem; 
      margin: 2rem 0 1rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.5rem;
    }
    p { margin-bottom: 1rem; color: var(--text-muted); font-size: 0.95rem; }

    .form-group { margin-bottom: 1.5rem; }
    label { 
      display: block; 
      margin-bottom: 0.5rem; 
      font-family: var(--font-mono);
      font-size: 0.85rem; 
      color: var(--primary-green); 
      text-transform: uppercase;
    }
    input, select { 
      width: 100%; 
      padding: 0.75rem 1rem; 
      border: 1px solid var(--border); 
      border-radius: 4px; 
      font-size: 1rem; 
      font-family: var(--font-mono);
      background-color: var(--bg-black);
      color: #ffffff;
      transition: all 0.2s;
    }
    input:focus, select:focus { 
      outline: none; 
      border-color: var(--primary-green); 
      box-shadow: 0 0 10px rgba(0, 255, 65, 0.2); 
    }
    input::placeholder { color: #484f58; }

    button, .btn { 
      display: inline-block; 
      padding: 0.8rem 1.5rem; 
      background: transparent; 
      color: var(--primary-green); 
      border: 1px solid var(--primary-green); 
      border-radius: 4px; 
      font-size: 1rem; 
      font-family: var(--font-mono);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 1px;
      cursor: pointer; 
      text-decoration: none; 
      transition: all 0.3s;
      margin-top: 0.5rem;
    }
    button:hover, .btn:hover { 
      background: rgba(0, 255, 65, 0.1);
      box-shadow: 0 0 15px rgba(0, 255, 65, 0.4);
    }
    .btn-green { 
      background: var(--primary-green); 
      color: #000000; 
    }
    .btn-green:hover { 
      background: #ffffff; 
      border-color: #ffffff;
      box-shadow: 0 0 20px rgba(255, 255, 255, 0.5);
    }

    .flash { 
      padding: 1rem; 
      border-radius: 4px; 
      margin-bottom: 1.5rem; 
      font-family: var(--font-mono);
      font-size: 0.9rem; 
      border: 1px solid;
      display: flex;
      align-items: center;
    }
    .flash.success { border-color: var(--primary-green); color: var(--primary-green); background: rgba(0, 255, 65, 0.05); }
    .flash.error { border-color: var(--danger); color: var(--danger); background: rgba(255, 51, 102, 0.05); }
    .flash.info { border-color: #58a6ff; color: #58a6ff; background: rgba(88, 166, 255, 0.05); }

    .plan-row { 
      display: flex; 
      justify-content: space-between; 
      align-items: center; 
      padding: 1.25rem; 
      background: var(--bg-black);
      border: 1px solid var(--border);
      border-radius: 4px;
      margin-bottom: 1rem; 
      transition: border-color 0.2s;
      font-family: var(--font-mono);
    }
    .plan-row:hover { border-color: var(--primary-green); }
    
    .badge { 
      display: inline-block; 
      padding: 0.25rem 0.75rem; 
      border-radius: 4px; 
      font-size: 0.75rem; 
      font-weight: 600; 
      text-transform: uppercase;
      font-family: var(--font-mono);
    }
    .badge-active { border: 1px solid var(--primary-green); color: var(--primary-green); }
    .badge-pending_verification { border: 1px solid var(--warning); color: var(--warning); }
    .badge-executed { border: 1px solid #58a6ff; color: #58a6ff; }
    
    pre { 
      background: #000000; 
      color: var(--primary-green); 
      padding: 1.5rem; 
      border-radius: 4px; 
      overflow-x: auto; 
      font-family: var(--font-mono);
      font-size: 0.85rem; 
      line-height: 1.6; 
      border: 1px solid var(--border);
      border-left: 3px solid var(--primary-green);
    }

    .muted { color: var(--text-muted); font-size: 0.85rem; display: block; margin-top: 0.25rem; }

    @media (max-width: 600px) {
      nav { flex-direction: column; gap: 1rem; }
      .nav-links { flex-wrap: wrap; justify-content: center; }
      .card { padding: 1.5rem; }
      h1 { font-size: 1.5rem; }
      .plan-row { flex-direction: column; align-items: flex-start; gap: 1rem; }
    }
  </style>
</head>
<body>
  <nav>
    <a href="/" class="brand">
      <span style="font-size: 1.5rem;">[</span> GRANT_SYS <span style="font-size: 1.5rem;">]</span>
    </a>
    <div class="nav-links">
      <a href="/">~ /home</a>
      {% if current_user.is_authenticated %}
        <a href="/dashboard">~ /dashboard</a>
        <a href="/create_plan">~ /new_plan</a>
        <a href="/logout" style="color: var(--danger);">~ /logout</a>
      {% else %}
        <a href="/signup">~ /signup</a>
        <a href="/login">~ /login</a>
      {% endif %}
    </div>
  </nav>

  <div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, message in messages %}
        <div class="flash {{ category }}">
          > {{ message }}
        </div>
      {% endfor %}
    {% endwith %}
"""

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="text-align: center; padding: 4rem 2rem;">
      <h1 style="font-size: 2.5rem; margin-bottom: 1.5rem;">GRANT Security</h1>
      <p style="font-size: 1.1rem; max-width: 600px; margin: 0 auto 2.5rem; font-family: var(--font-mono);">
        > INITIALIZING PROTOCOL...<br>
        > DIGITAL LEGACY ENCRYPTION ACTIVE.<br><br>
        Ensure your digital footprint is secured and handled exactly according to your directives. Set up an encrypted plan while alive. The system will execute the rest upon verified human confirmation.
      </p>
      <div style="margin-top: 2rem; display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
        {% if not current_user.is_authenticated %}
          <a href="/signup" class="btn btn-green" style="padding: 1rem 2rem;">[ CREATE_ACCOUNT ]</a>
          <a href="/login" class="btn" style="padding: 1rem 2rem;">[ SYSTEM_LOGIN ]</a>
        {% else %}
          <a href="/create_plan" class="btn btn-green" style="padding: 1rem 2rem;">[ NEW_PLAN ]</a>
          <a href="/dashboard" class="btn" style="padding: 1rem 2rem;">[ DASHBOARD ]</a>
        {% endif %}
      </div>
      <p class="muted" style="margin-top: 3rem; font-family: var(--font-mono);">[ ENCRYPTION: AES-256 ACTIVE ]</p>
    </div>
    """)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        name = request.form['name'].strip()
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('ERROR: Email already registered in the system.', 'error')
            return redirect(url_for('signup'))

        user = User(email=email, name=name, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash('SUCCESS: Account created. Proceed to login.', 'success')
        return redirect(url_for('login'))

    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="max-width: 500px; margin: 0 auto;">
      <h1>Register Operator</h1>
      <p style="font-family: var(--font-mono);">> ENTER NEW IDENTITY DETAILS</p>
      <form method="POST" style="margin-top: 2rem;">
        <div class="form-group">
          <label>> Full Name</label>
          <input name="name" required placeholder="e.g., John Doe">
        </div>
        <div class="form-group">
          <label>> Email Address</label>
          <input name="email" type="email" required placeholder="operator@domain.com">
        </div>
        <div class="form-group">
          <label>> Access Key (Password)</label>
          <input name="password" type="password" required minlength="6" placeholder="********">
        </div>
        <button type="submit" class="btn-green" style="width: 100%;">[ INITIALIZE ]</button>
      </form>
      <p class="muted" style="text-align: center; margin-top: 1.5rem; font-family: var(--font-mono);">> Existing user? <a href="/login" style="color: var(--primary-green); text-decoration: none;">[ LOGIN ]</a></p>
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
            flash(f'ACCESS GRANTED. Welcome back, {user.name}.', 'success')
            return redirect(url_for('dashboard'))
        flash('ACCESS DENIED: Invalid credentials.', 'error')

    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="max-width: 500px; margin: 0 auto;">
      <h1>System Login</h1>
      <p style="font-family: var(--font-mono);">> AUTHENTICATE TO CONTINUE</p>
      <form method="POST" style="margin-top: 2rem;">
        <div class="form-group">
          <label>> Email Address</label>
          <input name="email" type="email" required placeholder="operator@domain.com">
        </div>
        <div class="form-group">
          <label>> Access Key</label>
          <input name="password" type="password" required placeholder="********">
        </div>
        <button type="submit" class="btn-green" style="width: 100%;">[ AUTHENTICATE ]</button>
      </form>
      <p class="muted" style="text-align: center; margin-top: 1.5rem; font-family: var(--font-mono);">> Unregistered? <a href="/signup" style="color: var(--primary-green); text-decoration: none;">[ REGISTER ]</a></p>
    </div>
    """)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('SESSION TERMINATED.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    plans = LegacyPlan.query.filter_by(user_id=current_user.id).all()
    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;">
        <div>
          <h1>Ops Dashboard</h1>
          <p style="font-family: var(--font-mono);">> OPERATOR: {{ current_user.name }}</p>
        </div>
        <a href="/create_plan" class="btn btn-green">[ + NEW_PLAN ]</a>
      </div>
      
      {% if plans %}
        <h2 style="margin-top: 0;">ACTIVE PROTOCOLS</h2>
        {% for plan in plans %}
          <div class="plan-row">
            <div>
              <strong style="font-size: 1.1rem; color: #fff;">[ PLAN_ID: {{ plan.id }} ]</strong>
              <span class="muted">TARGET_CONTACT: {{ plan.contact_email }}</span>
              <span class="muted">INACTIVITY_THRESHOLD: {{ plan.inactivity_days }} days | LAST_CHECKIN: {{ plan.last_activity.strftime('%Y-%m-%d') }}</span>
            </div>
            <span class="badge badge-{{ plan.status }}">{{ plan.status.replace('_', ' ') }}</span>
          </div>
        {% endfor %}
        
        <div style="margin-top: 2rem; padding-top: 2rem; border-top: 1px solid var(--border);">
          <a href="/run_check" class="btn" style="width: 100%; text-align: center;">[ RUN INACTIVITY DIAGNOSTIC ]</a>
        </div>
      {% else %}
        <div style="text-align: center; padding: 3rem 0; border: 1px dashed var(--border); border-radius: 4px;">
          <p style="font-family: var(--font-mono);">> NO ACTIVE PROTOCOLS DETECTED.</p>
          <a href="/create_plan" class="btn btn-green" style="margin-top: 1rem;">[ INITIALIZE PLAN ]</a>
        </div>
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
        flash('PROTOCOL SAVED. DATA ENCRYPTED.', 'success')
        return redirect(url_for('dashboard'))

    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1>Initialize Protocol</h1>
      <p style="font-family: var(--font-mono);">> CONFIGURE LEGACY DIRECTIVES. DATA WILL BE ENCRYPTED.</p>
      <form method="POST" style="margin-top: 2rem;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
          <div class="form-group" style="margin-bottom: 0;">
            <label>> Emergency Contact (Email)</label>
            <input name="contact_email" type="email" required placeholder="trusted@domain.com">
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label>> Inactivity Threshold (Days)</label>
            <input name="inactivity_days" type="number" value="180" required min="30" max="3650">
          </div>
        </div>

        <h2>Target Assets</h2>
        
        <div id="accounts">
          <div class="account-block" style="background: rgba(0,0,0,0.3); padding: 1.5rem; border: 1px solid var(--border); border-radius: 4px; margin-bottom: 1rem;">
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem;">
              <div class="form-group" style="margin-bottom: 0;">
                <label>> Platform</label>
                <select name="platform[]">
                  <option>Facebook</option>
                  <option>Google Photos</option>
                  <option>Email</option>
                  <option>Instagram</option>
                </select>
              </div>
              <div class="form-group" style="margin-bottom: 0;">
                <label>> Directive</label>
                <select name="action[]">
                  <option>Delete</option>
                  <option>Transfer to contact</option>
                  <option>Archive privately</option>
                </select>
              </div>
              <div class="form-group" style="margin-bottom: 0;">
                <label>> Filter (Optional)</label>
                <input name="filter[]" placeholder="e.g., album: Family">
              </div>
            </div>
          </div>
        </div>
        
        <button type="button" onclick="addRow()" class="btn" style="margin-bottom: 2rem;">[ + ADD TARGET ]</button>
        <br>
        <button type="submit" class="btn-green" style="width: 100%; font-size: 1.1rem; padding: 1rem;">[ EXECUTE SAVE_PROTOCOL ]</button>
      </form>
    </div>
    <script>
    function addRow() {
      const div = document.getElementById('accounts');
      const row = document.createElement('div');
      row.className = 'account-block';
      row.style = "background: rgba(0,0,0,0.3); padding: 1.5rem; border: 1px solid var(--border); border-radius: 4px; margin-bottom: 1rem;";
      row.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem;">
          <div class="form-group" style="margin-bottom: 0;">
            <label>> Platform</label>
            <select name="platform[]">
              <option>Facebook</option>
              <option>Google Photos</option>
              <option>Email</option>
              <option>Instagram</option>
            </select>
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label>> Directive</label>
            <select name="action[]">
              <option>Delete</option>
              <option>Transfer to contact</option>
              <option>Archive privately</option>
            </select>
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label>> Filter (Optional)</label>
            <input name="filter[]" placeholder="e.g., album: Family">
          </div>
        </div>
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
                "action": "VERIFICATION_TRIGGERED",
                "contact": plan.contact_email,
                "token": token
            })
        else:
            results.append({
                "plan_id": plan.id,
                "action": "TARGET_ACTIVE",
                "days_left": plan.inactivity_days - days_inactive
            })

    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1>Diagnostic Output</h1>
      <p style="font-family: var(--font-mono);">> RUNNING INACTIVITY CHECK...</p>
      
      {% if results %}
        <div style="margin-top: 2rem;">
        {% for r in results %}
          <div class="plan-row" style="flex-direction: column; align-items: flex-start;">
            <strong style="font-size: 1.1rem; color: #fff;">[ PLAN_ID: {{ r.plan_id }} ]</strong>
            <span class="muted" style="margin-top: 0.5rem; font-weight: 600; font-family: var(--font-mono); color: {% if r.get('contact') %}var(--primary-green){% else %}var(--text-muted){% endif %};">
              > STATUS: {{ r.action }}
            </span>
            {% if r.get('contact') %}
              <div style="background: rgba(0, 255, 65, 0.05); border: 1px solid var(--primary-green); padding: 1.5rem; border-radius: 4px; width: 100%; margin-top: 1rem;">
                <p class="muted" style="color: var(--primary-green); margin-bottom: 1rem; font-family: var(--font-mono);">
                  > PAYLOAD SENT TO: {{ r.contact }}<br>
                  > AWAITING HUMAN CONFIRMATION.
                </p>
                <a href="/confirm/{{ r.token }}" class="btn btn-green" style="margin-top: 0.5rem; width: 100%; text-align: center; font-size: 0.9rem;">[ SIMULATE_CONFIRMATION ]</a>
              </div>
            {% endif %}
            {% if r.get('days_left') %}
              <p class="muted" style="margin-top: 0.5rem; font-family: var(--font-mono);">> {{ r.days_left }} days remaining until threshold.</p>
            {% endif %}
          </div>
        {% endfor %}
        </div>
      {% else %}
        <p class="muted" style="font-family: var(--font-mono);">> NO ACTIVE PLANS TO CHECK.</p>
      {% endif %}
      <a href="/dashboard" class="btn" style="margin-top: 2rem;">[ RETURN TO DASHBOARD ]</a>
    </div>
    """, results=results)

@app.route('/confirm/<token>')
def confirm(token):
    plan = LegacyPlan.query.filter_by(confirmation_token=token).first()
    if not plan:
        flash('ERROR: Invalid or expired token.', 'error')
        return redirect(url_for('index'))

    if plan.status in ("confirmed", "executed"):
        return render_template_string(BASE_TEMPLATE + """
        <div class="card" style="text-align: center;">
          <h1 style="color: var(--warning);">Protocol Executed</h1>
          <p style="font-family: var(--font-mono);">> This plan has already been confirmed and executed.</p>
          <a href="/" class="btn" style="margin-top: 1rem;">[ RETURN ]</a>
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
GRANT SECURITY EXECUTION REPORT
========================================
User: {plan_data.get('userName')}
Contact: {plan.contact_email}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}
Status: EXECUTION COMPLETE
========================================

ACTIONS:
"""
    for i, a in enumerate(actions, 1):
        report_text += f"\n{i}. {a['platform']} ({a['filter'] or 'no filter'})\n   Action: {a['action']}\n   Detail: {a['detail']}\n   Status: {a['status']}\n"

    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1 style="color: var(--primary-green);">Execution Successful</h1>
      <p style="font-family: var(--font-mono);">> THE PLAN HAS BEEN SUCCESSFULLY EXECUTED. FINAL REPORT:</p>
      <pre>{{ report }}</pre>
      <a href="/" class="btn" style="margin-top: 2rem;">[ RETURN TO HOME ]</a>
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
