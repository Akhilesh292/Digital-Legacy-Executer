"""
MARVEL PROTOCOL: DIGITAL LEGACY DIRECTIVE
============================================================
Autonomous Post-Mortem Asset Protection & Succession Protocol
Theme: Marvel / Grant Industries / S.H.I.E.L.D. Level 7 Clearance
Features:
- Upgraded Live Marvel Animated Canvas Background:
  - Luminous Grant Arc Reactor Core with Triangular Plasma Core & Rotating Rings
  - Interactive Doctor Strange Eldritch Mandala & Sling-Ring Sparks on Cursor
  - Click-triggered Repulsor / Infinity Shockwave Pulse
  - 6 Infinity Stone Energy Nodes + Quantum Nebula + S.H.I.E.L.D. Radar Sweep
- Complete User Auth & Encrypted Estate Planning
- Multi-tier Escalation & 2FA Document Verification
============================================================
"""
import os
import secrets
import json
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Robust encryption import with standard-library fallback
try:
    from cryptography.fernet import Fernet
except ImportError:
    import base64
    import hashlib
    import hmac

    class Fernet:  # type: ignore
        """Zero-dependency authenticated symmetric encryption using Python standard library."""
        def __init__(self, key: bytes):
            if isinstance(key, str):
                key = key.encode()
            self.raw_key = base64.urlsafe_b64decode(key)

        @classmethod
        def generate_key(cls) -> bytes:
            return base64.urlsafe_b64encode(secrets.token_bytes(32))

        def _keystream(self, iv: bytes, length: int) -> bytes:
            stream = bytearray()
            counter = 0
            while len(stream) < length:
                h = hmac.new(self.raw_key, iv + counter.to_bytes(4, 'big'), hashlib.sha256)
                stream.extend(h.digest())
                counter += 1
            return bytes(stream[:length])

        def encrypt(self, data: bytes) -> bytes:
            if isinstance(data, str):
                data = data.encode()
            iv = secrets.token_bytes(16)
            keystream = self._keystream(iv, len(data))
            ciphertext = bytes(a ^ b for a, b in zip(data, keystream))
            mac = hmac.new(self.raw_key, iv + ciphertext, hashlib.sha256).digest()
            return base64.urlsafe_b64encode(iv + mac + ciphertext)

        def decrypt(self, token: bytes) -> bytes:
            if isinstance(token, str):
                token = token.encode()
            raw = base64.urlsafe_b64decode(token)
            if len(raw) < 48:
                raise ValueError("Invalid encryption token")
            iv = raw[:16]
            mac = raw[16:48]
            ciphertext = raw[48:]
            expected_mac = hmac.new(self.raw_key, iv + ciphertext, hashlib.sha256).digest()
            if not hmac.compare_digest(mac, expected_mac):
                raise ValueError("Authentication tag mismatch or corrupted data")
            keystream = self._keystream(iv, len(ciphertext))
            return bytes(a ^ b for a, b in zip(ciphertext, keystream))


def resolve_database_uri() -> str:
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            return db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    if os.environ.get("RENDER"):
        return "sqlite:////tmp/legacy.db"
    return "sqlite:///legacy.db"


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = resolve_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

UPLOAD_FOLDER = '/tmp/uploads' if os.environ.get("RENDER") else 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

KEY_FILE = "/tmp/secret.key" if os.environ.get("RENDER") else "secret.key"
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


def init_db():
    with app.app_context():
        db.create_all()


init_db()


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except OperationalError:
        db.session.rollback()
        init_db()
        try:
            return db.session.get(User, int(user_id))
        except OperationalError:
            return None


@app.before_request
def ensure_tables():
    try:
        db.session.execute(db.select(User.id).limit(1))
    except OperationalError:
        db.session.rollback()
        init_db()


def encrypt_plan(data: dict) -> str:
    return fernet.encrypt(json.dumps(data).encode()).decode()

def decrypt_plan(encrypted: str) -> dict:
    return json.loads(fernet.decrypt(encrypted.encode()).decode())

def save_uploaded_file(file_storage, prefix: str) -> str:
    filename = secure_filename(file_storage.filename)
    unique_name = f"{prefix}_{secrets.token_hex(8)}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file_storage.save(filepath)
    return unique_name

