"""
GRANT SECURITY — PREMIUM CYBERSECURITY COMMAND CENTER
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
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>GRANT Security | Command Center</title>
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
:root { 
    --bg: #020202; 
    --panel: rgba(10, 15, 20, 0.85); 
    --green: #00ff41; 
    --green-dim: #00cc33;
    --cyan: #00ffff;
    --text: #e6edf3; 
    --muted: #8b949e; 
    --border: #1b222c; 
    --danger: #ff003c; 
    --warn: #ffb000; 
    --mono: 'Fira Code', monospace;
    --tech: 'Share Tech Mono', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { 
    font-family: var(--mono); 
    background-color: var(--bg); 
    color: var(--text); 
    line-height: 1.6; 
    min-height: 100vh; 
    overflow-x: hidden;
}
body::after {
    content: " ";
    display: block;
    position: fixed;
    top: 0; left: 0; bottom: 0; right: 0;
    background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
    z-index: 2;
    background-size: 100% 2px, 3px 100%;
    pointer-events: none;
}
#matrix-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; opacity: 0.15; }
nav { 
    background: rgba(2, 2, 2, 0.9); 
    padding: 1rem 2rem; 
    display: flex; 
    justify-content: space-between; 
    border-bottom: 1px solid var(--green); 
    position: sticky; 
    top: 0; 
    z-index: 100; 
    backdrop-filter: blur(10px);
    box-shadow: 0 0 15px rgba(0, 255, 65, 0.2);
}
.brand { 
    color: var(--green); 
    font-family: var(--tech); 
    font-weight: 600; 
    font-size: 1.5rem; 
    text-decoration: none; 
    text-transform: uppercase; 
    text-shadow: 0 0 10px var(--green);
    letter-spacing: 2px;
}
.nav-links { display: flex; gap: 1.5rem; font-family: var(--tech); }
nav a:not(.brand) { 
    color: var(--text); 
    text-decoration: none; 
    font-size: 1rem; 
    padding: 0.5rem; 
    transition: 0.3s; 
    border-bottom: 2px solid transparent;
}
nav a:not(.brand):hover { 
    color: var(--green); 
    text-shadow: 0 0 8px var(--green); 
    border-bottom: 2px solid var(--green);
}
.container { max-width: 1000px; margin: 3rem auto; padding: 0 1.5rem; position: relative; z-index: 10; }
.card { 
    background: var(--panel); 
    padding: 3rem; 
    border-radius: 4px; 
    border: 1px solid var(--border); 
    border-left: 4px solid var(--green); 
    margin-bottom: 2rem; 
    backdrop-filter: blur(15px); 
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8), inset 0 0 20px rgba(0, 255, 65, 0.05);
    position: relative;
}
.card::before {
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, transparent, var(--green), transparent);
    opacity: 0.5;
}
h1 { 
    color: #fff; 
    font-family: var(--tech); 
    font-size: 2.2rem; 
    margin-bottom: 1rem; 
    text-transform: uppercase; 
    text-shadow: 0 0 15px rgba(0, 255, 65, 0.5);
    letter-spacing: 2px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 1rem;
}
h2 { 
    color: var(--green); 
    font-family: var(--tech); 
    font-size: 1.3rem; 
    margin: 2rem 0 1rem; 
    border-bottom: 1px dashed var(--border); 
    padding-bottom: 0.5rem; 
    text-shadow: 0 0 5px rgba(0, 255, 65, 0.3);
}
p { margin-bottom: 1rem; color: var(--muted); }
.form-group { margin-bottom: 1.5rem; }
label { 
    display: block; 
    margin-bottom: 0.5rem; 
    font-family: var(--tech); 
    font-size: 0.9rem; 
    color: var(--green); 
    text-transform: uppercase; 
    letter-spacing: 1px;
}
input, select { 
    width: 100%; 
    padding: 0.8rem; 
    border: 1px solid var(--border); 
    border-radius: 4px; 
    font-family: var(--mono); 
    background: rgba(0,0,0,0.8); 
    color: var(--green); 
    transition: 0.3s;
    box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
}
input:focus, select:focus { 
    outline: none; 
    border-color: var(--green); 
    box-shadow: 0 0 15px rgba(0, 255, 65, 0.3), inset 0 0 10px rgba(0,255,65,0.1); 
}
button, .btn { 
    display: inline-block; 
    padding: 0.9rem 1.8rem; 
    background: transparent; 
    color: var(--green); 
    border: 1px solid var(--green); 
    border-radius: 4px; 
    font-family: var(--tech); 
    font-weight: 600; 
    font-size: 1.1rem;
    text-transform: uppercase; 
    cursor: pointer; 
    text-decoration: none; 
    margin-top: 0.5rem; 
    transition: 0.3s;
    position: relative;
    overflow: hidden;
    box-shadow: 0 0 10px rgba(0, 255, 65, 0.1);
}
button:hover, .btn:hover { 
    background: rgba(0, 255, 65, 0.1); 
    box-shadow: 0 0 25px rgba(0, 255, 65, 0.5); 
    text-shadow: 0 0 8px var(--green); 
}
.btn-green { 
    background: var(--green); 
    color: #000; 
    box-shadow: 0 0 15px rgba(0, 255, 65, 0.4);
}
.btn-green:hover { 
    background: #fff; 
    border-color: #fff; 
    box-shadow: 0 0 30px #fff; 
}
.flash { 
    padding: 1rem; 
    border-radius: 4px; 
    margin-bottom: 1.5rem; 
    font-family: var(--mono); 
    font-size: 0.95rem; 
    border: 1px solid; 
    background: rgba(0,0,0,0.9);
    display: flex;
    align-items: center;
}
.flash::before { content: "> "; margin-right: 10px; font-weight: bold; }
.flash.success { border-color: var(--green); color: var(--green); box-shadow: 0 0 15px rgba(0, 255, 65, 0.2); }
.flash.error { border-color: var(--danger); color: var(--danger); box-shadow: 0 0 15px rgba(255, 0, 60, 0.2); }
.plan-row { 
    display: flex; 
    justify-content: space-between; 
    align-items: center; 
    padding: 1.5rem; 
    background: rgba(0,0,0,0.6); 
    border: 1px solid var(--border); 
    border-radius: 4px; 
    margin-bottom: 1rem; 
    font-family: var(--mono); 
    transition: 0.3s; 
}
.plan-row:hover { 
    border-color: var(--green); 
    box-shadow: 0 0 20px rgba(0, 255, 65, 0.1); 
    transform: translateX(5px);
}
.badge { 
    padding: 0.3rem 1rem; 
    border-radius: 4px; 
    font-size: 0.8rem; 
    font-weight: 600; 
    text-transform: uppercase; 
    font-family: var(--tech); 
    letter-spacing: 1px;
}
.badge-active { border: 1px solid var(--green); color: var(--green); box-shadow: 0 0 10px rgba(0,255,65,0.3); }
.badge-pending_verification { border: 1px solid var(--warn); color: var(--warn); box-shadow: 0 0 10px rgba(255,176,0,0.3); }
.badge-executed { border: 1px solid var(--cyan); color: var(--cyan); box-shadow: 0 0 10px rgba(0,255,255,0.3); }
pre { 
    background: rgba(0,0,0,0.95); 
    color: var(--green); 
    padding: 1.5rem; 
    border-radius: 4px; 
    font-family: var(--mono); 
    font-size: 0.9rem; 
    border: 1px solid var(--border); 
    border-left: 3px solid var(--green); 
    white-space: pre-wrap; 
    box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
}
.muted { color: var(--muted); font-size: 0.85rem; display: block; margin-top: 0.25rem; font-family: var(--mono); }
</style></head><body>
<canvas id="matrix-canvas"></canvas>
<nav><a href="/" class="brand">[ GRANT_SYS ]</a><div class="nav-links"><a href="/">~ /home</a>
{% if current_user.is_authenticated %}<a href="/dashboard">~ /dashboard</a><a href="/create_plan">~ /new_plan</a><a href="/logout" style="color: var(--danger);">~ /logout</a>
{% else %}<a href="/signup">~ /signup</a><a href="/login">~ /login</a>{% endif %}</div></nav>
<div class="container">{% with messages = get_flashed_messages(with_categories=true) %}{% for category, message in messages %}<div class="flash {{ category }}">{{ message }}</div>{% endfor %}{% endwith %}
"""

