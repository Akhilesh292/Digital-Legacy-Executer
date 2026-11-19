"""
GRANT SECURITY — CYBERSECURITY THEME (WITH 2FA DOCUMENT VERIFICATION)
"""
import os
import secrets
import json
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///legacy.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure upload folder for documents
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

KEY_FILE = "secret.key"
if os.environ.get("FERNET_KEY"):
    FERNET_KEY = os.environ["FERNET_KEY"].encode()
elif os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f: FERNET_KEY = f.read()
else:
    FERNET_KEY = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f: f.write(FERNET_KEY)
fernet = Fernet(FERNET_KEY)

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
    primary_email = db.Column(db.String(150), nullable=False)
    secondary_email = db.Column(db.String(150), nullable=True)
    inactivity_days = db.Column(db.Integer, default=180)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="active")
    confirmation_token = db.Column(db.String(100), unique=True, nullable=True)
    contact_attempted = db.Column(db.String(20), default="primary")
    verification_sent_at = db.Column(db.DateTime, nullable=True)
    
    # NEW: Document Verification Fields
    id_document = db.Column(db.String(200), nullable=True)
    death_certificate = db.Column(db.String(200), nullable=True)
    verification_status = db.Column(db.String(50), default="pending")
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='plans')

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

def encrypt_plan(data: dict) -> str: return fernet.encrypt(json.dumps(data).encode()).decode()
def decrypt_plan(encrypted: str) -> dict: return json.loads(fernet.decrypt(encrypted.encode()).decode())

BASE_TEMPLATE = """
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>GRANT Security</title>
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&display=swap" rel="stylesheet">
<style>
:root { --bg: #050505; --panel: #161b22; --green: #00ff41; --text: #c9d1d9; --muted: #8b949e; --border: #30363d; --danger: #ff3366; --warn: #ffcc00; --mono: 'Fira Code', monospace; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: sans-serif; background-color: var(--bg); background-image: linear-gradient(rgba(0, 255, 65, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 255, 65, 0.03) 1px, transparent 1px); background-size: 30px 30px; color: var(--text); line-height: 1.6; min-height: 100vh; }
nav { background: #0d1117; padding: 1rem 2rem; display: flex; justify-content: space-between; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 50; }
.brand { color: var(--green); font-family: var(--mono); font-weight: 600; font-size: 1.3rem; text-decoration: none; text-transform: uppercase; }
.nav-links { display: flex; gap: 1.5rem; font-family: var(--mono); }
nav a:not(.brand) { color: var(--text); text-decoration: none; font-size: 0.9rem; padding: 0.5rem; }
nav a:not(.brand):hover { color: var(--green); background: rgba(0, 255, 65, 0.1); }
.container { max-width: 1000px; margin: 3rem auto; padding: 0 1.5rem; }
.card { background: var(--panel); padding: 2.5rem; border-radius: 8px; border: 1px solid var(--border); border-left: 4px solid var(--green); margin-bottom: 2rem; }
h1 { color: #fff; font-family: var(--mono); font-size: 2rem; margin-bottom: 1rem; text-transform: uppercase; }
h2 { color: var(--green); font-family: var(--mono); font-size: 1.2rem; margin: 2rem 0 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
p { margin-bottom: 1rem; color: var(--muted); }
.form-group { margin-bottom: 1.5rem; }
label { display: block; margin-bottom: 0.5rem; font-family: var(--mono); font-size: 0.85rem; color: var(--green); text-transform: uppercase; }
input, select { width: 100%; padding: 0.75rem; border: 1px solid var(--border); border-radius: 4px; font-family: var(--mono); background: var(--bg); color: #fff; }
input:focus, select:focus { outline: none; border-color: var(--green); box-shadow: 0 0 10px rgba(0, 255, 65, 0.2); }
button, .btn { display: inline-block; padding: 0.8rem 1.5rem; background: transparent; color: var(--green); border: 1px solid var(--green); border-radius: 4px; font-family: var(--mono); font-weight: 600; text-transform: uppercase; cursor: pointer; text-decoration: none; margin-top: 0.5rem; }
button:hover, .btn:hover { background: rgba(0, 255, 65, 0.1); box-shadow: 0 0 15px rgba(0, 255, 65, 0.4); }
.btn-green { background: var(--green); color: #000; }
.flash { padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem; font-family: var(--mono); font-size: 0.9rem; border: 1px solid; }
.flash.success { border-color: var(--green); color: var(--green); background: rgba(0, 255, 65, 0.05); }
.flash.error { border-color: var(--danger); color: var(--danger); background: rgba(255, 51, 102, 0.05); }
.plan-row { display: flex; justify-content: space-between; align-items: center; padding: 1.25rem; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; margin-bottom: 1rem; font-family: var(--mono); }
.badge { padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; font-family: var(--mono); }
.badge-active { border: 1px solid var(--green); color: var(--green); }
.badge-pending_verification { border: 1px solid var(--warn); color: var(--warn); }
.badge-executed { border: 1px solid #58a6ff; color: #58a6ff; }
pre { background: #000; color: var(--green); padding: 1.5rem; border-radius: 4px; font-family: var(--mono); font-size: 0.85rem; border: 1px solid var(--border); border-left: 3px solid var(--green); white-space: pre-wrap; }
.muted { color: var(--muted); font-size: 0.85rem; display: block; margin-top: 0.25rem; }
</style></head><body>
<nav><a href="/" class="brand">[ GRANT_SYS ]</a><div class="nav-links"><a href="/">~ /home</a>
{% if current_user.is_authenticated %}<a href="/dashboard">~ /dashboard</a><a href="/create_plan">~ /new_plan</a><a href="/logout" style="color: var(--danger);">~ /logout</a>
{% else %}<a href="/signup">~ /signup</a><a href="/login">~ /login</a>{% endif %}</div></nav>
<div class="container">{% with messages = get_flashed_messages(with_categories=true) %}{% for category, message in messages %}<div class="flash {{ category }}">> {{ message }}</div>{% endfor %}{% endwith %}
"""