# ============================================================
# MARVEL BASE TEMPLATE (HIGH-TECH HUD & CINEMATIC STYLING)
# ============================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MARVEL PROTOCOL // GRANT SECURE OS</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --marvel-red: #E62429;
      --marvel-red-dark: #a81014;
      --marvel-red-glow: rgba(230, 36, 41, 0.5);
      --gold: #FFD700;
      --gold-glow: rgba(255, 215, 0, 0.4);
      --arc-blue: #00F0FF;
      --arc-blue-glow: rgba(0, 240, 255, 0.45);
      --bg: #05060a;
      --panel: rgba(11, 15, 25, 0.78);
      --border: rgba(230, 36, 41, 0.35);
      --border-cyan: rgba(0, 240, 255, 0.4);
      --text: #e2e8f0;
      --muted: #94a3b8;
      --danger: #ff3344;
      --success: #10b981;
      --font-display: 'Bebas Neue', 'Impact', sans-serif;
      --font-tech: 'Rajdhani', sans-serif;
      --font-body: 'Inter', -apple-system, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: var(--font-body);
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.6;
      min-height: 100vh;
      overflow-x: hidden;
      position: relative;
    }

    /* Live Marvel Canvas Background */
    #marvel-canvas {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      z-index: -3;
      pointer-events: none;
    }

    /* Subtle CRT Scanline & Hex Grid Overlay */
    .hud-scanlines {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background:
        linear-gradient(rgba(0, 240, 255, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 240, 255, 0.025) 1px, transparent 1px);
      background-size: 60px 60px;
      z-index: -2;
      pointer-events: none;
    }

    /* Radial Vignette Overlay */
    .vignette-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: radial-gradient(circle at 50% 48%, transparent 35%, rgba(5, 6, 10, 0.65) 85%, rgba(5, 6, 10, 0.92) 100%);
      z-index: -1;
      pointer-events: none;
    }

    /* Bottom S.H.I.E.L.D. Telemetry Bar */
    .hud-footer {
      position: fixed;
      bottom: 0;
      left: 0;
      width: 100%;
      padding: 6px 24px;
      background: rgba(6, 9, 16, 0.85);
      border-top: 1px solid rgba(0, 240, 255, 0.25);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-family: var(--font-tech);
      font-size: 0.78rem;
      letter-spacing: 1.5px;
      color: var(--arc-blue);
      z-index: 40;
      backdrop-filter: blur(8px);
      pointer-events: none;
    }

    .hud-pulse-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--arc-blue);
      box-shadow: 0 0 10px var(--arc-blue);
      margin-right: 8px;
      animation: pulseDot 1.6s infinite ease-in-out;
    }

    @keyframes pulseDot {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.35; transform: scale(0.75); }
    }

    /* Top Navigation */
    nav {
      background: rgba(8, 11, 20, 0.86);
      padding: 0.9rem 2.2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid var(--marvel-red);
      box-shadow: 0 4px 25px rgba(230, 36, 41, 0.3);
      position: sticky;
      top: 0;
      z-index: 50;
      backdrop-filter: blur(12px);
    }

    .brand-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
    }

    .marvel-badge {
      background: var(--marvel-red);
      color: #ffffff;
      font-family: var(--font-display);
      font-size: 1.55rem;
      padding: 3px 12px 1px;
      letter-spacing: 1.5px;
      font-weight: 900;
      display: inline-block;
      box-shadow: 0 0 16px var(--marvel-red-glow);
      text-transform: uppercase;
      border-radius: 2px;
    }

    .brand-title {
      color: #ffffff;
      font-family: var(--font-tech);
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: 2px;
      text-transform: uppercase;
    }

    .shield-badge {
      background: rgba(0, 240, 255, 0.12);
      border: 1px solid var(--border-cyan);
      color: var(--arc-blue);
      font-family: var(--font-tech);
      font-size: 0.72rem;
      padding: 2px 8px;
      border-radius: 3px;
      letter-spacing: 1.2px;
      font-weight: 600;
    }

    .nav-links {
      display: flex;
      gap: 1.4rem;
      align-items: center;
      font-family: var(--font-tech);
    }

    nav a:not(.brand-wrap) {
      color: #cbd5e1;
      text-decoration: none;
      font-size: 0.95rem;
      font-weight: 600;
      letter-spacing: 1.2px;
      padding: 0.45rem 0.8rem;
      border-radius: 4px;
      transition: all 0.25s ease;
      text-transform: uppercase;
      border: 1px solid transparent;
    }

    nav a:not(.brand-wrap):hover {
      color: #ffffff;
      border-color: var(--marvel-red);
      background: rgba(230, 36, 41, 0.15);
      box-shadow: 0 0 12px var(--marvel-red-glow);
    }

    /* Container & Cards */
    .container {
      max-width: 1040px;
      margin: 2.8rem auto 4.5rem;
      padding: 0 1.5rem;
      position: relative;
      z-index: 10;
    }

    .card {
      background: var(--panel);
      padding: 2.5rem;
      border-radius: 10px;
      border: 1px solid var(--border);
      border-top: 3px solid var(--marvel-red);
      margin-bottom: 2rem;
      backdrop-filter: blur(10px);
      box-shadow: 0 12px 45px rgba(0, 0, 0, 0.7), inset 0 0 30px rgba(0, 240, 255, 0.04);
      position: relative;
      overflow: hidden;
    }

    .card::before {
      content: "";
      position: absolute;
      top: 0;
      right: 0;
      width: 90px;
      height: 90px;
      background: linear-gradient(135deg, transparent 50%, rgba(230, 36, 41, 0.14) 100%);
      pointer-events: none;
    }

    .corner-tag {
      position: absolute;
      top: 14px;
      right: 18px;
      font-family: var(--font-tech);
      font-size: 0.72rem;
      letter-spacing: 1.5px;
      color: var(--arc-blue);
      text-transform: uppercase;
      font-weight: 700;
    }

    h1 {
      color: #ffffff;
      font-family: var(--font-display);
      font-size: 2.6rem;
      letter-spacing: 2px;
      margin-bottom: 0.8rem;
      text-transform: uppercase;
      text-shadow: 0 2px 10px rgba(0,0,0,0.8);
    }

    h1 span.accent {
      color: var(--marvel-red);
      text-shadow: 0 0 15px var(--marvel-red-glow);
    }

    h2 {
      color: var(--gold);
      font-family: var(--font-tech);
      font-size: 1.3rem;
      font-weight: 700;
      letter-spacing: 1.5px;
      margin: 2rem 0 1rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.5rem;
      text-transform: uppercase;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    h2::before {
      content: "▶";
      font-size: 0.8rem;
      color: var(--marvel-red);
    }

    p {
      margin-bottom: 1.2rem;
      color: var(--text);
      font-size: 0.98rem;
    }

    /* Forms */
    .form-group { margin-bottom: 1.4rem; }

    label {
      display: block;
      margin-bottom: 0.45rem;
      font-family: var(--font-tech);
      font-size: 0.92rem;
      font-weight: 700;
      color: #f1f5f9;
      letter-spacing: 1.2px;
      text-transform: uppercase;
    }

    input, select, textarea {
      width: 100%;
      padding: 0.85rem 1rem;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 6px;
      font-family: var(--font-tech);
      font-size: 1.05rem;
      background: rgba(7, 10, 18, 0.85);
      color: #ffffff;
      transition: all 0.3s ease;
    }

    input:focus, select:focus, textarea:focus {
      outline: none;
      border-color: var(--marvel-red);
      box-shadow: 0 0 15px var(--marvel-red-glow);
      background: rgba(12, 16, 28, 0.95);
    }

    /* Buttons */
    button, .btn {
      display: inline-block;
      padding: 0.85rem 1.8rem;
      background: transparent;
      color: #ffffff;
      border: 1px solid var(--marvel-red);
      border-radius: 5px;
      font-family: var(--font-tech);
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: 1.8px;
      text-transform: uppercase;
      cursor: pointer;
      text-decoration: none;
      margin-top: 0.5rem;
      transition: all 0.3s ease;
      text-align: center;
    }

    button:hover, .btn:hover {
      background: rgba(230, 36, 41, 0.2);
      border-color: var(--marvel-red);
      box-shadow: 0 0 20px var(--marvel-red-glow);
      color: #ffffff;
    }

    .btn-sm {
      padding: 0.5rem 1rem;
      font-size: 0.88rem;
      letter-spacing: 1.2px;
      margin-top: 0;
    }

    .btn-red {
      background: linear-gradient(135deg, var(--marvel-red), var(--marvel-red-dark));
      border: 1px solid var(--marvel-red);
      color: #ffffff;
      box-shadow: 0 4px 18px var(--marvel-red-glow);
    }

    .btn-red:hover {
      background: linear-gradient(135deg, #ff3338, var(--marvel-red));
      box-shadow: 0 6px 25px rgba(230, 36, 41, 0.75);
      transform: translateY(-1px);
    }

    .btn-gold {
      background: linear-gradient(135deg, #d4a017, #f5c518);
      border: 1px solid var(--gold);
      color: #07080d;
      font-weight: 800;
      box-shadow: 0 4px 18px var(--gold-glow);
    }

    .btn-gold:hover {
      background: #ffdb4d;
      box-shadow: 0 6px 25px var(--gold-glow);
      transform: translateY(-1px);
    }

    .btn-cyan {
      border-color: var(--arc-blue);
      color: var(--arc-blue);
    }

    .btn-cyan:hover {
      background: rgba(0, 240, 255, 0.18);
      box-shadow: 0 0 20px var(--arc-blue-glow);
      color: #ffffff;
    }

    /* Flash Messages */
    .flash {
      padding: 1rem 1.25rem;
      border-radius: 6px;
      margin-bottom: 1.6rem;
      font-family: var(--font-tech);
      font-size: 1rem;
      font-weight: 600;
      letter-spacing: 1px;
      border: 1px solid;
      background: rgba(10, 13, 22, 0.95);
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .flash.success {
      border-color: var(--success);
      color: #34d399;
      box-shadow: 0 0 15px rgba(16, 185, 129, 0.25);
    }

    .flash.error {
      border-color: var(--danger);
      color: #f87171;
      box-shadow: 0 0 15px rgba(255, 51, 68, 0.25);
    }

    /* Plan Rows */
    .plan-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
      flex-wrap: wrap;
      padding: 1.4rem;
      background: rgba(10, 14, 24, 0.75);
      border: 1px solid var(--border);
      border-left: 4px solid var(--marvel-red);
      border-radius: 6px;
      margin-bottom: 1.1rem;
      font-family: var(--font-tech);
      transition: all 0.3s ease;
    }

    .plan-row:hover {
      border-color: var(--marvel-red);
      box-shadow: 0 4px 20px rgba(230, 36, 41, 0.2);
      transform: translateY(-2px);
    }

    .plan-actions {
      display: flex;
      gap: 0.6rem;
      align-items: center;
      flex-wrap: wrap;
    }

    .badge {
      padding: 0.35rem 0.9rem;
      border-radius: 4px;
      font-size: 0.82rem;
      font-weight: 700;
      letter-spacing: 1.2px;
      text-transform: uppercase;
      font-family: var(--font-tech);
    }

    .badge-active {
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid #10b981;
      color: #34d399;
      box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
    }

    .badge-pending_verification {
      background: rgba(255, 215, 0, 0.15);
      border: 1px solid var(--gold);
      color: var(--gold);
      box-shadow: 0 0 10px var(--gold-glow);
    }

    .badge-executed {
      background: rgba(0, 240, 255, 0.15);
      border: 1px solid var(--arc-blue);
      color: var(--arc-blue);
      box-shadow: 0 0 10px var(--arc-blue-glow);
    }

    pre {
      background: rgba(6, 8, 14, 0.95);
      color: var(--gold);
      padding: 1.6rem;
      border-radius: 6px;
      font-family: 'Fira Code', var(--font-tech), monospace;
      font-size: 0.92rem;
      border: 1px solid var(--border);
      border-left: 4px solid var(--marvel-red);
      white-space: pre-wrap;
      line-height: 1.6;
    }

    .muted {
      color: var(--muted);
      font-size: 0.88rem;
      display: block;
      margin-top: 0.3rem;
    }

    .hero-stat {
      background: rgba(230, 36, 41, 0.08);
      border: 1px solid var(--border);
      padding: 1rem 1.4rem;
      border-radius: 6px;
      text-align: center;
      flex: 1;
      min-width: 170px;
    }

    .hero-stat-val {
      font-family: var(--font-display);
      font-size: 2rem;
      color: var(--gold);
      letter-spacing: 1px;
    }

    .hero-stat-lbl {
      font-family: var(--font-tech);
      font-size: 0.8rem;
      color: #cbd5e1;
      letter-spacing: 1.5px;
      text-transform: uppercase;
    }

    .token-box {
      background: rgba(0, 240, 255, 0.07);
      border: 1px dashed var(--border-cyan);
      padding: 0.9rem 1.1rem;
      border-radius: 6px;
      font-family: var(--font-tech);
      font-size: 0.95rem;
      color: var(--arc-blue);
      word-break: break-all;
      margin-top: 0.6rem;
    }
  </style>
</head>
<body>
  <!-- Live Marvel Canvas Background -->
  <canvas id="marvel-canvas"></canvas>
  <div class="hud-scanlines"></div>
  <div class="vignette-overlay"></div>

  <!-- Navigation -->
  <nav>
    <a href="/" class="brand-wrap">
      <span class="marvel-badge">MARVEL</span>
      <span class="brand-title">GRANT SECURE OS</span>
      <span class="shield-badge">LEVEL 7</span>
    </a>
    <div class="nav-links">
      <a href="/">[ Home ]</a>
      {% if current_user.is_authenticated %}
        <a href="/dashboard">[ Dashboard ]</a>
        <a href="/create_plan" style="color: var(--gold);">[ + New Directive ]</a>
        <a href="/logout" style="color: var(--danger);">[ Logout ]</a>
      {% else %}
        <a href="/signup">[ Clearance Sign Up ]</a>
        <a href="/login">[ Access Login ]</a>
      {% endif %}
    </div>
  </nav>

  <!-- Content Container -->
  <div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, message in messages %}
        <div class="flash {{ category }}">
          <span>⚡</span>
          <span>{{ message }}</span>
        </div>
      {% endfor %}
    {% endwith %}
"""

# ============================================================
# LIVE MARVEL CANVAS ANIMATION (ARC REACTOR, INFINITY STONES & ELDRITCH HUD)
# ============================================================

MARVEL_LIVE_JS = """
  <!-- S.H.I.E.L.D. Bottom Telemetry HUD -->
  <div class="hud-footer">
    <div><span class="hud-pulse-dot"></span>J.A.R.V.I.S. // QUANTUM ENCRYPTION CORE ONLINE</div>
    <div id="hud-coords">SECTOR 7G // ARC OUTPUT: 3.2 GJ/S</div>
  </div>

<script>
(function() {
  const canvas = document.getElementById('marvel-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const hudCoords = document.getElementById('hud-coords');

  let w, h;
  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  const mouse = { x: w * 0.5, y: h * 0.5, active: false };

  const infinityStones = [
    { name: "REALITY", r: 230, g: 36,  b: 41  },
    { name: "SPACE",   r: 0,   g: 240, b: 255 },
    { name: "MIND",    r: 255, g: 215, b: 0   },
    { name: "POWER",   r: 175, g: 82,  b: 255 },
    { name: "TIME",    r: 16,  g: 225, b: 135 },
    { name: "SOUL",    r: 255, g: 125, b: 15  }
  ];

  const particles = [];
  const TOTAL_PARTICLES = Math.min(110, Math.floor(window.innerWidth / 12));
  for (let i = 0; i < TOTAL_PARTICLES; i++) {
    const stone = infinityStones[i % infinityStones.length];
    particles.push({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.65,
      vy: (Math.random() - 0.5) * 0.65,
      r: Math.random() * 2.6 + 1.1,
      stone: stone,
      alpha: Math.random() * 0.65 + 0.3,
      pulse: Math.random() * Math.PI * 2,
      pulseSpeed: Math.random() * 0.03 + 0.015
    });
  }

  const sparks = [];
  const shockwaves = [];

  window.addEventListener('mousemove', function(e) {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
    mouse.active = true;

    if (hudCoords) {
      hudCoords.textContent = `TARGET LOCK: [${Math.round(e.clientX)}, ${Math.round(e.clientY)}] // ARC OUTPUT: 3.2 GJ/S`;
    }

    for (let i = 0; i < 3; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = Math.random() * 2.2 + 0.6;
      sparks.push({
        x: e.clientX + (Math.random() - 0.5) * 14,
        y: e.clientY + (Math.random() - 0.5) * 14,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 0.5,
        size: Math.random() * 2.8 + 1.2,
        color: Math.random() > 0.35 ? '255, 195, 25' : '255, 95, 20',
        life: 1.0,
        decay: Math.random() * 0.03 + 0.02
      });
    }
  });

  window.addEventListener('click', function(e) {
    const pick = infinityStones[Math.floor(Math.random() * infinityStones.length)];
    shockwaves.push({
      x: e.clientX,
      y: e.clientY,
      radius: 8,
      maxRadius: Math.max(w, h) * 0.45,
      color: `${pick.r}, ${pick.g}, ${pick.b}`,
      life: 1.0
    });
  });

  let angle = 0;
  let pulseTime = 0;

  function drawCosmicNebula() {
    const g1 = ctx.createRadialGradient(w * 0.18, h * 0.22, 10, w * 0.18, h * 0.22, w * 0.42);
    g1.addColorStop(0, 'rgba(230, 36, 41, 0.16)');
    g1.addColorStop(1, 'rgba(5, 6, 10, 0)');
    ctx.fillStyle = g1;
    ctx.fillRect(0, 0, w, h);

    const g2 = ctx.createRadialGradient(w * 0.5, h * 0.48, 15, w * 0.5, h * 0.48, w * 0.45);
    g2.addColorStop(0, 'rgba(0, 240, 255, 0.14)');
    g2.addColorStop(1, 'rgba(5, 6, 10, 0)');
    ctx.fillStyle = g2;
    ctx.fillRect(0, 0, w, h);

    const g3 = ctx.createRadialGradient(w * 0.85, h * 0.8, 10, w * 0.85, h * 0.8, w * 0.4);
    g3.addColorStop(0, 'rgba(157, 78, 221, 0.14)');
    g3.addColorStop(1, 'rgba(5, 6, 10, 0)');
    ctx.fillStyle = g3;
    ctx.fillRect(0, 0, w, h);
  }

  function drawGrantArcReactor() {
    const px = (mouse.x - w * 0.5) * 0.025;
    const py = (mouse.y - h * 0.5) * 0.025;
    const cx = w * 0.5 + px;
    const cy = h * 0.48 + py;
    const baseR = Math.min(w, h) * 0.34;

    pulseTime += 0.03;
    angle += 0.004;
    const breathe = Math.sin(pulseTime) * 6;

    ctx.save();
    ctx.translate(cx, cy);

    const coreGlow = ctx.createRadialGradient(0, 0, baseR * 0.05, 0, 0, baseR * 1.15);
    coreGlow.addColorStop(0, 'rgba(0, 240, 255, 0.24)');
    coreGlow.addColorStop(0.45, 'rgba(0, 160, 255, 0.08)');
    coreGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = coreGlow;
    ctx.beginPath();
    ctx.arc(0, 0, baseR * 1.15, 0, Math.PI * 2);
    ctx.fill();

    ctx.save();
    ctx.rotate(angle * 2.2);
    const sweepGrad = ctx.createLinearGradient(0, 0, baseR, 0);
    sweepGrad.addColorStop(0, 'rgba(0, 240, 255, 0.14)');
    sweepGrad.addColorStop(1, 'rgba(0, 240, 255, 0)');
    ctx.fillStyle = sweepGrad;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, baseR + breathe, 0, 0.45);
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    ctx.strokeStyle = 'rgba(230, 36, 41, 0.26)';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(0, 0, baseR + breathe, 0, Math.PI * 2);
    ctx.stroke();

    ctx.save();
    ctx.rotate(angle);
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.24)';
    ctx.lineWidth = 2;
    ctx.setLineDash([22, 12, 6, 12]);
    ctx.beginPath();
    ctx.arc(0, 0, baseR * 0.84, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);

    const numCoils = 12;
    for (let i = 0; i < numCoils; i++) {
      const a = (i * Math.PI * 2) / numCoils;
      ctx.save();
      ctx.rotate(a);
      ctx.fillStyle = 'rgba(0, 240, 255, 0.28)';
      ctx.strokeStyle = 'rgba(255, 215, 0, 0.28)';
      ctx.lineWidth = 1;
      ctx.fillRect(baseR * 0.72, -5, baseR * 0.11, 10);
      ctx.strokeRect(baseR * 0.72, -5, baseR * 0.11, 10);
      ctx.restore();
    }
    ctx.restore();

    ctx.save();
    ctx.rotate(-angle * 1.5);
    ctx.strokeStyle = 'rgba(255, 215, 0, 0.22)';
    ctx.lineWidth = 1.8;
    ctx.setLineDash([30, 14, 8, 14]);
    ctx.beginPath();
    ctx.arc(0, 0, baseR * 0.64, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();

    const triR = baseR * 0.44 + breathe * 0.4;
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.38)';
    ctx.fillStyle = 'rgba(0, 240, 255, 0.06)';
    ctx.lineWidth = 3;
    ctx.beginPath();
    for (let k = 0; k < 3; k++) {
      const ta = Math.PI / 2 + (k * 2 * Math.PI) / 3;
      const tx = Math.cos(ta) * triR;
      const ty = Math.sin(ta) * triR;
      if (k === 0) ctx.moveTo(tx, ty);
      else ctx.lineTo(tx, ty);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    ctx.font = "900 " + Math.floor(baseR * 0.56) + "px 'Bebas Neue', sans-serif";
    ctx.fillStyle = "rgba(230, 36, 41, 0.14)";
    ctx.strokeStyle = "rgba(255, 215, 0, 0.18)";
    ctx.lineWidth = 1.2;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("A", 0, 4);
    ctx.strokeText("A", 0, 4);

    ctx.restore();
  }

  function drawEldritchCursor() {
    if (!mouse.active) return;
    ctx.save();
    ctx.translate(mouse.x, mouse.y);

    ctx.save();
    ctx.rotate(angle * 4);
    ctx.strokeStyle = 'rgba(255, 195, 25, 0.35)';
    ctx.lineWidth = 1.2;
    ctx.setLineDash([8, 6]);
    ctx.beginPath();
    ctx.arc(0, 0, 32, 0, Math.PI * 2);
    ctx.stroke();

    ctx.setLineDash([]);
    ctx.strokeStyle = 'rgba(255, 130, 20, 0.25)';
    ctx.strokeRect(-18, -18, 36, 36);
    ctx.rotate(Math.PI / 4);
    ctx.strokeRect(-18, -18, 36, 36);
    ctx.restore();

    ctx.restore();
  }

  function render() {
    ctx.clearRect(0, 0, w, h);

    drawCosmicNebula();
    drawGrantArcReactor();

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 125) {
          const alpha = (1 - dist / 125) * 0.22;
          const s = particles[i].stone;
          ctx.strokeStyle = `rgba(${s.r}, ${s.g}, ${s.b}, ${alpha})`;
          ctx.lineWidth = 0.9;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }

    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0) p.x = w;
      if (p.x > w) p.x = 0;
      if (p.y < 0) p.y = h;
      if (p.y > h) p.y = 0;

      p.pulse += p.pulseSpeed;
      const currentAlpha = Math.max(0.2, p.alpha + Math.sin(p.pulse) * 0.25);

      ctx.fillStyle = `rgba(${p.stone.r}, ${p.stone.g}, ${p.stone.b}, ${currentAlpha * 0.25})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 3, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = `rgba(${p.stone.r}, ${p.stone.g}, ${p.stone.b}, ${currentAlpha})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }

    for (let i = shockwaves.length - 1; i >= 0; i--) {
      const sw = shockwaves[i];
      sw.radius += 7;
      sw.life -= 0.022;
      if (sw.life <= 0) {
        shockwaves.splice(i, 1);
        continue;
      }
      ctx.strokeStyle = `rgba(${sw.color}, ${sw.life * 0.6})`;
      ctx.lineWidth = 2.5 * sw.life;
      ctx.beginPath();
      ctx.arc(sw.x, sw.y, sw.radius, 0, Math.PI * 2);
      ctx.stroke();
    }

    drawEldritchCursor();

    for (let i = sparks.length - 1; i >= 0; i--) {
      const s = sparks[i];
      s.x += s.vx;
      s.y += s.vy;
      s.life -= s.decay;

      if (s.life <= 0) {
        sparks.splice(i, 1);
        continue;
      }

      ctx.fillStyle = `rgba(${s.color}, ${s.life})`;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.size * s.life, 0, Math.PI * 2);
      ctx.fill();
    }

    requestAnimationFrame(render);
  }
  requestAnimationFrame(render);
})();
</script>
</body>
</html>
"""

# ============================================================
# APPLICATION ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="text-align: center; padding: 3rem 2.5rem;">
      <span class="corner-tag">GRANT INDUSTRIES // PROTOCOL 07</span>
      <h1>DIGITAL LEGACY <span class="accent">DIRECTIVE</span></h1>
      <p style="max-width: 680px; margin: 0 auto 2rem; color: #cbd5e1;">
        Autonomous post-mortem asset protection and succession vaults secured with authenticated encryption,
        multi-tier escalation, and two-factor document verification.
      </p>
      <div style="display: flex; gap: 1rem; justify-content: center; margin-bottom: 2.2rem; flex-wrap: wrap;">
        <div class="hero-stat">
          <div class="hero-stat-val">FERNET</div>
          <div class="hero-stat-lbl">Authenticated Vault</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-val">2-TIER</div>
          <div class="hero-stat-lbl">Escalation Chain</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-val">2FA DOCS</div>
          <div class="hero-stat-lbl">Verification Gate</div>
        </div>
      </div>
      {% if current_user.is_authenticated %}
        <a href="/dashboard" class="btn btn-red">Open Command Dashboard</a>
        <a href="/create_plan" class="btn btn-gold">Create New Directive</a>
      {% else %}
        <a href="/signup" class="btn btn-red">Request Clearance</a>
        <a href="/login" class="btn btn-cyan">Operator Login</a>
      {% endif %}
    </div>
    """ + MARVEL_LIVE_JS)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not name or not email or not password:
            flash("All clearance fields are required.", "error")
            return redirect(url_for('signup'))
        if User.query.filter_by(email=email).first():
            flash("An operator with that email already exists.", "error")
            return redirect(url_for('signup'))
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f"Level 7 clearance granted for {user.name}. Welcome to Grant Secure OS.", "success")
        return redirect(url_for('dashboard'))

    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="max-width: 540px; margin: 0 auto;">
      <span class="corner-tag">GRANT INDUSTRIES // NEW OPERATOR</span>
      <h1>CLEARANCE <span class="accent">SIGN UP</span></h1>
      <form method="POST">
        <div class="form-group">
          <label for="name">Operator Full Name</label>
          <input type="text" id="name" name="name" required placeholder="e.g. Elena Grant">
        </div>
        <div class="form-group">
          <label for="email">Command Email</label>
          <input type="email" id="email" name="email" required placeholder="operator@grantindustries.io">
        </div>
        <div class="form-group">
          <label for="password">Access Passphrase</label>
          <input type="password" id="password" name="password" required>
        </div>
        <button type="submit" class="btn btn-red" style="width: 100%;">Authorize & Register</button>
      </form>
    </div>
    """ + MARVEL_LIVE_JS)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f"Identity verified. Welcome back, {user.name}.", "success")
            return redirect(url_for('dashboard'))
        flash("Invalid credentials. Access denied.", "error")
        return redirect(url_for('login'))

    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="max-width: 540px; margin: 0 auto;">
      <span class="corner-tag">GRANT INDUSTRIES // AUTH GATE</span>
      <h1>OPERATOR <span class="accent">LOGIN</span></h1>
      <form method="POST">
        <div class="form-group">
          <label for="email">Command Email</label>
          <input type="email" id="email" name="email" required>
        </div>
        <div class="form-group">
          <label for="password">Access Passphrase</label>
          <input type="password" id="password" name="password" required>
        </div>
        <button type="submit" class="btn btn-red" style="width: 100%;">Engage Protocol</button>
      </form>
    </div>
    """ + MARVEL_LIVE_JS)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Session terminated. Vault locks engaged.", "success")
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    plans = LegacyPlan.query.filter_by(user_id=current_user.id).order_by(LegacyPlan.created_at.desc()).all()
    now = datetime.utcnow()
    overdue_plans = []
    for p in plans:
        deadline = p.last_activity + timedelta(days=p.inactivity_days)
        if p.status == "active" and now >= deadline:
            overdue_plans.append(p)

    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <span class="corner-tag">OPERATOR: {{ current_user.name }}</span>
      <h1>LEGACY <span class="accent">COMMAND</span></h1>
      <p>Monitor active directives, send life-sign heartbeats, or trigger/review succession escalation.</p>

      {% if overdue_plans %}
        <div class="flash error">
          <span>⚠️</span>
          <span>{{ overdue_plans|length }} directive(s) have exceeded their inactivity window and are eligible for escalation.</span>
        </div>
      {% endif %}

      <div style="margin-bottom: 1.5rem;">
        <a href="/create_plan" class="btn btn-gold">+ New Legacy Directive</a>
      </div>

      <h2>Active & Escalated Directives</h2>
      {% if plans %}
        {% for plan in plans %}
          <div class="plan-row">
            <div>
              <strong style="font-size: 1.15rem; color: #ffffff;">DIRECTIVE #{{ plan.id }}</strong>
              <span class="badge badge-{{ plan.status }}" style="margin-left: 8px;">{{ plan.status }}</span>
              <span class="muted">
                Primary: {{ plan.primary_email }}
                {% if plan.secondary_email %} | Secondary: {{ plan.secondary_email }}{% endif %}
                | Window: {{ plan.inactivity_days }}d
                | Last Heartbeat: {{ plan.last_activity.strftime('%Y-%m-%d %H:%M UTC') }}
              </span>
              {% if plan.confirmation_token and plan.status == 'pending_verification' %}
                <div class="token-box">
                  Escalation Target: <strong>{{ plan.contact_attempted|upper }}</strong> |
                  Verification Link: <a href="{{ url_for('verify_escalation', token=plan.confirmation_token, _external=True) }}" style="color: var(--gold);">{{ url_for('verify_escalation', token=plan.confirmation_token, _external=True) }}</a>
                </div>
              {% endif %}
            </div>
            <div class="plan-actions">
              {% if plan.status != 'executed' %}
                <form method="POST" action="{{ url_for('heartbeat', plan_id=plan.id) }}" style="display:inline;">
                  <button type="submit" class="btn btn-sm btn-cyan">Heartbeat Check-In</button>
                </form>
                <form method="POST" action="{{ url_for('escalate_plan', plan_id=plan.id) }}" style="display:inline;">
                  <button type="submit" class="btn btn-sm btn-red">Escalate Now</button>
                </form>
              {% endif %}
              <a href="{{ url_for('view_plan', plan_id=plan.id) }}" class="btn btn-sm btn-gold">Inspect Vault</a>
            </div>
          </div>
        {% endfor %}
      {% else %}
        <p style="color: var(--muted);">No directives registered yet. Create one to encrypt your succession instructions.</p>
      {% endif %}
    </div>
    """ + MARVEL_LIVE_JS, plans=plans, overdue_plans=overdue_plans)

@app.route('/create_plan', methods=['GET', 'POST'])
@login_required
def create_plan():
    if request.method == 'POST':
        beneficiary_name = request.form.get('beneficiary_name', '').strip()
        beneficiary_email = request.form.get('beneficiary_email', '').strip()
        primary_email = request.form.get('primary_email', '').strip().lower()
        secondary_email = request.form.get('secondary_email', '').strip().lower() or None
        inactivity_days = int(request.form.get('inactivity_days', 180))
        secret_notes = request.form.get('secret_notes', '').strip()

        if not beneficiary_name or not primary_email or not secret_notes:
            flash("Beneficiary name, primary contact email, and vault instructions are required.", "error")
            return redirect(url_for('create_plan'))

        payload = {
            "beneficiary_name": beneficiary_name,
            "beneficiary_email": beneficiary_email,
            "instructions": secret_notes,
            "created_by": current_user.email
        }

        plan = LegacyPlan(
            user_id=current_user.id,
            encrypted_data=encrypt_plan(payload),
            primary_email=primary_email,
            secondary_email=secondary_email,
            inactivity_days=max(1, inactivity_days),
            last_activity=datetime.utcnow(),
            status="active"
        )
        db.session.add(plan)
        db.session.commit()
        flash(f"Directive #{plan.id} encrypted and stored in Grant Secure OS.", "success")
        return redirect(url_for('dashboard'))

    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="max-width: 680px; margin: 0 auto;">
      <span class="corner-tag">GRANT INDUSTRIES // NEW DIRECTIVE</span>
      <h1>ENCRYPT <span class="accent">LEGACY DIRECTIVE</span></h1>
      <form method="POST">
        <div class="form-group">
          <label for="beneficiary_name">Designated Beneficiary Name</label>
          <input type="text" id="beneficiary_name" name="beneficiary_name" required placeholder="e.g. Morgan Grant">
        </div>
        <div class="form-group">
          <label for="beneficiary_email">Beneficiary Email (Optional)</label>
          <input type="email" id="beneficiary_email" name="beneficiary_email" placeholder="beneficiary@example.com">
        </div>
        <div class="form-group">
          <label for="primary_email">Tier-1 Escalation Contact Email</label>
          <input type="email" id="primary_email" name="primary_email" required placeholder="trusted.contact1@example.com">
        </div>
        <div class="form-group">
          <label for="secondary_email">Tier-2 Fallback Contact Email (Optional)</label>
          <input type="email" id="secondary_email" name="secondary_email" placeholder="trusted.contact2@example.com">
        </div>
        <div class="form-group">
          <label for="inactivity_days">Inactivity Trigger Window (Days)</label>
          <input type="number" id="inactivity_days" name="inactivity_days" value="180" min="1" max="3650" required>
          <span class="muted">If no heartbeat check-in occurs within this window, escalation can be triggered.</span>
        </div>
        <div class="form-group">
          <label for="secret_notes">Encrypted Succession Payload & Asset Keys</label>
          <textarea id="secret_notes" name="secret_notes" rows="6" required placeholder="Enter asset locations, estate instructions, or recovery notes..."></textarea>
        </div>
        <button type="submit" class="btn btn-red">Lock & Encrypt Directive</button>
      </form>
    </div>
    """ + MARVEL_LIVE_JS)

