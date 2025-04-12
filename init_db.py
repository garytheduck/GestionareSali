from app import create_app, db
from app.models.user import User, UserRole
from app.models.settings import InstitutionSettings
import os

def init_database():
    """Initialize the database with required tables and default data"""
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            # Create default admin user
            admin = User(
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                role=UserRole.ADMIN,
                password='admin123'  # This should be changed immediately in production
            )
            db.session.add(admin)
        
        # Check if institution settings exist
        settings = InstitutionSettings.query.first()
        if not settings:
            # Create default settings
            settings = InstitutionSettings(
                name="Universitatea de Științe Aplicate",
                address="Strada Exemplu, Nr. 123, Oraș, Țară",
                current_semester="2023-2024-2"
            )
            db.session.add(settings)
        
        db.session.commit()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()