MATRIX_JS = """
<script>
const canvas = document.getElementById('matrix-canvas');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;
const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*()_+{}|:<>?";
const fontSize = 18;
const columns = canvas.width / fontSize;
const drops = [];
for (let x = 0; x < columns; x++) drops[x] = 1;

function draw() {
    ctx.fillStyle = "rgba(2, 2, 2, 0.08)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#00ff41";
    ctx.font = fontSize + "px 'Share Tech Mono', monospace";
    for (let i = 0; i < drops.length; i++) {
        const text = letters.charAt(Math.floor(Math.random() * letters.length));
        ctx.fillText(text, i * fontSize, drops[i] * fontSize);
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.95) drops[i] = 0;
        drops[i]++;
    }
}
setInterval(draw, 40);
window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
});
</script>
"""

@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="text-align: center; padding: 5rem 2rem;">
      <h1 style="font-size: 3rem; border: none; text-shadow: 0 0 20px var(--green);">GRANT Security</h1>
      <p style="font-family: var(--tech); font-size: 1.2rem; color: var(--green); margin-bottom: 2rem;">
        > SYSTEM ONLINE<br>> AES-256 ENCRYPTION ACTIVE<br>> AWAITING OPERATOR INPUT
      </p>
      <p style="max-width: 700px; margin: 0 auto 3rem; color: var(--text);">
        Ensure your digital footprint is secured and handled exactly according to your directives. Set up an encrypted legacy plan while alive. The system will execute the rest upon verified human confirmation.
      </p>
      <div style="display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap;">
        {% if not current_user.is_authenticated %}
          <a href="/signup" class="btn btn-green" style="padding: 1rem 2.5rem;">[ INITIALIZE_ACCOUNT ]</a>
          <a href="/login" class="btn" style="padding: 1rem 2.5rem;">[ SYSTEM_LOGIN ]</a>
        {% else %}
          <a href="/create_plan" class="btn btn-green" style="padding: 1rem 2.5rem;">[ NEW_PROTOCOL ]</a>
          <a href="/dashboard" class="btn" style="padding: 1rem 2.5rem;">[ DASHBOARD ]</a>
        {% endif %}
      </div>
    </div>
    """ + MATRIX_JS)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email, name, password = request.form['email'].strip().lower(), request.form['name'].strip(), request.form['password']
        if User.query.filter_by(email=email).first():
            flash('ERROR: Email already registered.', 'error')
            return redirect(url_for('signup'))
        db.session.add(User(email=email, name=name, password_hash=generate_password_hash(password)))
        db.session.commit()
        flash('SUCCESS: Account created. Proceed to login.', 'success')
        return redirect(url_for('login'))
    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="max-width: 500px; margin: 0 auto;">
      <h1>Register Operator</h1>
      <form method="POST" style="margin-top: 2rem;">
        <div class="form-group"><label>> Full Name</label><input name="name" required></div>
        <div class="form-group"><label>> Email Address</label><input name="email" type="email" required></div>
        <div class="form-group"><label>> Access Key</label><input name="password" type="password" required minlength="6"></div>
        <button type="submit" class="btn-green" style="width: 100%;">[ INITIALIZE ]</button>
      </form>
    </div>
    """ + MATRIX_JS)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email'].strip().lower()).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            flash('ACCESS GRANTED. Welcome to the mainframe.', 'success')
            return redirect(url_for('dashboard'))
        flash('ACCESS DENIED: Invalid credentials.', 'error')
    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="max-width: 500px; margin: 0 auto;">
      <h1>System Login</h1>
      <form method="POST" style="margin-top: 2rem;">
        <div class="form-group"><label>> Email Address</label><input name="email" type="email" required></div>
        <div class="form-group"><label>> Access Key</label><input name="password" type="password" required></div>
        <button type="submit" class="btn-green" style="width: 100%;">[ AUTHENTICATE ]</button>
      </form>
    </div>
    """ + MATRIX_JS)

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
    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
        <h1 style="margin: 0; border: none;">Ops Dashboard</h1>
        <a href="/create_plan" class="btn btn-green">[ + NEW_PROTOCOL ]</a>
      </div>
      {% if plans %}
        {% for plan in plans %}
          <div class="plan-row" style="flex-direction: column; align-items: flex-start;">
            <div style="width: 100%; display: flex; justify-content: space-between; align-items: center;">
              <strong style="font-size: 1.2rem; color: var(--green); font-family: var(--tech); text-shadow: 0 0 5px var(--green);">[ PLAN_ID: {{ plan.id }} ]</strong>
              <span class="badge badge-{{ plan.status }}">{{ plan.status.replace('_', ' ') }}</span>
            </div>
            <div style="margin-top: 1rem; width: 100%; padding-left: 1rem; border-left: 2px solid var(--border);">
              <span class="muted">PRIMARY E-MAIL: {{ plan.primary_email }}</span>
              <span class="muted">SECONDARY E-MAIL: {{ plan.secondary_email or 'NONE' }}</span>
              <span class="muted">THRESHOLD: {{ plan.inactivity_days }} days | LAST_CHECKIN: {{ plan.last_activity.strftime('%Y-%m-%d') }}</span>
            </div>
          </div>
        {% endfor %}
        <div style="margin-top: 2rem;">
          <a href="/run_check" class="btn" style="width: 100%; text-align: center; border-color: var(--warn); color: var(--warn);">[ RUN SYSTEM DIAGNOSTIC ]</a>
        </div>
      {% else %}
        <p style="font-family: var(--mono); text-align: center; padding: 2rem;">> NO ACTIVE PROTOCOLS DETECTED.</p>
      {% endif %}
    </div>
    """ + MATRIX_JS, plans=plans)