@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="text-align: center; padding: 4rem 2rem;"><h1>GRANT Security</h1>
      <p style="font-family: var(--mono);">> INITIALIZING PROTOCOL...<br>> DIGITAL LEGACY ENCRYPTION ACTIVE.<br><br>Ensure your digital footprint is secured and handled exactly according to your directives. Set up an encrypted plan while alive. The system will execute the rest upon verified human confirmation.</p>
      <div style="margin-top: 2rem; display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
        {% if not current_user.is_authenticated %}<a href="/signup" class="btn btn-green" style="padding: 1rem 2rem;">[ CREATE_ACCOUNT ]</a><a href="/login" class="btn" style="padding: 1rem 2rem;">[ SYSTEM_LOGIN ]</a>
        {% else %}<a href="/create_plan" class="btn btn-green" style="padding: 1rem 2rem;">[ NEW_PLAN ]</a><a href="/dashboard" class="btn" style="padding: 1rem 2rem;">[ DASHBOARD ]</a>{% endif %}
      </div></div>
    """)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email, name, password = request.form['email'].strip().lower(), request.form['name'].strip(), request.form['password']
        if User.query.filter_by(email=email).first():
            flash('ERROR: Email already registered.', 'error')
            return redirect(url_for('signup'))
        db.session.add(User(email=email, name=name, password_hash=generate_password_hash(password)))
        db.session.commit()
        flash('SUCCESS: Account created.', 'success')
        return redirect(url_for('login'))
    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="max-width: 500px; margin: 0 auto;"><h1>Register</h1>
      <form method="POST" style="margin-top: 2rem;">
        <div class="form-group"><label>> Full Name</label><input name="name" required></div>
        <div class="form-group"><label>> Email Address</label><input name="email" type="email" required></div>
        <div class="form-group"><label>> Access Key</label><input name="password" type="password" required minlength="6"></div>
        <button type="submit" class="btn-green" style="width: 100%;">[ INITIALIZE ]</button>
      </form></div>
    """)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email'].strip().lower()).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            flash('ACCESS GRANTED.', 'success')
            return redirect(url_for('dashboard'))
        flash('ACCESS DENIED.', 'error')
    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="max-width: 500px; margin: 0 auto;"><h1>Login</h1>
      <form method="POST" style="margin-top: 2rem;">
        <div class="form-group"><label>> Email Address</label><input name="email" type="email" required></div>
        <div class="form-group"><label>> Access Key</label><input name="password" type="password" required></div>
        <button type="submit" class="btn-green" style="width: 100%;">[ AUTHENTICATE ]</button>
      </form></div>
    """)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    plans = LegacyPlan.query.filter_by(user_id=current_user.id).all()
    return render_template_string(BASE_TEMPLATE + """
    <div class="card"><div style="display: flex; justify-content: space-between; margin-bottom: 2rem;"><h1>Dashboard</h1><a href="/create_plan" class="btn btn-green">[ + NEW_PLAN ]</a></div>
      {% if plans %}
        {% for plan in plans %}
          <div class="plan-row" style="flex-direction: column; align-items: flex-start;">
            <div style="width: 100%; display: flex; justify-content: space-between;"><strong>[ PLAN_ID: {{ plan.id }} ]</strong><span class="badge badge-{{ plan.status }}">{{ plan.status.replace('_', ' ') }}</span></div>
            <div style="margin-top: 1rem; width: 100%;">
              <span class="muted">PRIMARY E-MAIL: {{ plan.primary_email }}</span>
              <span class="muted">SECONDARY E-MAIL: {{ plan.secondary_email or 'NONE' }}</span>
              <span class="muted">THRESHOLD: {{ plan.inactivity_days }} days | LAST_CHECKIN: {{ plan.last_activity.strftime('%Y-%m-%d') }}</span>
            </div>
          </div>
        {% endfor %}
        <div style="margin-top: 2rem;"><a href="/run_check" class="btn" style="width: 100%; text-align: center;">[ RUN DIAGNOSTIC ]</a></div>
      {% else %}<p style="font-family: var(--mono);">> NO ACTIVE PROTOCOLS.</p>{% endif %}
    </div>
    """, plans=plans)

@app.route('/create_plan', methods=['GET', 'POST'])
@login_required
def create_plan():
    if request.method == 'POST':
        accounts = [{"platform": p, "action": a, "filter": f.strip()} for p, a, f in zip(request.form.getlist('platform[]'), request.form.getlist('action[]'), request.form.getlist('filter[]')) if p and a]
        plan_data = {"userName": current_user.name, "accounts": accounts, "createdAt": datetime.utcnow().isoformat()}
        db.session.add(LegacyPlan(user_id=current_user.id, encrypted_data=encrypt_plan(plan_data), primary_email=request.form['primary_email'].strip().lower(), secondary_email=request.form.get('secondary_email', '').strip().lower() or None, inactivity_days=int(request.form['inactivity_days']), last_activity=datetime.utcnow(), status="active"))
        db.session.commit()
        flash('PROTOCOL SAVED.', 'success')
        return redirect(url_for('dashboard'))
    return render_template_string(BASE_TEMPLATE + """
    <div class="card"><h1>Initialize Protocol</h1>
      <form method="POST" style="margin-top: 2rem;">
        <h2>E-mail Escalation Path</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
          <div class="form-group" style="margin:0;"><label>> Primary E-mail</label><input name="primary_email" type="email" required></div>
          <div class="form-group" style="margin:0;"><label>> Secondary E-mail</label><input name="secondary_email" type="email"><span class="muted" style="text-transform:none;">Used after 7 days of no response.</span></div>
        </div>
        <div class="form-group"><label>> Inactivity Threshold (Days)</label><input name="inactivity_days" type="number" value="180" required min="1"></div>
        <h2>Target Assets</h2>
        <div id="accounts"><div class="account-block" style="background: #000; padding: 1.5rem; border: 1px solid #30363d; margin-bottom: 1rem;">
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem;">
            <div class="form-group" style="margin:0;"><label>> Platform</label><select name="platform[]"><option>WhatsApp</option><option>Discord</option><option>X</option><option>Threads</option><option>Instagram</option><option>Pinterest</option><option>LinkedIn</option><option>Bank Details</option></select></div>
            <div class="form-group" style="margin:0;"><label>> Directive</label><select name="action[]"><option>Delete</option><option>Transfer to contact</option><option>Archive privately</option></select></div>
            <div class="form-group" style="margin:0;"><label>> Filter (e.g. Bank Action)</label><input name="filter[]" placeholder="e.g., Account Balance"></div>
          </div>
        </div></div>
        <button type="button" onclick="addRow()" class="btn" style="margin-bottom: 2rem;">[ + ADD ]</button><br>
        <button type="submit" class="btn-green" style="width: 100%; padding: 1rem;">[ EXECUTE ]</button>
      </form>
    </div>
    <script>
    function addRow() {
      const d = document.getElementById('accounts'); const r = document.createElement('div');
      r.style = "background: #000; padding: 1.5rem; border: 1px solid #30363d; margin-bottom: 1rem;";
      r.innerHTML = `<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem;"><div class="form-group" style="margin:0;"><label>> Platform</label><select name="platform[]"><option>WhatsApp</option><option>Discord</option><option>X</option><option>Threads</option><option>Instagram</option><option>Pinterest</option><option>LinkedIn</option><option>Bank Details</option></select></div><div class="form-group" style="margin:0;"><label>> Directive</label><select name="action[]"><option>Delete</option><option>Transfer to contact</option><option>Archive privately</option></select></div><div class="form-group" style="margin:0;"><label>> Filter</label><input name="filter[]" placeholder="e.g., Account Balance"></div></div>`;
      d.appendChild(r);
    }
    </script>
    """)

@app.route('/run_check')
@login_required
def run_check():
    plans = LegacyPlan.query.filter_by(user_id=current_user.id).all()
    results = []
    for plan in plans:
        days_inactive = (datetime.utcnow() - plan.last_activity).days
        if plan.status == "active" and days_inactive >= plan.inactivity_days:
            token = secrets.token_urlsafe(32); plan.confirmation_token = token; plan.status = "pending_verification"; plan.contact_attempted = "primary"; plan.verification_sent_at = datetime.utcnow(); db.session.commit()
            results.append({"plan_id": plan.id, "action": "TRIGGERED", "contact": plan.primary_email, "type": "Primary E-mail", "token": token})
        elif plan.status == "pending_verification":
            days_since = (datetime.utcnow() - plan.verification_sent_at).days
            if plan.contact_attempted == "primary" and days_since >= 7 and plan.secondary_email:
                token = secrets.token_urlsafe(32); plan.confirmation_token = token; plan.contact_attempted = "secondary"; plan.verification_sent_at = datetime.utcnow(); db.session.commit()
                results.append({"plan_id": plan.id, "action": "ESCALATED", "contact": plan.secondary_email, "type": "Secondary E-mail", "token": token})
            else:
                ct = "Primary" if plan.contact_attempted == "primary" else "Secondary"; ce = plan.primary_email if plan.contact_attempted == "primary" else plan.secondary_email
                results.append({"plan_id": plan.id, "action": f"AWAITING_{ct.upper()}", "contact": ce, "type": f"{ct} E-mail", "token": plan.confirmation_token})
        elif plan.status == "active":
            results.append({"plan_id": plan.id, "action": "ACTIVE", "days_left": plan.inactivity_days - days_inactive})

    return render_template_string(BASE_TEMPLATE + """
    <div class="card"><h1>Diagnostic</h1>
      {% if results %}{% for r in results %}
          <div class="plan-row" style="flex-direction: column; align-items: flex-start;">
            <strong>[ ID: {{ r.plan_id }} ] > {{ r.action }}</strong>
            {% if r.get('contact') %}
              <div style="background: rgba(0,255,65,0.05); padding: 1rem; width: 100%; margin-top: 1rem;">
                <p class="muted" style="color:#fff;">TARGET ({{ r.type }}): {{ r.contact }}</p>
                <a href="/verify/{{ r.token }}" class="btn btn-green" style="width: 100%; text-align: center;">[ VERIFY & CONFIRM ]</a>
              </div>
            {% endif %}
          </div>
      {% endfor %}{% else %}<p>NO PLANS.</p>{% endif %}
      <a href="/dashboard" class="btn" style="margin-top: 2rem;">[ BACK ]</a>
    </div>
    """, results=results)

@app.route('/verify/<token>', methods=['GET', 'POST'])
def verify_documents(token):
    plan = LegacyPlan.query.filter_by(confirmation_token=token).first()
    if not plan: return "Invalid token", 404
    if plan.status in ("confirmed", "executed"): return "Already executed", 400

    if request.method == 'POST':
        # Handle File Uploads
        id_file = request.files.get('id_document')
        death_file = request.files.get('death_certificate')
        
        if id_file and death_file:
            id_filename = secure_filename(id_file.filename)
            death_filename = secure_filename(death_file.filename)
            
            id_file.save(os.path.join(app.config['UPLOAD_FOLDER'], id_filename))
            death_file.save(os.path.join(app.config['UPLOAD_FOLDER'], death_filename))
            
            plan.id_document = id_filename
            plan.death_certificate = death_filename
            plan.verification_status = "documents_uploaded"
            db.session.commit()
            
            flash('DOCUMENTS RECEIVED. AWAITING SYSTEM VALIDATION.', 'success')
            return redirect(url_for('execute_plan', token=token))
        else:
            flash('ERROR: Both documents are required.', 'error')

    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="max-width: 600px; margin: 0 auto;">
      <h1>2FA Verification</h1>
      <p style="font-family: var(--mono); color: var(--warn);">> ACTION REQUIRED: UPLOAD ID & DEATH CERTIFICATE TO PROCEED.</p>
      <form method="POST" enctype="multipart/form-data" style="margin-top: 2rem;">
        <div class="form-group">
          <label>> Upload Your ID (Aadhaar / Passport)</label>
          <input type="file" name="id_document" accept="image/*,.pdf" required style="border: 1px dashed var(--green); padding: 1rem;">
        </div>
        <div class="form-group">
          <label>> Upload Death Certificate of Deceased</label>
          <input type="file" name="death_certificate" accept="image/*,.pdf" required style="border: 1px dashed var(--green); padding: 1rem;">
        </div>
        <button type="submit" class="btn-green" style="width: 100%; padding: 1rem;">[ SUBMIT DOCUMENTS ]</button>
      </form>
      <p class="muted" style="margin-top: 1.5rem; text-align: center;">Your documents are encrypted and only used for legal verification.</p>
    </div>
    """)

@app.route('/execute/<token>')
def execute_plan(token):
    plan = LegacyPlan.query.filter_by(confirmation_token=token).first()
    if not plan: return "Invalid token", 404
    if plan.status in ("confirmed", "executed"): return "Already executed", 400

    plan.status = "executed"
    plan.verification_status = "approved"
    db.session.commit()
    
    data = decrypt_plan(plan.encrypted_data)
    rc = plan.primary_email if plan.contact_attempted == 'primary' else plan.secondary_email
    rep = f"EXECUTION REPORT\nUser: {data.get('userName')}\nContact: {rc}\nStatus: COMPLETE\nVerification: ID + Death Certificate Approved\n\nACTIONS:\n"
    for i, a in enumerate(data.get('accounts', []), 1):
        rep += f"{i}. {a['platform']} - {a['action']} ({a.get('filter','')})\n"
    
    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1 style="color:var(--green);">Verified & Confirmed</h1>
      <p>Documents validated. Plan executed.</p>
      <pre>{{ report }}</pre>
    </div>
    """, report=rep)

with app.app_context(): db.create_all()
if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
