from app import app, db
from models import User
import sys

def set_admin(email):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            try:
                user.is_admin = True
                db.session.commit()
                print(f"SUCCESS: Admin privileges granted to {email}")
            except Exception as e:
                print(f"ERROR: Could not set admin privilege: {e}")
        else:
            print(f"ERROR: User with email '{email}' not found. Please register first.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        email = sys.argv[1]
    else:
        email = input("Enter email to promote to admin: ")
    
    if email:
        set_admin(email.strip())
    else:
        print("No email provided.")
