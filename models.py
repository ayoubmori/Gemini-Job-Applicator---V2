from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class UserConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=True)
    personal_info_json = db.Column(db.Text, nullable=True)

    @property
    def personal_info(self):
        if self.personal_info_json:
            try:
                return json.loads(self.personal_info_json)
            except json.JSONDecodeError:
                return {}
        return {}

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    recipient_email = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