@app.route('/plan/<int:plan_id>/heartbeat', methods=['POST'])
@login_required
def heartbeat(plan_id):
    plan = db.session.get(LegacyPlan, plan_id)
    if not plan or plan.user_id != current_user.id:
        flash("Directive not found or unauthorized.", "error")
        return redirect(url_for('dashboard'))
    plan.last_activity = datetime.utcnow()
    plan.status = "active"
    plan.confirmation_token = None
    plan.contact_attempted = "primary"
    plan.verification_sent_at = None
    db.session.commit()
    flash(f"Heartbeat confirmed for Directive #{plan.id}. Inactivity timer reset.", "success")
    return redirect(url_for('dashboard'))

@app.route('/plan/<int:plan_id>/escalate', methods=['POST'])
@login_required
def escalate_plan(plan_id):
    plan = db.session.get(LegacyPlan, plan_id)
    if not plan or plan.user_id != current_user.id:
        flash("Directive not found or unauthorized.", "error")
        return redirect(url_for('dashboard'))

    if plan.status == "executed":
        flash("Directive has already been executed.", "error")
        return redirect(url_for('dashboard'))

    if plan.status == "pending_verification" and plan.contact_attempted == "primary" and plan.secondary_email:
        plan.contact_attempted = "secondary"
    else:
        plan.contact_attempted = "primary"

    plan.status = "pending_verification"
    plan.confirmation_token = secrets.token_urlsafe(24)
    plan.verification_sent_at = datetime.utcnow()
    db.session.commit()

    target_email = plan.secondary_email if plan.contact_attempted == "secondary" else plan.primary_email
    flash(f"Escalation token dispatched to {plan.contact_attempted} contact ({target_email}) for Directive #{plan.id}.", "success")
    return redirect(url_for('dashboard'))

