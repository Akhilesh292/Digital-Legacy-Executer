import os, secrets, json
from datetime import datetime, timedelta
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
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>S.H.I.E.L.D. SECURE // DIGITAL LEGACY</title>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root { --bg: #080a10; --panel: rgba(14,18,28,0.85); --cyan: #00e5ff; --cyan-glow: rgba(0,229,255,0.35); --gold: #f0b429; --red: #e23636; --text: #e2e8f0; --muted: #8b949e; --border: rgba(255,255,255,0.1); --danger: #ff3366; --success: #10b981; --font-tech: 'Rajdhani', sans-serif; --font-body: 'Inter', sans-serif; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--font-body); background-color: var(--bg); color: var(--text); line-height: 1.6; min-height: 100vh; overflow-x: hidden; }
#cosmic-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -2; pointer-events: none; }
.vignette { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: radial-gradient(circle at 50% 45%, transparent 30%, rgba(8,10,16,0.7) 80%, rgba(8,10,16,0.95) 100%); z-index: -1; pointer-events: none; }
nav { background: rgba(10,14,22,0.9); padding: 0.9rem 2.2rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--cyan); box-shadow: 0 4px 25px rgba(0,229,255,0.15); position: sticky; top: 0; z-index: 50; backdrop-filter: blur(12px); }
.brand-wrap { display: flex; align-items: center; gap: 12px; text-decoration: none; }
.brand-title { color: var(--cyan); font-family: var(--font-tech); font-size: 1.3rem; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; text-shadow: 0 0 10px var(--cyan-glow); }
.nav-links { display: flex; gap: 1.4rem; align-items: center; font-family: var(--font-tech); }
nav a:not(.brand-wrap) { color: #cbd5e1; text-decoration: none; font-size: 0.95rem; font-weight: 600; letter-spacing: 1.2px; padding: 0.45rem 0.8rem; border-radius: 4px; transition: all 0.25s ease; text-transform: uppercase; border: 1px solid transparent; }
nav a:not(.brand-wrap):hover { color: var(--cyan); border-color: var(--cyan); background: rgba(0,229,255,0.1); box-shadow: 0 0 12px var(--cyan-glow); }
.container { max-width: 1040px; margin: 3rem auto 5rem; padding: 0 1.5rem; position: relative; z-index: 10; }
.card { background: var(--panel); padding: 2.5rem; border-radius: 8px; border: 1px solid var(--border); border-left: 4px solid var(--cyan); margin-bottom: 2rem; backdrop-filter: blur(10px); box-shadow: 0 12px 45px rgba(0,0,0,0.7), inset 0 0 30px rgba(0,229,255,0.03); position: relative; }
h1 { color: #ffffff; font-family: var(--font-tech); font-size: 2.2rem; letter-spacing: 1.5px; margin-bottom: 1rem; text-transform: uppercase; }
h1 span.accent { color: var(--cyan); text-shadow: 0 0 15px var(--cyan-glow); }
h2 { color: var(--gold); font-family: var(--font-tech); font-size: 1.25rem; font-weight: 700; letter-spacing: 1.5px; margin: 2rem 0 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; text-transform: uppercase; }
p { margin-bottom: 1.2rem; color: var(--text); font-size: 0.98rem; }
.form-group { margin-bottom: 1.4rem; }
label { display: block; margin-bottom: 0.45rem; font-family: var(--font-tech); font-size: 0.92rem; font-weight: 700; color: var(--cyan); letter-spacing: 1.2px; text-transform: uppercase; }
input, select { width: 100%; padding: 0.85rem 1rem; border: 1px solid var(--border); border-radius: 6px; font-family: var(--font-tech); font-size: 1.05rem; background: rgba(0,0,0,0.6); color: #ffffff; transition: all 0.3s ease; }
input:focus, select:focus { outline: none; border-color: var(--cyan); box-shadow: 0 0 15px var(--cyan-glow); background: rgba(0,0,0,0.85); }
button, .btn { display: inline-block; padding: 0.85rem 1.8rem; background: transparent; color: var(--cyan); border: 1px solid var(--cyan); border-radius: 5px; font-family: var(--font-tech); font-size: 1.05rem; font-weight: 700; letter-spacing: 1.8px; text-transform: uppercase; cursor: pointer; text-decoration: none; margin-top: 0.5rem; transition: all 0.3s ease; text-align: center; }
button:hover, .btn:hover { background: rgba(0,229,255,0.15); box-shadow: 0 0 20px var(--cyan-glow); color: #ffffff; }
.btn-primary { background: var(--cyan); color: #080a10; box-shadow: 0 4px 18px var(--cyan-glow); }
.btn-primary:hover { background: #ffffff; box-shadow: 0 6px 25px rgba(255,255,255,0.4); transform: translateY(-1px); }
.btn-danger { border-color: var(--danger); color: var(--danger); }
.flash { padding: 1rem 1.25rem; border-radius: 6px; margin-bottom: 1.6rem; font-family: var(--font-tech); font-size: 1rem; font-weight: 600; letter-spacing: 1px; border: 1px solid; background: rgba(10,13,22,0.95); display: flex; align-items: center; gap: 10px; }
.flash.success { border-color: var(--success); color: #34d399; box-shadow: 0 0 15px rgba(16,185,129,0.25); }
.flash.error { border-color: var(--danger); color: #f87171; box-shadow: 0 0 15px rgba(255,51,102,0.25); }
.plan-row { display: flex; justify-content: space-between; align-items: center; padding: 1.4rem; background: rgba(10,14,24,0.75); border: 1px solid var(--border); border-left: 4px solid var(--cyan); border-radius: 6px; margin-bottom: 1.1rem; font-family: var(--font-tech); transition: all 0.3s ease; }
.plan-row:hover { border-color: var(--cyan); box-shadow: 0 4px 20px rgba(0,229,255,0.15); transform: translateY(-2px); }
.badge { padding: 0.35rem 0.9rem; border-radius: 4px; font-size: 0.82rem; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; font-family: var(--font-tech); }
.badge-active { background: rgba(16,185,129,0.15); border: 1px solid #10b981; color: #34d399; }
.badge-pending_verification { background: rgba(240,180,41,0.15); border: 1px solid var(--gold); color: var(--gold); }
.badge-executed { background: rgba(0,229,255,0.15); border: 1px solid var(--cyan); color: var(--cyan); }
pre { background: rgba(0,0,0,0.85); color: var(--cyan); padding: 1.6rem; border-radius: 6px; font-family: monospace; font-size: 0.92rem; border: 1px solid var(--border); border-left: 4px solid var(--cyan); white-space: pre-wrap; line-height: 1.6; }
.muted { color: var(--muted); font-size: 0.88rem; display: block; margin-top: 0.3rem; }
</style></head><body><canvas id="cosmic-canvas"></canvas><div class="vignette"></div>
<nav><a href="/" class="brand-wrap"><span class="brand-title">S.H.I.E.L.D. // SECURE OS</span></a><div class="nav-links"><a href="/">[ Home ]</a>
{% if current_user.is_authenticated %}<a href="/dashboard">[ Dashboard ]</a><a href="/create_plan">[ + New Directive ]</a><a href="/logout" style="color: var(--danger);">[ Logout ]</a>
{% else %}<a href="/signup">[ Sign Up ]</a><a href="/login">[ Login ]</a>{% endif %}</div></nav>
<div class="container">{% with messages = get_flashed_messages(with_categories=true) %}{% for category, message in messages %}<div class="flash {{ category }}"><span>⚡</span><span>{{ message }}</span></div>{% endfor %}{% endwith %}
"""

JS = """
<script>
(function() {
  const canvas = document.getElementById('cosmic-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let w, h;
  function resize() { w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; }
  resize(); window.addEventListener('resize', resize);
  const particles = []; const TOTAL = 60;
  const colors = ['rgba(0,229,255,0.4)', 'rgba(240,180,41,0.35)', 'rgba(226,54,54,0.3)'];
  for (let i = 0; i < TOTAL; i++) {
    particles.push({ x: Math.random()*w, y: Math.random()*h, vx: (Math.random()-0.5)*0.25, vy: (Math.random()-0.5)*0.25, r: Math.random()*1.5+0.8, color: colors[Math.floor(Math.random()*colors.length)], alpha: Math.random()*0.5+0.2, pulse: Math.random()*Math.PI*2, pulseSpeed: Math.random()*0.02+0.01 });
  }
  let angle = 0, pulseTime = 0;
  function render() {
    ctx.clearRect(0, 0, w, h);
    pulseTime += 0.015; const breathe = Math.sin(pulseTime)*0.05+1;
    const g = ctx.createRadialGradient(w*0.5, h*0.45, 10, w*0.5, h*0.45, w*0.45);
    g.addColorStop(0, 'rgba(0,229,255,0.06)'); g.addColorStop(0.6, 'rgba(0,229,255,0.02)'); g.addColorStop(1, 'rgba(8,10,16,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    angle += 0.002; const cx = w*0.5, cy = h*0.45, baseR = Math.min(w, h)*0.35*breathe;
    ctx.save(); ctx.translate(cx, cy);
    ctx.strokeStyle = 'rgba(0,229,255,0.05)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(0,0,baseR,0,Math.PI*2); ctx.stroke();
    ctx.rotate(angle); ctx.strokeStyle = 'rgba(240,180,41,0.04)'; ctx.setLineDash([15,20]); ctx.beginPath(); ctx.arc(0,0,baseR*0.8,0,Math.PI*2); ctx.stroke(); ctx.restore();
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = w; if (p.x > w) p.x = 0; if (p.y < 0) p.y = h; if (p.y > h) p.y = 0;
      p.pulse += p.pulseSpeed; const a = Math.max(0.1, p.alpha + Math.sin(p.pulse)*0.15);
      ctx.fillStyle = p.color.replace(/[^,]+(?=\\))/, a); ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI*2); ctx.fill();
    });
    requestAnimationFrame(render);
  }
  requestAnimationFrame(render);
})();
</script>
</body></html>
"""

@app.route('/')
def index(): return render_template_string(BASE + """
<div class="card" style="text-align:center;padding:4rem 2.5rem;"><h1>DIGITAL LEGACY <span class="accent">DIRECTIVE</span></h1>
<p style="font-family:var(--font-tech);font-size:1.2rem;color:var(--cyan);letter-spacing:1.5px;text-transform:uppercase;">// S.H.I.E.L.D. LEVEL 7 ASSET SUCCESSION PROTOCOL</p>
<p style="max-width:720px;margin:1.5rem auto 2rem;color:var(--text);line-height:1.8;">Protect your digital empire with military-grade AES encryption. In the event of confirmed inactive status, your designated emergency contacts receive encrypted directives following strict legal verification.</p>
<div style="display:flex;justify-content:center;gap:1.2rem;flex-wrap:wrap;">
{% if not current_user.is_authenticated %}<a href="/signup" class="btn btn-primary" style="padding:1rem 2.4rem;">[ INITIATE CLEARANCE ]</a><a href="/login" class="btn" style="padding:1rem 2.4rem;">[ AGENT LOGIN ]</a>
{% else %}<a href="/create_plan" class="btn btn-primary" style="padding:1rem 2.4rem;">[ + NEW DIRECTIVE ]</a><a href="/dashboard" class="btn" style="padding:1rem 2.4rem;">[ COMMAND DASHBOARD ]</a>{% endif %}
</div></div>""" + JS)

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        email, name, pw = request.form['email'].strip().lower(), request.form['name'].strip(), request.form['password']
        if User.query.filter_by(email=email).first(): flash('SECURITY ALERT: Agent email already registered.', 'error'); return redirect(url_for('signup'))
        db.session.add(User(email=email, name=name, password_hash=generate_password_hash(pw))); db.session.commit()
        flash('CLEARANCE GRANTED: Agent account initialized.', 'success'); return redirect(url_for('login'))
    return render_template_string(BASE + """
<div class="card" style="max-width:540px;margin:0 auto;"><h1>AGENT <span class="accent">CLEARANCE</span></h1>
<form method="POST" style="margin-top:1.8rem;"><div class="form-group"><label>Agent Name</label><input name="name" required placeholder="e.g., Tony Stark"></div>
<div class="form-group"><label>Secure Comms Email</label><input name="email" type="email" required placeholder="agent@grantindustries.com"></div>
<div class="form-group"><label>Passcode (Min 6 chars)</label><input name="password" type="password" required minlength="6" placeholder="••••••••••••"></div>
<button type="submit" class="btn btn-primary" style="width:100%;padding:1rem;margin-top:1rem;">[ INITIALIZE AGENT CLEARANCE ]</button></form>
<p class="muted" style="margin-top:1.5rem;text-align:center;">Already have active clearance? <a href="/login" style="color:var(--gold);">Login here</a></p></div>""" + JS)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email'].strip().lower()).first()
        if user and check_password_hash(user.password_hash, request.form['password']): login_user(user); flash(f'AUTHENTICATION VERIFIED: Welcome back, Agent {user.name}.', 'success'); return redirect(url_for('dashboard'))
        flash('SECURITY ALERT: Invalid credentials.', 'error')
    return render_template_string(BASE + """
<div class="card" style="max-width:540px;margin:0 auto;"><h1>AGENT <span class="accent">LOGIN</span></h1>
<form method="POST" style="margin-top:1.8rem;"><div class="form-group"><label>Comms Email Address</label><input name="email" type="email" required placeholder="agent@grantindustries.com"></div>
<div class="form-group"><label>Passcode</label><input name="password" type="password" required placeholder="••••••••••••"></div>
<button type="submit" class="btn btn-primary" style="width:100%;padding:1rem;margin-top:1rem;">[ VERIFY & ENTER ]</button></form>
<p class="muted" style="margin-top:1.5rem;text-align:center;">New to the protocol? <a href="/signup" style="color:var(--gold);">Request Clearance</a></p></div>""" + JS)

@app.route('/logout')
@login_required
def logout(): logout_user(); flash('CLEARANCE SUSPENDED: Secure session closed.', 'success'); return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    plans = LegacyPlan.query.filter_by(user_id=current_user.id).all()
    return render_template_string(BASE + """
<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2rem;flex-wrap:wrap;gap:1rem;"><div><h1>COMMAND <span class="accent">DASHBOARD</span></h1><p style="color:var(--cyan);font-family:var(--font-tech);font-size:1.1rem;letter-spacing:1px;margin:0;">ACTIVE AGENT: {{ current_user.name | upper }} // ENCRYPTION ONLINE</p></div><a href="/create_plan" class="btn btn-primary">[ + NEW DIRECTIVE ]</a></div>
{% if plans %}{% for plan in plans %}
<div class="plan-row" style="flex-direction:column;align-items:flex-start;"><div style="width:100%;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;"><strong style="font-size:1.2rem;color:#ffffff;">[ DIRECTIVE #{{ plan.id }} ]</strong><span class="badge badge-{{ plan.status }}">{{ plan.status.replace('_',' ') }}</span></div>
<div style="margin-top:1rem;width:100%;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:0.8rem;"><span class="muted"><strong>PRIMARY:</strong> {{ plan.primary_email }}</span><span class="muted"><strong>ESCALATION:</strong> {{ plan.secondary_email or 'NONE' }}</span><span class="muted"><strong>THRESHOLD:</strong> {{ plan.inactivity_days }} DAYS</span><span class="muted"><strong>LAST CHECK-IN:</strong> {{ plan.last_activity.strftime('%Y-%m-%d %H:%M') }}</span></div></div>
{% endfor %}<div style="margin-top:2rem;"><a href="/run_check" class="btn btn-primary" style="width:100%;text-align:center;padding:1rem;">[ RUN INACTIVITY DIAGNOSTIC ]</a></div>
{% else %}<div style="text-align:center;padding:3rem 1rem;background:rgba(0,0,0,0.4);border-radius:6px;border:1px dashed var(--border);"><p style="font-family:var(--font-tech);font-size:1.2rem;color:var(--cyan);">NO ACTIVE DIRECTIVES DETECTED.</p><a href="/create_plan" class="btn btn-primary" style="margin-top:1rem;">[ CREATE FIRST DIRECTIVE ]</a></div>{% endif %}</div>""" + JS, plans=plans)

@app.route('/create_plan', methods=['GET','POST'])
@login_required
def create_plan():
    if request.method == 'POST':
        accs = [{"platform":p,"action":a,"filter":f.strip()} for p,a,f in zip(request.form.getlist('platform[]'),request.form.getlist('action[]'),request.form.getlist('filter[]')) if p and a]
        data = {"userName":current_user.name,"accounts":accs,"createdAt":datetime.utcnow().isoformat()}
        db.session.add(LegacyPlan(user_id=current_user.id, encrypted_data=encrypt_plan(data), primary_email=request.form['primary_email'].strip().lower(), secondary_email=request.form.get('secondary_email','').strip().lower() or None, inactivity_days=int(request.form['inactivity_days']), last_activity=datetime.utcnow(), status="active")); db.session.commit()
        flash('DIRECTIVE ENCRYPTED & REGISTERED.', 'success'); return redirect(url_for('dashboard'))
    return render_template_string(BASE + """
<div class="card"><h1>INITIALIZE <span class="accent">DIRECTIVE</span></h1>
<form method="POST" style="margin-top:2rem;">
<h2>Contact Escalation Path</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:1.5rem;"><div class="form-group" style="margin:0;"><label>Primary Trusted Contact</label><input name="primary_email" type="email" required placeholder="trusted.primary@example.com"></div><div class="form-group" style="margin:0;"><label>Secondary Escalation Contact</label><input name="secondary_email" type="email" placeholder="trusted.secondary@example.com"><span class="muted">Alerted if primary does not respond in 7 days.</span></div></div>
<div class="form-group"><label>Inactivity Trigger Threshold (Days)</label><input name="inactivity_days" type="number" value="180" required min="1" max="3650"></div>
<h2>Target Digital Assets & Directives</h2>
<div id="accounts"><div class="account-block" style="background:rgba(8,12,22,0.7);padding:1.4rem;border:1px solid var(--border);border-radius:6px;margin-bottom:1rem;"><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.2rem;"><div class="form-group" style="margin:0;"><label>Platform / Service</label><select name="platform[]"><option>WhatsApp</option><option>Discord</option><option>X (Twitter)</option><option>Threads</option><option>Instagram</option><option>Google Drive / Photos</option><option>GitHub / Code Repos</option><option>LinkedIn</option></select></div><div class="form-group" style="margin:0;"><label>Action Directive</label><select name="action[]"><option>Delete Account & Wipe Data</option><option>Transfer to Trusted Contact</option><option>Archive Privately in Secure Vault</option></select></div><div class="form-group" style="margin:0;"><label>Scope / Filter (Optional)</label><input name="filter[]" placeholder="e.g., Specific Folder, Chats, or All"></div></div></div></div>
<button type="button" onclick="addRow()" class="btn" style="margin-bottom:2rem;">+ ADD ANOTHER ASSET DIRECTIVE</button><br>
<button type="submit" class="btn btn-primary" style="width:100%;padding:1.1rem;font-size:1.15rem;">[ ENCRYPT & COMMIT DIRECTIVE TO VAULT ]</button></form></div>
<script>function addRow(){const c=document.getElementById('accounts'),d=document.createElement('div');d.className='account-block';d.style="background:rgba(8,12,22,0.7);padding:1.4rem;border:1px solid var(--border);border-radius:6px;margin-bottom:1rem;";d.innerHTML=`<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.2rem;"><div class="form-group" style="margin:0;"><label>Platform / Service</label><select name="platform[]"><option>WhatsApp</option><option>Discord</option><option>X (Twitter)</option><option>Threads</option><option>Instagram</option><option>Google Drive / Photos</option><option>GitHub / Code Repos</option><option>LinkedIn</option></select></div><div class="form-group" style="margin:0;"><label>Action Directive</label><select name="action[]"><option>Delete Account & Wipe Data</option><option>Transfer to Trusted Contact</option><option>Archive Privately in Secure Vault</option></select></div><div class="form-group" style="margin:0;"><label>Scope / Filter (Optional)</label><input name="filter[]" placeholder="e.g., Specific Folder, Chats, or All"></div></div>`;c.appendChild(d);}</script>""" + JS)

@app.route('/run_check')
@login_required
def run_check():
    plans = LegacyPlan.query.filter_by(user_id=current_user.id).all(); res = []
    for p in plans:
        days = (datetime.utcnow()-p.last_activity).days
        if p.status=="active" and days>=p.inactivity_days:
            t = secrets.token_urlsafe(32); p.confirmation_token=t; p.status="pending_verification"; p.contact_attempted="primary"; p.verification_sent_at=datetime.utcnow(); db.session.commit()
            res.append({"id":p.id,"act":"TRIGGERED // THRESHOLD EXCEEDED","contact":p.primary_email,"type":"Primary Trusted Contact","token":t})
        elif p.status=="pending_verification":
            d = (datetime.utcnow()-p.verification_sent_at).days if p.verification_sent_at else 0
            if p.contact_attempted=="primary" and d>=7 and p.secondary_email:
                t = secrets.token_urlsafe(32); p.confirmation_token=t; p.contact_attempted="secondary"; p.verification_sent_at=datetime.utcnow(); db.session.commit()
                res.append({"id":p.id,"act":"ESCALATED // 7-DAY WINDOW LAPSED","contact":p.secondary_email,"type":"Secondary Escalation Contact","token":t})
            else:
                ct = "Primary" if p.contact_attempted=="primary" else "Secondary"; ce = p.primary_email if p.contact_attempted=="primary" else p.secondary_email
                res.append({"id":p.id,"act":f"AWAITING_{ct.upper()}_VERIFICATION","contact":ce,"type":f"{ct} Contact","token":p.confirmation_token})
        elif p.status=="active": res.append({"id":p.id,"act":"HEARTBEAT NORMAL // ACTIVE","days_left":p.inactivity_days-days})
    return render_template_string(BASE + """
<div class="card"><h1>INACTIVITY <span class="accent">DIAGNOSTIC REPORT</span></h1>
{% for r in res %}<div class="plan-row" style="flex-direction:column;align-items:flex-start;"><div style="width:100%;display:flex;justify-content:space-between;"><strong style="color:#ffffff;font-size:1.15rem;">[ DIRECTIVE #{{ r.id }} ]</strong><span class="badge badge-active">{{ r.act }}</span></div>
{% if r.get('days_left') is not none %}<div style="margin-top:0.8rem;"><span class="muted" style="color:var(--cyan);">DAYS REMAINING UNTIL TRIGGER: {{ r.days_left }} DAYS</span></div>{% endif %}
{% if r.get('contact') %}<div style="background:rgba(226,54,54,0.08);padding:1.2rem;width:100%;margin-top:1rem;border:1px solid var(--border);border-radius:6px;"><p style="color:#ffffff;margin-bottom:0.6rem;"><strong>DISPATCH DESTINATION ({{ r.type }}):</strong> {{ r.contact }}</p><p class="muted" style="margin-bottom:1rem;">A secure one-time verification link has been
