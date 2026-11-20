import os, secrets, json
from datetime import datetime
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
def load_user(user_id): return User.query.get(int(user_id))

def encrypt_plan(data): return fernet.encrypt(json.dumps(data).encode()).decode()
def decrypt_plan(enc): return json.loads(fernet.decrypt(enc.encode()).decode())

BASE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>GRANT Security</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
<style>
:root { --bg: #05080f; --panel: rgba(10,15,25,0.85); --red: #e23636; --gold: #f0b429; --blue: #00e5ff; --text: #e6edf3; --muted: #8b949e; --border: #1b222c; --danger: #ff003c; --warn: #ffb000; --mono: 'Share Tech Mono', monospace; --sans: 'Rajdhani', sans-serif; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--mono); background: var(--bg); color: var(--text); min-height: 100vh; overflow-x: hidden; }
#canvas-bg { position: fixed; inset: 0; z-index: -1; opacity: 0.4; }
nav { background: rgba(5,8,15,0.95); padding: 1rem 2rem; display: flex; justify-content: space-between; border-bottom: 1px solid var(--red); z-index: 50; box-shadow: 0 0 15px rgba(226,54,54,0.2); }
.brand { color: var(--red); font-family: var(--sans); font-size: 1.6rem; font-weight: 700; text-decoration: none; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 10px rgba(226,54,54,0.5); }
nav a { color: var(--text); text-decoration: none; margin-left: 1.5rem; font-family: var(--sans); font-size: 1.1rem; transition: 0.3s; }
nav a:hover { color: var(--gold); text-shadow: 0 0 8px var(--gold); }
.container { max-width: 900px; margin: 3rem auto; padding: 0 1rem; position: relative; z-index: 10; }
.card { background: var(--panel); padding: 2.5rem; border: 1px solid var(--border); border-top: 3px solid var(--red); margin-bottom: 2rem; box-shadow: 0 10px 30px rgba(0,0,0,0.8); backdrop-filter: blur(10px); }
h1 { color: var(--gold); font-family: var(--sans); font-size: 2.2rem; margin-bottom: 1.5rem; text-transform: uppercase; letter-spacing: 2px; border-bottom: 1px solid var(--border); padding-bottom: 1rem; text-shadow: 0 0 10px rgba(240,180,41,0.3); }
h2 { color: var(--red); font-family: var(--sans); font-size: 1.4rem; margin: 1.5rem 0 1rem; text-transform: uppercase; }
p { color: var(--muted); margin-bottom: 1rem; }
label { display: block; color: var(--blue); margin-bottom: 0.5rem; font-size: 0.9rem; font-family: var(--sans); font-weight: 700; text-transform: uppercase; }
input, select { width: 100%; padding: 0.8rem; border: 1px solid var(--border); background: #000; color: var(--text); font-family: var(--mono); margin-bottom: 1.2rem; font-size: 1rem; }
input:focus, select:focus { outline: none; border-color: var(--blue); box-shadow: 0 0 10px rgba(0,229,255,0.3); }
button, .btn { display: inline-block; padding: 0.9rem 1.8rem; background: transparent; color: var(--red); border: 1px solid var(--red); font-family: var(--sans); font-weight: 700; font-size: 1.1rem; text-transform: uppercase; cursor: pointer; text-decoration: none; transition: 0.3s; margin-top: 0.5rem; letter-spacing: 1px; }
button:hover, .btn:hover { background: rgba(226,54,54,0.1); box-shadow: 0 0 20px rgba(226,54,54,0.4); color: #fff; }
.btn-green { background: var(--red); color: #fff; }
.btn-green:hover { background: #ff4a4a; box-shadow: 0 0 25px #ff4a4a; }
.flash { padding: 1rem; border: 1px solid; margin-bottom: 1.5rem; background: #000; font-weight: bold; }
.flash.success { border-color: var(--blue); color: var(--blue); box-shadow: 0 0 15px rgba(0,229,255,0.2); }
.flash.error { border-color: var(--danger); color: var(--danger); box-shadow: 0 0 15px rgba(255,0,60,0.2); }
.row { display: flex; justify-content: space-between; padding: 1.2rem; border: 1px solid var(--border); margin-bottom: 1rem; background: #000; transition: 0.3s; }
.row:hover { border-color: var(--gold); box-shadow: 0 0 15px rgba(240,180,41,0.1); }
.badge { padding: 0.3rem 0.8rem; border: 1px solid var(--blue); color: var(--blue); font-size: 0.8rem; text-transform: uppercase; font-weight: bold; }
pre { background: #000; color: var(--blue); padding: 1.5rem; border: 1px solid var(--border); border-left: 3px solid var(--blue); white-space: pre-wrap; font-size: 0.9rem; }
.muted { color: var(--muted); font-size: 0.85rem; display: block; margin-top: 0.4rem; }
</style></head><body><canvas id="canvas-bg"></canvas>
<nav><a href="/" class="brand">GRANT // SECURE</a><div>
<a href="/">HOME</a>
{% if current_user.is_authenticated %}<a href="/dashboard">DASHBOARD</a><a href="/create_plan">NEW PLAN</a><a href="/logout" style="color: var(--danger);">LOGOUT</a>
{% else %}<a href="/signup">SIGN UP</a><a href="/login">LOGIN</a>{% endif %}</div></nav>
<div class="container">{% with messages = get_flashed_messages(with_categories=true) %}{% for category, message in messages %}<div class="flash {{ category }}">> {{ message }}</div>{% endfor %}{% endwith %}
"""

JS = """
<script>
const canvas = document.getElementById('canvas-bg');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

let particles = [];
for (let i = 0; i < 100; i++) {
    particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        size: Math.random() * 2 + 1,
        speedX: Math.random() * 0.5 - 0.25,
        speedY: Math.random() * 0.5 - 0.25,
        color: Math.random() > 0.5 ? 'rgba(226,54,54,0.6)' : 'rgba(240,180,41,0.4)'
    });
}

let time = 0;

function animate() {
    ctx.fillStyle = 'rgba(5, 8, 15, 0.2)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw Arc Reactor Glow
    time += 0.02;
    const pulse = Math.sin(time) * 0.5 + 0.5;
    const gradient = ctx.createRadialGradient(canvas.width/2, canvas.height/2, 0, canvas.width/2, canvas.height/2, 400 + pulse * 100);
    gradient.addColorStop(0, 'rgba(0, 229, 255, 0.08)');
    gradient.addColorStop(0.5, 'rgba(0, 229, 255, 0.02)');
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw Particles
    particles.forEach(p => {
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
        
        p.x += p.speedX;
        p.y += p.speedY;
        
        if (p.x < 0 || p.x > canvas.width) p.speedX *= -1;
        if (p.y < 0 || p.y > canvas.height) p.speedY *= -1;
    });
    
    requestAnimationFrame(animate);
}
animate();

window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
});
</script>
"""

@app.route('/')
def index(): return render_template_string(BASE + """
<div class="card" style="text-align:center;padding:4rem 2rem;">
<h1 style="border:none;font-size:3rem;">GRANT SECURITY</h1>
<p style="font-family:var(--sans);font-size:1.2rem;color:var(--blue);">PROTOCOL INITIATED // ENCRYPTION ACTIVE</p>
<p style="max-width:600px;margin:1.5rem auto;font-size:1.1rem;">Ensure your digital footprint is secured and handled exactly according to your directives. Set up an encrypted legacy plan while alive.</p>
{% if not current_user.is_authenticated %}<a href="/signup" class="btn btn-green">[ CREATE ACCOUNT ]</a><a href="/login" class="btn">[ LOGIN ]</a>
{% else %}<a href="/create_plan" class="btn btn-green">[ NEW PLAN ]</a><a href="/dashboard" class="btn">[ DASHBOARD ]</a>{% endif %}
</div>""" + JS)

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        email, name, pw = request.form['email'].strip().lower(), request.form['name'].strip(), request.form['password']
        if User.query.filter_by(email=email).first(): flash('ERROR: Email already registered.', 'error'); return redirect(url_for('signup'))
        db.session.add(User(email=email, name=name, password_hash=generate_password_hash(pw))); db.session.commit()
        flash('SUCCESS: Account created.', 'success'); return redirect(url_for('login'))
    return render_template_string(BASE + """
<div class="card" style="max-width:450px;margin:0 auto;"><h1>Register</h1>
<form method="POST"><label>Full Name</label><input name="name" required><label>Email</label><input name="email" type="email" required><label>Password</label><input name="password" type="password" required minlength="6"><button type="submit" class="btn-green" style="width:100%;">[ INITIALIZE ]</button></form>
</div>""" + JS)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email'].strip().lower()).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user); flash('ACCESS GRANTED.', 'success'); return redirect(url_for('dashboard'))
        flash('ACCESS DENIED.', 'error')
    return render_template_string(BASE + """
<div class="card" style="max-width:450px;margin:0 auto;"><h1>System Login</h1>
<form method="POST"><label>Email</label><input name="email" type="email" required><label>Password</label><input name="password" type="password" required><button type="submit" class="btn-green" style="width:100%;">[ AUTHENTICATE ]</button></form>
</div>""" + JS)

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    plans = LegacyPlan.query.filter_by(user_id=current_user.id).all()
    return render_template_string(BASE + """
<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;"><h1 style="margin:0;border:none;">Ops Dashboard</h1><a href="/create_plan" class="btn btn-green">[ + NEW PLAN ]</a></div>
{% if plans %}{% for plan in plans %}
<div class="row" style="flex-direction:column;align-items:flex-start;"><div style="width:100%;display:flex;justify-content:space-between;"><strong style="color:var(--gold);font-family:var(--sans);font-size:1.2rem;">[ PLAN_ID: {{ plan.id }} ]</strong><span class="badge">{{ plan.status.replace('_',' ') }}</span></div>
<div style="margin-top:0.8rem;"><span class="muted">PRIMARY: {{ plan.primary_email }}</span><span class="muted">SECONDARY: {{ plan.secondary_email or 'NONE' }}</span><span class="muted">THRESHOLD: {{ plan.inactivity_days }} DAYS</span></div></div>
{% endfor %}<div style="margin-top:1.5rem;"><a href="/run_check" class="btn" style="width:100%;text-align:center;border-color:var(--warn);color:var(--warn);">[ RUN DIAGNOSTIC ]</a></div>
{% else %}<p>> NO ACTIVE PROTOCOLS.</p>{% endif %}</div>""" + JS, plans=plans)

@app.route('/create_plan', methods=['GET','POST'])
@login_required
def create_plan():
    if request.method == 'POST':
        accs = [{"platform":p,"action":a,"filter":f.strip()} for p,a,f in zip(request.form.getlist('platform[]'),request.form.getlist('action[]'),request.form.getlist('filter[]')) if p and a]
        data = {"userName":current_user.name,"accounts":accs,"createdAt":datetime.utcnow().isoformat()}
        db.session.add(LegacyPlan(user_id=current_user.id, encrypted_data=encrypt_plan(data), primary_email=request.form['primary_email'].strip().lower(), secondary_email=request.form.get('secondary_email','').strip().lower() or None, inactivity_days=int(request.form['inactivity_days']), last_activity=datetime.utcnow(), status="active")); db.session.commit()
        flash('PROTOCOL SAVED.', 'success'); return redirect(url_for('dashboard'))
    return render_template_string(BASE + """
<div class="card"><h1>Initialize Protocol</h1>
<form method="POST">
<h2>Escalation Path</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;"><div><label>Primary Email</label><input name="primary_email" type="email" required></div><div><label>Secondary Email</label><input name="secondary_email" type="email"></div></div>
<label>Threshold (Days)</label><input name="inactivity_days" type="number" value="180" required>
<h2>Targets</h2>
<div id="acc"><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;"><select name="platform[]"><option>WhatsApp</option><option>Discord</option><option>X</option><option>Threads</option><option>Instagram</option><option>Pinterest</option><option>LinkedIn</option></select><select name="action[]"><option>Delete</option><option>Transfer</option><option>Archive</option></select><input name="filter[]" placeholder="Filter"></div></div>
<button type="button" onclick="addRow()" class="btn" style="margin-bottom:1.5rem;">[ + ADD TARGET ]</button><br>
<button type="submit" class="btn-green" style="width:100%;">[ SAVE ]</button>
</form></div>
<script>function addRow(){const d=document.getElementById('acc'),r=document.createElement('div');r.style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.5rem;margin-top:0.5rem;";r.innerHTML=`<select name="platform[]"><option>WhatsApp</option><option>Discord</option><option>X</option><option>Threads</option><option>Instagram</option><option>Pinterest</option><option>LinkedIn</option></select><select name="action[]"><option>Delete</option><option>Transfer</option><option>Archive</option></select><input name="filter[]" placeholder="Filter">`;d.appendChild(r);}</script>
""" + JS)

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
            d = (datetime.utcnow()-p.verification_sent_at).days
            if p.contact_attempted=="primary" and d>=7 and p.secondary_email:
                t = secrets.token_urlsafe(32); p.confirmation_token=t; p.contact_attempted="secondary"; p.verification_sent_at=datetime.utcnow(); db.session.commit()
                res.append({"id":p.id,"act":"ESCALATED","contact":p.secondary_email,"type":"SECONDARY","token":t})
            else:
                ce = p.primary_email if p.contact_attempted=="primary" else p.secondary_email; res.append({"id":p.id,"act":f"AWAITING_{p.contact_attempted.upper()}","contact":ce,"type":p.contact_attempted.upper(),"token":p.confirmation_token})
    return render_template_string(BASE + """
<div class="card"><h1>System Diagnostic</h1>
{% for r in res %}<div class="row" style="flex-direction:column;align-items:flex-start;"><strong style="color:var(--warn);font-family:var(--sans);">> {{ r.act }}</strong>
{% if r.contact %}<div style="background:rgba(226,54,54,0.05);padding:1.5rem;width:100%;margin-top:0.8rem;border:1px solid var(--red);"><p style="color:#fff;margin:0 0 0.8rem 0;">[ {{ r.type }}: {{ r.contact }} ]</p><a href="/verify/{{ r.token }}" class="btn btn-green" style="width:100%;text-align:center;">[ VERIFY & EXECUTE ]</a></div>{% endif %}
</div>{% endfor %}
{% if not res %}<p>> NO ACTIVE PLANS.</p>{% endif %}
<a href="/dashboard" class="btn" style="margin-top:1.5rem;">[ BACK ]</a></div>""" + JS, res=res)

@app.route('/verify/<token>', methods=['GET','POST'])
def verify(token):
    p = LegacyPlan.query.filter_by(confirmation_token=token).first()
    if not p: return "Invalid", 404
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
<div class="card" style="max-width:550px;margin:0 auto;"><h1 style="color:var(--warn);">2FA Verification</h1>
<p style="color:var(--warn);">> UPLOAD ID & DEATH CERTIFICATE.</p>
<form method="POST" enctype="multipart/form-data" style="margin-top:1.5rem;">
<label>Your ID (Aadhaar/Passport)</label><input type="file" name="id_document" accept="image/*,.pdf" required style="border:1px dashed var(--blue);padding:1rem;margin-bottom:1rem;">
<label>Death Certificate</label><input type="file" name="death_certificate" accept="image/*,.pdf" required style="border:1px dashed var(--blue);padding:1rem;margin-bottom:1rem;">
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
<div class="card"><h1 style="color:var(--blue);">Verified & Executed</h1><p>Documents validated. Plan executed.</p><pre>{{ report }}</pre></div>""" + JS, report=rep)

with app.app_context(): db.create_all()
if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
