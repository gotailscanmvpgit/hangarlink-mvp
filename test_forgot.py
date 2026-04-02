import os
from app import create_app
from extensions import db, mail
from models import User
from flask_mail import Message as MailMessage

app = create_app()

def test():
    with app.app_context():
        print(f"Server: {app.config['MAIL_SERVER']}")
        print(f"User: {app.config['MAIL_USERNAME']}")
        
        user = User.query.filter_by(email='owner77@yahoo.com').first()
        if not user:
            print("User not found.")
            return
            
        print(f"Found user: {user.email}")
        
        from routes import _send_reset_email
        print("Triggering _send_reset_email...")
        success = _send_reset_email(user)
        print(f"Success: {success}")

if __name__ == '__main__':
    test()
