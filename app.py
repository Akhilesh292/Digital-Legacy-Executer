"""
MARVEL PROTOCOL: DIGITAL LEGACY DIRECTIVE
============================================================
Autonomous Post-Mortem Asset Protection & Succession Protocol
Theme: Marvel / Stark Industries / S.H.I.E.L.D. Level 7 Clearance
Features:
- Upgraded Live Marvel Animated Canvas Background:
  * Luminous Stark Arc Reactor Core with Triangular Plasma Core & Rotating Rings
  * Interactive Doctor Strange Eldritch Mandala & Sling-Ring Sparks on Cursor
  * Click-triggered Repulsor / Infinity Shockwave Pulse
  * 6 Infinity Stone Energy Nodes + Quantum Nebula + S.H.I.E.L.D. Radar Sweep
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
