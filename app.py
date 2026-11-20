import os, secrets, json
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

try:
    from cryptography.fernet import Fernet
except ImportError:
    import base64, hashlib, hmac
    class Fernet:
        def __init__(self, key): self.raw_key = base64.urlsafe_b64decode(key if isinstance(key, bytes) else key.encode())
        @classmethod
        def generate_key(cls): return base64.urlsafe_b64encode(secrets.token_bytes(32))
        def encrypt(self, data):
            data = data if isinstance(data, bytes) else data.encode()
            iv = secrets.token_bytes(16)
            k = b"".join(hmac.new(self.raw_key, iv + i.to_bytes(4,'big'), hashlib.sha256).digest() for i in range((len(data)//32)+1))[:len(data)]
            c = bytes(a ^ b for a, b in zip(data, k))
            return base64.urlsafe_b64encode(iv + hmac.new(self.raw_key, iv+c, hashlib.sha256).digest() + c)
        def decrypt(self, token):
            token = token if isinstance(token, bytes) else token.encode()
            raw = base64.urlsafe_b64decode(token); iv, mac, c = raw[:16], raw[16:48], raw[48:]
            if not hmac.compare_digest(mac, hmac.new(self.raw_key, iv+c, hashlib.sha256).digest()): raise ValueError("MAC mismatch")
            k = b"".join(hmac.new(self.raw_key, iv + i.to_bytes(4,'big'), hashlib.sha256).digest() for i in range((len(c)//32)+1))[:len(c)]
            return bytes(a ^ b for a, b in zip(c, k))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///legacy.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

KEY_FILE = "secret.key"
if os.environ.get("FERNET_KEY"): FERNET_KEY = os.environ["FERNET_KEY"].encode()
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
    user = db.relationship('User', backref='plans')

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

def encrypt_plan(data): return fernet.encrypt(json.dumps(data).encode()).decode()
def decrypt_plan(enc): return json.loads(fernet.decrypt(enc.encode()).decode())

BASE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>GRANT SECURE // DIGITAL LEGACY</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
<style>
:root { --bg: #020202; --panel: rgba(10,15,20,0.85); --green: #00ff41; --green-glow: rgba(0,255,65,0.35); --cyan: #00e5ff; --text: #e2e8f0; --muted: #8b949e; --border: #1b222c; --danger: #ff3366; --success: #10b981; --mono: 'Share Tech Mono', monospace; --sans: 'Rajdhani', sans-serif; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--mono); background: var(--bg); color: var(--text); min-height: 100vh; overflow-x: hidden; }
#matrix-canvas { position: fixed; inset: 0; z-index: -2; opacity: 0.25; }
body::after { content: ""; position: fixed; inset: 0; background: linear-gradient(rgba(0,0,0,0) 50%, rgba(0,0,0,0.25) 50%); background-size: 100% 4px; pointer-events: none; z-index: -1; }
nav { background: rgba(2,2,2,0.95); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--green); position: sticky; top: 0; z-index: 50; box-shadow: 0 0 15px rgba(0,255,65,0.2); }
.brand { color: var(--green); font-family: var(--sans); font-size: 1.4rem; font-weight: 700; text-decoration: none; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 10px var(--green-glow); }
nav a:not(.brand) { color: var(--text); text-decoration: none; margin-left: 1.2rem; font-family: var(--sans); font-size: 1rem; font-weight: 700; text-transform: uppercase; transition: 0.3s; }
nav a:not(.brand):hover { color: var(--green); text-shadow: 0 0 8px var(--green-glow); }
.container { max-width: 1000px; margin: 3rem auto 4rem; padding: 0 1.5rem; position: relative; z-index: 10; }
.card { background: var(--panel); padding: 2.5rem; border: 1px solid var(--border); border-left: 3px solid var(--green); margin-bottom: 2rem; backdrop-filter: blur(10px); box-shadow: 0 10px 40px rgba(0,0,0,0.8); }
h1 { color: #ffffff; font-family: var(--sans); font-size: 2.2rem; margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 1.5px; }
h1 span.accent { color: var(--green); text-shadow: 0 0 15px var(--green-glow); }
h2 { color: var(--green); font-family: var(--sans); font-size: 1.25rem; margin: 1.5rem 0 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; text-transform: uppercase; }
p { color: var(--muted); margin-bottom: 1rem; }
.form-group { margin-bottom: 1.4rem; }
label { display: block; margin-bottom: 0.5rem; font-family: var(--sans); font-size: 0.9rem; font-weight: 700; color: var(--cyan); letter-spacing: 1px; text-transform: uppercase; }
input, select { width: 100%; padding: 0.8rem; border: 1px solid var(--border); border-radius: 4px; font-family: var(--mono); font-size: 1rem; background: rgba(0,0,0,0.7); color: var(--green); transition: 0.3s; }
input:focus, select:focus { outline: none; border-color: var(--green); box-shadow: 0 0 15px var(--green-glow); }
button, .btn { display: inline-block; padding: 0.9rem 1.8rem; background: transparent; color: var(--green); border: 1px solid var(--green); border-radius: 4px; font-family: var(--sans); font-weight: 700; font-size: 1.05rem; text-transform: uppercase; cursor: pointer; text-decoration: none; margin-top: 0.5rem; letter-spacing: 1px; transition: 0.3s; text-align: center; }
button:hover, .btn:hover { background: rgba(0,255,65,0.1); box-shadow: 0 0 25px var(--green-glow); color: #fff; }
.btn-green { background: var(--green); color: #000; box-shadow: 0 0 15px var(--green-glow); }
.btn-green:hover { background: #fff; border-color: #fff; box-shadow: 0 0 30px #fff; }
.flash { padding: 1rem; border: 1px solid; margin-bottom: 1.5rem; background: rgba(0,0,0,0.9); font-family: var(--mono); font-weight: bold; display: flex; align-items: center; gap: 10px; }
.flash.success { border-color: var(--success); color: #34d399; }
.flash.error { border-color: var(--danger); color: #f87171; }
.plan-row { display: flex; justify-content: space-between; align-items: center; padding: 1.4rem; background: rgba(0,0,0,0.6); border: 1px solid var(--border); border-radius: 4px; margin-bottom: 1rem; font-family: var(--mono); transition: 0.3s; }
.plan-row:hover { border-color: var(--green); box-shadow: 0 0 15px rgba(0,255,65,0.1); }
.badge { padding: 0.3rem 0.9rem; border-radius: 4px; font-size: 0.8rem; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; font-family: var(--sans); }
.badge-active { border: 1px solid var(--success); color: #34d399; }
.badge-pending_verification { border: 1px solid #f0b429; color: #f0b429; }
.badge-executed { border: 1px solid var(--cyan); color: var(--cyan); }
pre { background: rgba(0,0,0,0.95); color: var(--green); padding: 1.5rem; border-radius: 4px; font-family: var(--mono); font-size: 0.9rem; border: 1px solid var(--border); border-left: 3px solid var(--green); white-space: pre-wrap; line-height: 1.6; }
.muted { color: var(--muted); font-size: 0.85rem; display: block; margin-top: 0.3rem; }
</style></head><body><canvas id="matrix-canvas"></canvas>
<nav><a href="/" class="brand">[ GRANT_SYS ]</a><div>
<a href="/">HOME</a>
{% if current_user.is_authenticated %}<a href="/dashboard">DASHBOARD</a><a href="/create_plan">NEW DIRECTIVE</a><a href="/logout" style="color: var(--danger);">LOGOUT</a>
{% else %}<a href="/signup">SIGN UP</a><a href="/login">LOGIN</a>{% endif %}</div></nav>
<div class="container">{% with messages = get_flashed_messages(with_categories=true) %}{% for category, message in messages %}<div class="flash {{ category }}">> {{ message }}</div>{% endfor %}{% endwith %}
"""

JS = """
<script>
const canvas = document.getElementById('matrix-canvas');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;
const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*()_+{}|:<>?";
const fontSize = 16;
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
</body></html>
"""

@app.route('/')
def index(): return render_template_string(BASE + """
<div class="card" style="text-align:center;padding:4rem 2rem;">
<h1>GRANT SECURE <span class="accent">OS</span></h1>
<p style="font-family:var(--sans);font-size:1.2rem;color:var(--green);">> INITIALIZING PROTOCOL...<br>> DIGITAL LEGACY ENCRYPTION ACTIVE</p>
<p style="max-width:650px;margin:1.5rem auto;color:var(--text);">Ensure your digital footprint is secured and handled exactly according to your directives. Set up an encrypted legacy plan while alive. The system will execute the rest upon verified human confirmation.</p>
{% if not current_user.is_authenticated %}<a href="/signup" class="btn btn-green">[ INITIALIZE ACCOUNT ]</a><a href="/login" class="btn">[ SYSTEM LOGIN ]</a>
{% else %}<a href="/create_plan" class="btn btn-green">[ NEW DIRECTIVE ]</a><a href="/dashboard" class="btn">[ DASHBOARD ]</a>{% endif %}
</div>""" + JS)

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        email, name, pw = request.form['email'].strip().lower(), request.form['name'].strip(), request.form['password']
        if User.query.filter_by(email=email).first(): flash('ERROR: Email already registered.', 'error'); return redirect(url_for('signup'))
        db.session.add(User(email=email, name=name, password_hash=generate_password_hash(pw))); db.session.commit()
        flash('SUCCESS: Account created.', 'success'); return redirect(url_for('login'))
    return render_template_string(BASE + """
<div class="card" style="max-width:450px;margin:0 auto;"><h1>REGISTER</h1>
<form method="POST"><div class="form-group"><label>Full Name</label><input name="name" required></div>
<div class="form-group"><label>Email Address</label><input name="email" type="email" required></div>
<div class="form-group"><label>Password</label><input name="password" type="password" required minlength="6"></div>
<button type="submit" class="btn-green" style="width:100%;">[ INITIALIZE ]</button></form></div>""" + JS)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email'].strip().lower()).first()
        if user and check_password_hash(user.password_hash, request.form['password']): login_user(user); flash('ACCESS GRANTED.', 'success'); return redirect(url_for('dashboard'))
        flash('ACCESS DENIED.', 'error')
    return render_template_string(BASE + """
<div class="card" style="max-width:450px;margin:0 auto;"><h1>SYSTEM LOGIN</h1>
<form method="POST"><div class="form-group"><label>Email Address</label><input name="email" type="email" required></div>
<div class="form-group"><label>Password</label><input name="password" type="password" required></div>
<button type="submit" class="btn-green" style="width:100%;">[ AUTHENTICATE ]</button></form></div>""" + JS)

@app.route('/logout')
@login_required
def logout(): logout_user(); flash('SESSION TERMINATED.', 'success'); return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    plans = LegacyPlan.query.filter_by(user_id=current_user.id).all()
    return render_template_string(BASE + """
<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2rem;flex-wrap:wrap;gap:1rem;"><div><h1>OPS <span class="accent">DASHBOARD</span></h1><p style="font-family:var(--sans);color:var(--green);margin:0;">OPERATOR: {{ current_user.name | upper }}</p></div><a href="/create_plan" class="btn btn-green">[ + NEW DIRECTIVE ]</a></div>
{% if plans %}{% for plan in plans %}
<div class="plan-row" style="flex-direction:column;align-items:flex-start;"><div style="width:100%;display:flex;justify-content:space-between;align-items:center;"><strong style="font-size:1.2rem;color:#fff;">[ DIRECTIVE #{{ plan.id }} ]</strong><span class="badge badge-{{ plan.status }}">{{ plan.status.replace('_',' ') }}</span></div>
<div style="margin-top:1rem;width:100%;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:0.8rem;"><span class="muted">PRIMARY: {{ plan.primary_email }}</span><span class="muted">ESCALATION: {{ plan.secondary_email or 'NONE' }}</span><span class="muted">THRESHOLD: {{ plan.inactivity_days }} DAYS</span><span class="muted">LAST CHECK-IN: {{ plan.last_activity.strftime('%Y-%m-%d %H:%M') }}</span></div></div>
{% endfor %}<div style="margin-top:2rem;"><a href="/run_check" class="btn btn-green" style="width:100%;text-align:center;padding:1rem;">[ RUN INACTIVITY DIAGNOSTIC ]</a></div>
{% else %}<div style="text-align:center;padding:3rem 1rem;background:rgba(0,0,0,0.4);border-radius:4px;border:1px dashed var(--border);"><p style="font-family:var(--mono);color:var(--green);">> NO ACTIVE DIRECTIVES.</p><a href="/create_plan" class="btn btn-green" style="margin-top:1rem;">[ CREATE FIRST DIRECTIVE ]</a></div>{% endif %}</div>""" + JS, plans=plans)

@app.route('/create_plan', methods=['GET','POST'])
@login_required
def create_plan():
    if request.method == 'POST':
        accs = [{"platform":p,"action":a,"filter":f.strip()} for p,a,f in zip(request.form.getlist('platform[]'),request.form.getlist('action[]'),request.form.getlist('filter[]')) if p and a]
        data = {"userName":current_user.name,"accounts":accs,"createdAt":datetime.utcnow().isoformat()}
        db.session.add(LegacyPlan(user_id=current_user.id, encrypted_data=encrypt_plan(data), primary_email=request.form['primary_email'].strip().lower(), secondary_email=request.form.get('secondary_email','').strip().lower() or None, inactivity_days=int(request.form['inactivity_days']), last_activity=datetime.utcnow(), status="active")); db.session.commit()
        flash('DIRECTIVE SAVED & ENCRYPTED.', 'success'); return redirect(url_for('dashboard'))
    return render_template_string(BASE + """
<div class="card"><h1>INITIALIZE <span class="accent">DIRECTIVE</span></h1>
<form method="POST" style="margin-top:2rem;">
<h2>Escalation Path</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:1.5rem;"><div class="form-group" style="margin:0;"><label>Primary Email</label><input name="primary_email" type="email" required></div><div class="form-group" style="margin:0;"><label>Secondary Email</label><input name="secondary_email" type="email"><span class="muted">Used after 7 days of no response.</span></div></div>
<div class="form-group"><label>Inactivity Threshold (Days)</label><input name="inactivity_days" type="number" value="180" required min="1"></div>
<h2>Target Assets</h2>
<div id="accounts"><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;margin-bottom:1rem;"><select name="platform[]"><option>WhatsApp</option><option>Discord</option><option>X</option><option>Threads</option><option>Instagram</option><option>Pinterest</option><option>LinkedIn</option></select><select name="action[]"><option>Delete</option><option>Transfer</option><option>Archive</option></select><input name="filter[]" placeholder="Filter"></div></div>
<button type="button" onclick="addRow()" class="btn" style="margin-bottom:1.5rem;">[ + ADD TARGET ]</button><br>
<button type="submit" class="btn-green" style="width:100%;padding:1rem;">[ SAVE ]</button>
</form></div>
<script>function addRow(){const d=document.getElementById('accounts'),r=document.createElement('div');r.style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;margin-top:0.5rem;";r.innerHTML=`<select name="platform[]"><option>WhatsApp</option><option>Discord</option><option>X</option><option>Threads</option><option>Instagram</option><option>Pinterest</option><option>LinkedIn</option></select><select name="action[]"><option>Delete</option><option>Transfer</option><option>Archive</option></select><input name="filter[]" placeholder="Filter">`;d.appendChild(r);}</script>""" + JS)

@app.route('/run_check')
@login_required
def run_check():
    plans = LegacyPlan.query.filter_by(user_id=current_user.id).all(); res = []
    for p in plans:
        days = (datetime.utcnow()-p.last_activity).days
        if p.status=="active" and days>=p.inactivity_days:
            t = secrets.token_urlsafe(32); p.confirmation_token=t; p.status="pending_verification"; p.contact_attempted="primary"; p.verification_sent_at=datetime.utcnow(); db.session.commit()
            res.append({"id":p.id,"act":"TRIGGERED","contact":p.primary_email,"type":"PRIMARY","token":t})
        elif p.status=="pending_verification":
            d = (datetime.utcnow()-p.verification_sent_at).days if p.verification_sent_at else 0
            if p.contact_attempted=="primary" and d>=7 and p.secondary_email:
                t = secrets.token_urlsafe(32); p.confirmation_token=t; p.contact_attempted="secondary"; p.verification_sent_at=datetime.utcnow(); db.session.commit()
                res.append({"id":p.id,"act":"ESCALATED","contact":p.secondary_email,"type":"SECONDARY","token":t})
            else:
                ct = "Primary" if p.contact_attempted=="primary" else "Secondary"; ce = p.primary_email if p.contact_attempted=="primary" else p.secondary_email
                res.append({"id":p.id,"act":f"AWAITING_{ct.upper()}","contact":ce,"type":ct.upper(),"token":p.confirmation_token})
        elif p.status=="active": res.append({"id":p.id,"act":"ACTIVE","days_left":p.inactivity_days-days})
    return render_template_string(BASE + """
<div class="card"><h1>DIAGNOSTIC</h1>
{% for r in res %}<div class="plan-row" style="flex-direction:column;align-items:flex-start;"><strong style="color:var(--green);">> {{ r.act }}</strong>
{% if r.get('days_left') is not none %}<span class="muted" style="color:var(--cyan);margin-top:0.5rem;">DAYS LEFT: {{ r.days_left }}</span>{% endif %}
{% if r.get('contact') %}<div style="background:rgba(0,255,65,0.05);padding:1rem;width:100%;margin-top:0.8rem;border:1px solid var(--green);"><p style="color:#fff;margin-bottom:0.5rem;">[ {{ r.type }}: {{ r.contact }} ]</p><a href="/verify/{{ r.token }}" class="btn btn-green" style="width:100%;text-align:center;">[ VERIFY & EXECUTE ]</a></div>{% endif %}
</div>{% endfor %}
{% if not res %}<p>> NO ACTIVE PLANS.</p>{% endif %}
<a href="/dashboard" class="btn" style="margin-top:1.5rem;">[ BACK ]</a></div>""" + JS, res=res)

@app.route('/verify/<token>', methods=['GET','POST'])
def verify(token):
    p = LegacyPlan.query.filter_by(confirmation_token=token).first()
    if not p: return "Invalid token", 404
    if p.status in ("confirmed","executed"): return "Already executed", 400
    if request.method == 'POST':
        id_f, dc_f = request.files.get('id_document'), request.files.get('death_certificate')
        if id_f and dc_f:
            p.id_document = secure_filename(id_f.filename); p.death_certificate = secure_filename(dc_f.filename)
            id_f.save(os.path.join(app.config['UPLOAD_FOLDER'], p.id_document)); dc_f.save(os.path.join(app.config['UPLOAD_FOLDER'], p.death_certificate))
            p.verification_status = "docs_uploaded"; db.session.commit()
            flash('DOCUMENTS RECEIVED.', 'success'); return redirect(url_for('execute', token=token))
        flash('ERROR: Both documents required.', 'error')
    return render_template_string(BASE + """
<div class="card" style="max-width:550px;margin:0 auto;"><h1 style="color:#f0b429;">2FA VERIFICATION</h1>
<p style="color:#f0b429;">> UPLOAD ID & DEATH CERTIFICATE.</p>
<form method="POST" enctype="multipart/form-data" style="margin-top:1.5rem;">
<div class="form-group"><label>Your ID (Aadhaar/Passport)</label><input type="file" name="id_document" accept="image/*,.pdf" required style="border:1px dashed var(--green);padding:1rem;"></div>
<div class="form-group"><label>Death Certificate</label><input type="file" name="death_certificate" accept="image/*,.pdf" required style="border:1px dashed var(--green);padding:1rem;"></div>
<button type="submit" class="btn-green" style="width:100%;">[ SUBMIT ]</button></form></div>""" + JS)

@app.route('/execute/<token>')
def execute(token):
    p = LegacyPlan.query.filter_by(confirmation_token=token).first()
    if not p: return "Invalid", 404
    if p.status in ("confirmed","executed"): return "Already executed", 400
    p.status = "executed"; p.verification_status = "approved"; db.session.commit()
    data = decrypt_plan(p.encrypted_data); rc = p.primary_email if p.contact_attempted=='primary' else p.secondary_email
    rep = f"EXECUTION REPORT\nUser: {data.get('userName')}\nContact: {rc}\nStatus: COMPLETE\n\nACTIONS:\n"
    for i, a in enumerate(data.get('accounts', []), 1): rep += f"{i}. {a['platform']} - {a['action']} ({a.get('filter','')})\n"
    return render_template_string(BASE + """
<div class="card"><h1 style="color:var(--cyan);">VERIFIED & EXECUTED</h1><p>Documents validated. Plan executed.</p><pre>{{ report }}</pre></div>""" + JS, report=rep)

with app.app_context(): db.create_all()
if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
