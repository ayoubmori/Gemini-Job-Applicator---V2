import os
from flask import Flask
from models import db
from routes import bp

# --- Application Setup ---
app = Flask(__name__)

# --- Configuration ---
# Set the secret key for flash messages, crucial for security and sessions.
app.config['SECRET_KEY'] = 'a-very-secret-key'

# Define the absolute path for the 'instance' folder, where the database will be stored.
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True) # Create the folder if it doesn't exist.

# Set the path for the SQLite database.
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(instance_path, 'database.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Database and Blueprint Initialization ---
# Initialize the database with the Flask app.
db.init_app(app)
# Register the routes defined in routes.py to make them accessible.
app.register_blueprint(bp)

# --- Create Database Tables ---
# This context block ensures that the database tables are created based on
# your models.py file if they don't already exist.
with app.app_context():
    db.create_all()

# --- Run the Application ---
# This block runs the Flask development server when you execute 'python app.py'.
if __name__ == '__main__':
    app.run(debug=True)