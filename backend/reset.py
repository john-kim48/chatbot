from app import app
from models import db

if __name__ == '__main__':
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Recreate all tables
        db.create_all()
        print("Database has been reset successfully!")