@app.route('/create_plan', methods=['GET', 'POST'])
@login_required
def create_plan():
    if request.method == 'POST':
        accounts = [{"platform": p, "action": a, "filter": f.strip()} for p, a, f in zip(request.form.getlist('platform[]'), request.form.getlist('action[]'), request.form.getlist('filter[]')) if p and a]
        plan_data = {"userName": current_user.name, "accounts": accounts, "createdAt": datetime.utcnow().isoformat()}
        db.session.add(LegacyPlan(user_id=current_user.id, encrypted_data=encrypt_plan(plan_data), primary_email=request.form['primary_email'].strip().lower(), secondary_email=request.form.get('secondary_email', '').strip().lower() or None, inactivity_days=int(request.form['inactivity_days']), last_activity=datetime.utcnow(), status="active"))
        db.session.commit()
        flash('PROTOCOL SAVED. DATA ENCRYPTED.', 'success')
        return redirect(url_for('dashboard'))
    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <h1>Initialize Protocol</h1>
      <form method="POST" style="margin-top: 2rem;">
        <h2>E-mail Escalation Path</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
          <div class="form-group" style="margin:0;"><label>> Primary E-mail</label><input name="primary_email" type="email" required></div>
          <div class="form-group" style="margin:0;"><label>> Secondary E-mail</label><input name="secondary_email" type="email"><span class="muted" style="text-transform:none;">Used after 7 days of no response.</span></div>
        </div>
        <div class="form-group"><label>> Inactivity Threshold (Days)</label><input name="inactivity_days" type="number" value="180" required min="1"></div>
        <h2>Target Assets</h2>
        <div id="accounts">
          <div class="account-block" style="background: rgba(0,0,0,0.5); padding: 1.5rem; border: 1px solid var(--border); margin-bottom: 1rem;">
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem;">
              <div class="form-group" style="margin:0;"><label>> Platform</label><select name="platform[]"><option>WhatsApp</option><option>Discord</option><option>X</option><option>Threads</option><option>Instagram</option><option>Pinterest</option><option>LinkedIn</option></select></div>
              <div class="form-group" style="margin:0;"><label>> Directive</label><select name="action[]"><option>Delete</option><option>Transfer to contact</option><option>Archive privately</option></select></div>
              <div class="form-group" style="margin:0;"><label>> Filter (Optional)</label><input name="filter[]" placeholder="e.g., Specific Album / Chat"></div>
            </div>
          </div>
        </div>
        <button type="button" onclick="addRow()" class="btn" style="margin-bottom: 2rem;">[ + ADD_TARGET ]</button><br>
        <button type="submit" class="btn-green" style="width: 100%; padding: 1rem;">[ EXECUTE_SAVE ]</button>
      </form>
    </div>
    <script>
    function addRow() {
      const d = document.getElementById('accounts'); const r = document.createElement('div');
      r.style = "background: rgba(0,0,0,0.5); padding: 1.5rem; border: 1px solid var(--border); margin-bottom: 1rem;";
      r.innerHTML = `<div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem;"><div class="form-group" style="margin:0;"><label>> Platform</label><select name="platform[]"><option>WhatsApp</option><option>Discord</option><option>X</option><option>Threads</option><option>Instagram</option><option>Pinterest</option><option>LinkedIn</option></select></div><div class="form-group" style="margin:0;"><label>> Directive</label><select name="action[]"><option>Delete</option><option>Transfer to contact</option><option>Archive privately</option></select></div><div class="form-group" style="margin:0;"><label>> Filter</label><input name="filter[]" placeholder="e.g., Specific Album"></div></div>`;
      d.appendChild(r);
    }
    </script>
    """ + MATRIX_JS)

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
    <div class="card">
      <h1>System Diagnostic</h1>
      {% if results %}
        {% for r in results %}
          <div class="plan-row" style="flex-direction: column; align-items: flex-start;">
            <strong style="color: var(--warn); font-family: var(--tech); font-size: 1.1rem;">> STATUS: {{ r.action }}</strong>
            {% if r.get('contact') %}
              <div style="background: rgba(0,255,65,0.05); padding: 1.5rem; width: 100%; margin-top: 1rem; border: 1px solid var(--green); border-left: 4px solid var(--green);">
                <p class="muted" style="color:var(--text); margin-bottom: 1rem;">[ TARGET {{ r.type }}: {{ r.contact }} ]</p>
                <a href="/verify/{{ r.token }}" class="btn btn-green" style="width: 100%; text-align: center;">[ VERIFY & EXECUTE ]</a>
              </div>
            {% endif %}
          </div>
        {% endfor %}
      {% else %}
        <p style="font-family: var(--mono);">> NO ACTIVE PROTOCOLS DETECTED.</p>
      {% endif %}
      <a href="/dashboard" class="btn" style="margin-top: 2rem;">[ RETURN TO DASHBOARD ]</a>
    </div>
    """ + MATRIX_JS, results=results)

@app.route('/verify/<token>', methods=['GET', 'POST'])
def verify_documents(token):
    plan = LegacyPlan.query.filter_by(confirmation_token=token).first()
    if not plan: return "Invalid token", 404
    if plan.status in ("confirmed", "executed"): return "Already executed", 400

    if request.method == 'POST':
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
      <h1 style="color: var(--warn);">2FA Document Verification</h1>
      <p style="font-family: var(--mono); color: var(--warn);">> ACTION REQUIRED: UPLOAD ID & DEATH CERTIFICATE TO PROCEED.</p>
      <form method="POST" enctype="multipart/form-data" style="margin-top: 2rem;">
        <div class="form-group">
          <label>>
