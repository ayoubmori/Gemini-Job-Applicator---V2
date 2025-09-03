from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, UserConfig, Job
import services
import json

bp = Blueprint('main', __name__)

@bp.route('/')
def dashboard():
    jobs = Job.query.order_by(Job.date_added.desc()).all()
    return render_template('dashboard.html', jobs=jobs)

@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    config = UserConfig.query.first()
    if not config:
        config = UserConfig(id=1)

    if request.method == 'POST':
        skills_list = [skill.strip() for skill in request.form.get('skills', '').split(',')]
        
        personal_info_dict = {
            "name": request.form.get('name'),
            "degree": request.form.get('degree'),
            "cv_link": request.form.get('cv_link'),
            "gemini_api_key": request.form.get('gemini_api_key'),
            "links": {
                "linkedin": request.form.get('linkedin'),
                "github": request.form.get('github'),
                "portfolio": request.form.get('portfolio')
            },
            "skills": skills_list
        }
        
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
        new_job = Job(
            job_type=request.form['job_type'],
            recipient_email=request.form['recipient_email'],
            description=request.form['description'],
            status='Pending'
        )
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
