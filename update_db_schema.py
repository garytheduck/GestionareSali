from app import create_app, db
import os

def update_database_schema():
    """Update the database schema to include google_id field"""
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        # Recreate all tables - this will update the schema
        # Warning: This will delete all data in the database
        db.drop_all()
        db.create_all()
        
        print("Database schema updated successfully!")

if __name__ == '__main__':
    update_database_schema()
