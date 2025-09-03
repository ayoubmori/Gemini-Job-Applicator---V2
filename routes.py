from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, UserConfig, Job
import services
import json
import pandas as pd
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
def dashboard():
    """
    Renders the main dashboard page. The analytics data will be fetched
    by a separate API call from the frontend.
    """
    jobs = Job.query.order_by(Job.date_added.desc()).all()
    return render_template('dashboard.html', jobs=jobs)

# --- NEW: DEDICATED API ENDPOINT FOR ANALYTICS ---
@bp.route('/api/analytics')
def get_analytics_data():
    """
    Provides analytics data as JSON, with a filter for the time period.
    """
    # Get the time period filter from the request, default to 'W-MON' (Weekly)
    period = request.args.get('period', 'W-MON') 
    
    jobs = Job.query.all()
    analytics_data = {"status_counts": {}, "weekly_counts": {}}

    if jobs:
        df = pd.DataFrame([
            {"status": j.status, "date": j.date_added} for j in jobs
        ])
        
        # 1. Get status counts for the pie chart
        analytics_data['status_counts'] = df['status'].value_counts().to_dict()
        
        # 2. Get time-series application counts based on the period filter
        df['date'] = pd.to_datetime(df['date'])
        
        # Use a dictionary to map filters to pandas resampling rules
        period_map = {
            'D': 'D',      # Daily
            'W': 'W-MON',  # Weekly (starting Monday)
            'M': 'ME'     # Monthly End
        }
        resample_rule = period_map.get(period, 'W-MON') # Default to Weekly
        
        counts = df.set_index('date').resample(resample_rule).size()
        analytics_data['weekly_counts'] = {
            date.strftime('%Y-%m-%d'): count for date, count in counts.items()
        }
        
    return jsonify(analytics_data)


# (The rest of your routes.py file remains the same)
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
        return jsonify({"success": True, "message": f"Status for Job {job_id} updated."})
    return jsonify({"success": False, "message": "New status not provided."}), 400

@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    # This route remains the same
    config = UserConfig.query.first()
    if not config: config = UserConfig(id=1)
    if request.method == 'POST':
        skills_list = [skill.strip() for skill in request.form.get('skills', '').split(',')]
        personal_info_dict = {"name": request.form.get('name'),"degree": request.form.get('degree'),"cv_link": request.form.get('cv_link'),"gemini_api_key": request.form.get('gemini_api_key'),"links": {"linkedin": request.form.get('linkedin'),"github": request.form.get('github'),"portfolio": request.form.get('portfolio')},"skills": skills_list}
        config.user_email = request.form.get('user_email')
        config.personal_info_json = json.dumps(personal_info_dict, indent=4)
        db.session.add(config)
        db.session.commit()
        flash('Settings saved successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    personal_info = config.personal_info
    gemini_key = personal_info.get('gemini_api_key', '')
    return render_template('settings.html', config=config, personal_info=personal_info, gemini_key=gemini_key)

@bp.route('/add_job', methods=['GET', 'POST'])
def add_job():
    if request.method == 'POST':
        new_job = Job(job_type=request.form['job_type'],recipient_email=request.form['recipient_email'],description=request.form['description'],status='Pending')
        db.session.add(new_job)
        db.session.commit()
        flash('New job added successfully!', 'success')
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

