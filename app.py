"""
MARVEL PROTOCOL: DIGITAL LEGACY DIRECTIVE
============================================================
Autonomous Post-Mortem Asset Protection & Succession Protocol
Theme: Marvel / Stark Industries / S.H.I.E.L.D. Level 7 Clearance
Features:
- Upgraded Live Marvel Animated Canvas Background:
  - Luminous Stark Arc Reactor Core with Triangular Plasma Core & Rotating Rings
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

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def encrypt_plan(data: dict) -> str:
    return fernet.encrypt(json.dumps(data).encode()).decode()

def decrypt_plan(encrypted: str) -> dict:
    return json.loads(fernet.decrypt(encrypted.encode()).decode())

# ============================================================
# MARVEL BASE TEMPLATE (HIGH-TECH HUD & CINEMATIC STYLING)
# ============================================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MARVEL PROTOCOL // STARK SECURE OS</title>
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

    input, select {
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

    input:focus, select:focus {
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
      <span class="brand-title">STARK SECURE OS</span>
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

  // Mouse state for Eldritch Mandala & Parallax
  const mouse = { x: w * 0.5, y: h * 0.5, active: false };

  // Infinity Stone Palette (Space, Reality, Power, Mind, Time, Soul)
  const infinityStones = [
    { name: "REALITY", r: 230, g: 36,  b: 41  }, // Red
    { name: "SPACE",   r: 0,   g: 240, b: 255 }, // Blue
    { name: "MIND",    r: 255, g: 215, b: 0   }, // Yellow
    { name: "POWER",   r: 175, g: 82,  b: 255 }, // Purple
    { name: "TIME",    r: 16,  g: 225, b: 135 }, // Green
    { name: "SOUL",    r: 255, g: 125, b: 15  }  // Orange
  ];

  // 1. Cosmic Infinity Energy Particles
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

  // 2. Doctor Strange Eldritch Sparks & Click Shockwaves
  const sparks = [];
  const shockwaves = [];

  window.addEventListener('mousemove', function(e) {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
    mouse.active = true;

    if (hudCoords) {
      hudCoords.textContent = `TARGET LOCK: [${Math.round(e.clientX)}, ${Math.round(e.clientY)}] // ARC OUTPUT: 3.2 GJ/S`;
    }

    // Spawn Eldritch Sling-Ring Sparks
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

  // Repulsor / Infinity Pulse on Click
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

  // Draw Cosmic Nebula Glows
  function drawCosmicNebula() {
    // Red Reality Nebula (Top-Left)
    const g1 = ctx.createRadialGradient(w * 0.18, h * 0.22, 10, w * 0.18, h * 0.22, w * 0.42);
    g1.addColorStop(0, 'rgba(230, 36, 41, 0.16)');
    g1.addColorStop(1, 'rgba(5, 6, 10, 0)');
    ctx.fillStyle = g1;
    ctx.fillRect(0, 0, w, h);

    // Space Tesseract Cyan Glow (Center)
    const g2 = ctx.createRadialGradient(w * 0.5, h * 0.48, 15, w * 0.5, h * 0.48, w * 0.45);
    g2.addColorStop(0, 'rgba(0, 240, 255, 0.14)');
    g2.addColorStop(1, 'rgba(5, 6, 10, 0)');
    ctx.fillStyle = g2;
    ctx.fillRect(0, 0, w, h);

    // Power Stone Purple Nebula (Bottom-Right)
    const g3 = ctx.createRadialGradient(w * 0.85, h * 0.8, 10, w * 0.85, h * 0.8, w * 0.4);
    g3.addColorStop(0, 'rgba(157, 78, 221, 0.14)');
    g3.addColorStop(1, 'rgba(5, 6, 10, 0)');
    ctx.fillStyle = g3;
    ctx.fillRect(0, 0, w, h);
  }

  // Draw Luminous Stark Arc Reactor Core & Avengers Emblem
  function drawStarkArcReactor() {
    // Subtle parallax shift toward cursor
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

    // 1. Core Plasma Backlight
    const coreGlow = ctx.createRadialGradient(0, 0, baseR * 0.05, 0, 0, baseR * 1.15);
    coreGlow.addColorStop(0, 'rgba(0, 240, 255, 0.24)');
    coreGlow.addColorStop(0.45, 'rgba(0, 160, 255, 0.08)');
    coreGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = coreGlow;
    ctx.beginPath();
    ctx.arc(0, 0, baseR * 1.15, 0, Math.PI * 2);
    ctx.fill();

    // 2. S.H.I.E.L.D. Rotating Radar Sweep
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

    // 3. Outer Marvel Red Armor Ring
    ctx.strokeStyle = 'rgba(230, 36, 41, 0.26)';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(0, 0, baseR + breathe, 0, Math.PI * 2);
    ctx.stroke();

    // 4. Segmented Cyan Arc Reactor Ring + 12 Copper/Plasma Coils
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

    // 5. Counter-Rotating Gold Vibranium Ring
    ctx.save();
    ctx.rotate(-angle * 1.5);
    ctx.strokeStyle = 'rgba(255, 215, 0, 0.22)';
    ctx.lineWidth = 1.8;
    ctx.setLineDash([30, 14, 8, 14]);
    ctx.beginPath();
    ctx.arc(0, 0, baseR * 0.64, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();

    // 6. Mark VI Triangular Plasma Core
    const triR = baseR * 0.44 + breathe * 0.4;
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.38)';
    ctx.fillStyle = 'rgba(0, 240, 255, 0.06)';
    ctx.lineWidth = 3;
    ctx.beginPath();
    for (let k = 0; k < 3; k++) {
      // Inverted triangle like Iron Man's chest reactor
      const ta = Math.PI / 2 + (k * 2 * Math.PI) / 3;
      const tx = Math.cos(ta) * triR;
      const ty = Math.sin(ta) * triR;
      if (k === 0) ctx.moveTo(tx, ty);
      else ctx.lineTo(tx, ty);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // 7. Central Avengers 'A' Hologram Emblem
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

  // Draw Doctor Strange Rotating Eldritch Mandala around Cursor
  function drawEldritchCursor() {
    if (!mouse.active) return;
    ctx.save();
    ctx.translate(mouse.x, mouse.y);

    // Outer rotating rune circle
    ctx.save();
    ctx.rotate(angle * 4);
    ctx.strokeStyle = 'rgba(255, 195, 25, 0.35)';
    ctx.lineWidth = 1.2;
    ctx.setLineDash([8, 6]);
    ctx.beginPath();
    ctx.arc(0, 0, 32, 0, Math.PI * 2);
    ctx.stroke();

    // Intersecting Mystic Squares
    ctx.setLineDash([]);
    ctx.strokeStyle = 'rgba(255, 130, 20, 0.25)';
    ctx.strokeRect(-18, -18, 36, 36);
    ctx.rotate(Math.PI / 4);
    ctx.strokeRect(-18, -18, 36, 36);
    ctx.restore();

    ctx.restore();
  }

  // Main 60FPS Render Loop
  function render() {
    ctx.clearRect(0, 0, w, h);

    // Layer 1: Cosmic Nebula
    drawCosmicNebula();

    // Layer 2: Stark Arc Reactor & Avengers Hologram
    drawStarkArcReactor();

    // Layer 3: Quantum Energy Filaments between Infinity Particles
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

    // Layer 4: Glowing Infinity Stone Particles
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

      // Outer stone aura
      ctx.fillStyle = `rgba(${p.stone.r}, ${p.stone.g}, ${p.stone.b}, ${currentAlpha * 0.25})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 3, 0, Math.PI * 2);
      ctx.fill();

      // Bright stone core
      ctx.fillStyle = `rgba(${p.stone.r}, ${p.stone.g}, ${p.stone.b}, ${currentAlpha})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }

    // Layer 5: Click Shockwaves
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

    // Layer 6: Doctor Strange Eldritch Mandala & Sparks
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
      <span class="corner-tag">STARK INDUSTRIES // PROTOCOL 07</span>
      <h1>DIGITAL LEGACY <span class="accent">DIRECTIVE</span></h1>
      <p style="max-width: 680px; margin: 0 auto 2rem; color: #cbd5e1;">
        Autonomous post-mortem asset protection and succession vaults secured with 256-bit encryption,
        multi-tier escalation, and two-factor document verification.
      </p>
      <div style="display: flex; gap: 1rem; justify-content: center; margin-bottom: 2.2rem; flex-wrap: wrap;">
        <div class="hero-stat">
          <div class="hero-stat-val">256-BIT</div>
          <div class="hero-stat-lbl">Quantum Vault</div>
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
