                "primary_email": "VARCHAR(150)",
                "secondary_email": "VARCHAR(150)",
                "contact_attempted": "VARCHAR(20) DEFAULT 'primary'",
                "verification_sent_at": "DATETIME",
                "id_document": "VARCHAR(200)",
                "death_certificate": "VARCHAR(200)",
                "verification_status": "VARCHAR(50) DEFAULT 'pending'"
            }
            for _c, _ctype in _cols_to_add.items():
                if _c not in _cols:
                    _conn.execute(text(f"ALTER TABLE legacy_plan ADD COLUMN {_c} {_ctype}"))
            _conn.commit()
    except Exception as _e:
        print(f"[Notice] DB schema check: {_e}")
if __name__ == "__main__":
    import socket
    def is_port_available(p):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', p))
                return True
        except OSError:
            return False
    if os.environ.get("PORT"):
        port = int(os.environ.get("PORT"))
    elif is_port_available(5000):
        port = 5000
    elif is_port_available(5001):
        port = 5001
        print("\n[Notice] Port 5000 is occupied (e.g. by macOS AirPlay Receiver). Switched to port 5001.")
    else:
        port = 8080
    print("\n=======================================================")
    print("  MARVEL PROTOCOL // STARK SECURE OS IS LIVE!")
    print(f"  👉 http://127.0.0.1:{port} (or http://localhost:{port})")
    print("=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