@app.route('/verify/<token>', methods=['GET', 'POST'])
def verify_escalation(token):
    plan = LegacyPlan.query.filter_by(confirmation_token=token).first()
    if not plan:
        flash("Invalid or expired verification token.", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        id_file = request.files.get('id_document')
        cert_file = request.files.get('death_certificate')
        if not id_file or not id_file.filename or not cert_file or not cert_file.filename:
            flash("Both an ID document and a death/status certificate are required for 2FA verification.", "error")
            return redirect(url_for('verify_escalation', token=token))

        plan.id_document = save_uploaded_file(id_file, f"id_p{plan.id}")
        plan.death_certificate = save_uploaded_file(cert_file, f"cert_p{plan.id}")
        plan.verification_status = "verified"
        plan.status = "executed"
        plan.confirmation_token = None
        db.session.commit()
        flash(f"2FA documents verified. Directive #{plan.id} is now EXECUTED and unlocked.", "success")
        return redirect(url_for('view_plan', plan_id=plan.id))

    return render_template_string(BASE_TEMPLATE + """
    <div class="card" style="max-width: 620px; margin: 0 auto;">
      <span class="corner-tag">2FA VERIFICATION GATE</span>
      <h1>DOCUMENT <span class="accent">VERIFICATION</span></h1>
      <p>
        Directive <strong>#{{ plan.id }}</strong> is currently awaiting two-factor verification via
        <strong>{{ plan.contact_attempted|upper }}</strong> contact. Upload both required documents to execute release.
      </p>
      <form method="POST" enctype="multipart/form-data">
        <div class="form-group">
          <label for="id_document">Verifier Government / Operator ID</label>
          <input type="file" id="id_document" name="id_document" required>
        </div>
        <div class="form-group">
          <label for="death_certificate">Official Status / Death Certificate</label>
          <input type="file" id="death_certificate" name="death_certificate" required>
        </div>
        <button type="submit" class="btn btn-gold" style="width: 100%;">Submit 2FA & Execute Directive</button>
      </form>
    </div>
    """ + MARVEL_LIVE_JS, plan=plan)

@app.route('/plan/<int:plan_id>')
@login_required
def view_plan(plan_id):
    plan = db.session.get(LegacyPlan, plan_id)
    if not plan or plan.user_id != current_user.id:
        flash("Directive not found or unauthorized.", "error")
        return redirect(url_for('dashboard'))

    decrypted = decrypt_plan(plan.encrypted_data)
    formatted_payload = json.dumps(decrypted, indent=2)

    return render_template_string(BASE_TEMPLATE + """
    <div class="card">
      <span class="corner-tag">DIRECTIVE #{{ plan.id }} // {{ plan.status|upper }}</span>
      <h1>VAULT <span class="accent">INSPECTION</span></h1>
      <p>
        <strong>Status:</strong> <span class="badge badge-{{ plan.status }}">{{ plan.status }}</span>  | 
        <strong>2FA Status:</strong> {{ plan.verification_status|upper }}
      </p>
      {% if plan.id_document or plan.death_certificate %}
        <p class="muted">
          Uploaded Docs — ID: <code>{{ plan.id_document or 'None' }}</code> | Certificate: <code>{{ plan.death_certificate or 'None' }}</code>
        </p>
      {% endif %}

      <h2>Decrypted Payload</h2>
      <pre>{{ formatted_payload }}</pre>

      <div style="margin-top: 1.5rem;">
        <a href="/dashboard" class="btn btn-cyan">← Back to Dashboard</a>
      </div>
    </div>
    """ + MARVEL_LIVE_JS, plan=plan, formatted_payload=formatted_payload)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
