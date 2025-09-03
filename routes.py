from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, UserConfig, Job
import services
import json
import pandas as pd

bp = Blueprint('main', __name__)

@bp.route('/')
def dashboard():
    # This route is unchanged
    jobs = Job.query.order_by(Job.date_added.desc()).all()
    analytics_data = {}
    if jobs:
        df = pd.DataFrame([{"status": j.status, "date": j.date_added} for j in jobs])
        analytics_data['status_counts'] = df['status'].value_counts().to_dict()
        df['date'] = pd.to_datetime(df['date'])
        weekly_counts = df.set_index('date').resample('W-MON').size()
        analytics_data['weekly_counts'] = {date.strftime('%Y-%m-%d'): count for date, count in weekly_counts.items()}
    return render_template('dashboard.html', jobs=jobs, analytics_data=analytics_data)


@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    config = UserConfig.query.first()
    if not config:
        config = UserConfig(id=1)

    if request.method == 'POST':
        # --- KEY CHANGE: More secure update logic ---
        
        # Get the current personal info from the database
        current_personal_info = config.personal_info

        # If the user submitted a new key, update it.
        # Otherwise, keep the existing key.
        new_gemini_key = request.form.get('gemini_api_key')
        if new_gemini_key:
            current_personal_info['gemini_api_key'] = new_gemini_key
        
        # Update all other fields from the form
        current_personal_info['name'] = request.form.get('name')
        current_personal_info['degree'] = request.form.get('degree')
        current_personal_info['cv_link'] = request.form.get('cv_link')
        current_personal_info['links'] = {
            "linkedin": request.form.get('linkedin'),
            "github": request.form.get('github'),
            "portfolio": request.form.get('portfolio')
        }
        current_personal_info['skills'] = [skill.strip() for skill in request.form.get('skills', '').split(',')]

        config.user_email = request.form.get('user_email')
        config.personal_info_json = json.dumps(current_personal_info, indent=4)
        
        db.session.add(config)
        db.session.commit()
        flash('Settings saved successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    # --- KEY CHANGE: Do NOT pass the key to the template ---
    personal_info = config.personal_info
    # Instead, just check if the key is set or not
    api_key_is_set = bool(personal_info.get('gemini_api_key'))
        
    return render_template('settings.html', config=config, personal_info=personal_info, api_key_is_set=api_key_is_set)


# (The rest of your routes file is unchanged)
@bp.route('/api/analytics')
def get_analytics_data():
    period = request.args.get('period', 'W')
    jobs = Job.query.all()
    analytics_data = {"status_counts": {}, "weekly_counts": {}}
    if jobs:
        df = pd.DataFrame([{"status": j.status, "date": j.date_added} for j in jobs])
        analytics_data['status_counts'] = df['status'].value_counts().to_dict()
        df['date'] = pd.to_datetime(df['date'])
        period_map = {'D': 'D', 'W': 'W-MON', 'M': 'ME'}
        resample_rule = period_map.get(period, 'W-MON')
        counts = df.set_index('date').resample(resample_rule).size()
        analytics_data['weekly_counts'] = {date.strftime('%Y-%m-%d'): count for date, count in counts.items()}
    return jsonify(analytics_data)

@bp.route('/job/<int:job_id>')
def get_job_details(job_id):
    job = Job.query.get_or_404(job_id)
    return jsonify({"id": job.id, "job_type": job.job_type, "description": job.description, "recipient_email": job.recipient_email, "status": job.status, "date_added": job.date_added.strftime('%Y-%m-%d')})

@bp.route('/update_status/<int:job_id>', methods=['POST'])
def update_status(job_id):
    job = Job.query.get_or_404(job_id)
    new_status = request.json.get('status')
    if new_status:
        job.status = new_status
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@bp.route('/add_job', methods=['GET', 'POST'])
def add_job():
    if request.method == 'POST':
        new_job = Job(job_type=request.form['job_type'],recipient_email=request.form['recipient_email'],description=request.form['description'],status='Pending')
        db.session.add(new_job)
        db.session.commit()
        flash('New job added!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('add_job.html')

@bp.route('/run_apply', methods=['POST'])
def run_apply():
    try:
        summary = services.run_application_process()
        flash(summary, 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('main.dashboard'))