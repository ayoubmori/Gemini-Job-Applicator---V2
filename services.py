import time
import json
import base64
from email.message import EmailMessage
import google.generativeai as genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
from models import db, UserConfig, Job

# ... (_get_gmail_service function remains the same) ...
def _get_gmail_service():
    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def _generate_email_content(job, config):
    personal_info = config.personal_info
    
    genai.configure(api_key=personal_info.get('gemini_api_key'))
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    prompt = f"""
    You are an expert AI assistant writing a professional job application email.
    The response must be a valid JSON object with two keys: "subject" and "body".

    **Job Description to Analyze:**
    ---
    {job.description}
    ---

    **My Personal Information (use this to write the email):**
    ---
    - Name: {personal_info.get('name')}
    - Email: {config.user_email}
    - Degree: {personal_info.get('degree')}
    - Key Skills: {', '.join(personal_info.get('skills', []))}
    - CV Link: {personal_info.get('cv_link')}
    - Portfolio Links:
      - LinkedIn: {personal_info.get('links', {}).get('linkedin')}
      - GitHub: {personal_info.get('links', {}).get('github')}
      - Portfolio: {personal_info.get('links', {}).get('portfolio')}
    ---
    
    **Instructions for the email body:**
    1.  Create a compelling subject line including the job title.
    2.  Start with a polite greeting.
    3.  Express strong interest in the specific job role.
    4.  Mention my degree and highlight 2-3 key skills from my list that are most relevant to the job description.
    5.  Conclude by mentioning that my CV is available at the provided link and include my other portfolio links in a clean list.
    6.  Sign off professionally with my name and email address.
    """
    
    response = model.generate_content(prompt)
    cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
    return json.loads(cleaned_response)

def _send_email(service, to_email, subject, body, sender_email):
    message = EmailMessage()
    message.set_content(body)
    message["To"] = to_email
    message["From"] = sender_email
    message["Subject"] = subject
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {"raw": encoded_message}
    service.users().messages().send(userId="me", body=create_message).execute()
    return True

def run_application_process():
    config = UserConfig.query.first()
    if not config or not config.personal_info_json:
        raise ValueError("Configuration is incomplete. Please fill out all fields in Settings.")
    
    personal_info = config.personal_info
    if not personal_info.get('gemini_api_key') or not config.user_email:
         raise ValueError("User email and Gemini API Key must be set in Settings.")

    pending_jobs = Job.query.filter_by(status='Pending').all()
    if not pending_jobs:
        return "No pending jobs to apply for."

    applied_count = 0
    error_count = 0
    
    gmail_service = _get_gmail_service()

    for job in pending_jobs:
        try:
            job.status = 'Applying...'
            db.session.commit()
            email_data = _generate_email_content(job, config)
            _send_email(gmail_service, job.recipient_email, email_data.get('subject'), email_data.get('body'), config.user_email)
            job.status = 'Applied'
            db.session.commit()
            applied_count += 1
        except Exception as e:
            job.status = f'Error: {str(e)[:100]}'
            db.session.commit()
            error_count += 1
        time.sleep(10)
    return f"Process finished. Applied to {applied_count} jobs. Encountered {error_count} errors."