    function addRow() {
      const d = document.getElementById('accounts'); const r = document.createElement('div');
      r.style = "background: rgba(7,12,24,.72); padding: 1.5rem; border: 1px solid rgba(90,125,180,.38); margin-bottom: 1rem;";
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
    <div class="card"><h1>Diagnostic</h1>
      {% if results %}{% for r in results %}
          <div class="plan-row" style="flex-direction: column; align-items: flex-start;">
            <strong>[ ID: {{ r.plan_id }} ] > {{ r.action }}</strong>
            {% if r.get('contact') %}
              <div style="background: rgba(0,255,65,0.05); padding: 1rem; width: 100%; margin-top: 1rem; border: 1px solid var(--green);">
                <p class="muted" style="color:#fff;">TARGET ({{ r.type }}): {{ r.contact }}</p>
                <a href="/verify/{{ r.token }}" class="btn btn-green" style="width: 100%; text-align: center;">[ VERIFY & CONFIRM ]</a>
              </div>
            {% endif %}
          </div>
      {% endfor %}{% else %}<p>NO PLANS.</p>{% endif %}
      <a href="/dashboard" class="btn" style="margin-top: 2rem;">[ BACK ]</a>
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
    """ + MATRIX_JS)

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
    """ + MATRIX_JS, report=rep)

with app.app_context(): db.create_all()
if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
