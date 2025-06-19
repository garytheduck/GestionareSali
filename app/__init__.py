from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_mail import Mail
import os
from app.config import config_by_name
from app.utils.cors_middleware import setup_cors_middleware

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
mail = Mail()

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    # Configurăm CORS - folosim doar o singură metodă pentru a evita duplicate
    # 1. Folosim doar middleware-ul nostru personalizat pentru CORS
    setup_cors_middleware(app)
    
    # NOTĂ: Am comentat configurarea flask_cors pentru a evita duplicate
    # CORS(app, resources={
    #     r"/*": {
    #         "origins": "*",
    #         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    #         "allow_headers": ["Content-Type", "Authorization"]
    #     }
    # })
    
    mail.init_app(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.secretary import secretary_bp
    from app.routes.admin import admin_bp
    from app.routes.teacher import teacher_bp
    from app.routes.course_management import course_bp
    from app.routes.group_leader_management import group_leader_bp
    from app.routes.exam_management import exam_bp
    from app.routes.exam_registration import registration_bp
    from app.routes.external_api import external_api_bp
    from app.routes.teacher_management import teacher_management_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(student_bp, url_prefix='/api/student')
    app.register_blueprint(secretary_bp, url_prefix='/api/secretary')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(teacher_bp, url_prefix='/api/teacher')
    app.register_blueprint(course_bp)
    app.register_blueprint(group_leader_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(registration_bp)
    app.register_blueprint(external_api_bp, url_prefix='/api/external')
    app.register_blueprint(teacher_management_bp)
    
    # Add root route for API documentation or welcome page
    @app.route('/')
    def index():
        return """
        <html>
            <head>
                <title>Programări Examene - API Backend</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                    h1 { color: #2c3e50; }
                    h2 { color: #3498db; }
                    pre { background-color: #f8f9fa; padding: 10px; border-radius: 5px; }
                    .endpoint { margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <h1>Programări Examene - API Backend</h1>
                <p>Aceasta este aplicația backend pentru sistemul de programare a examenelor universitare.</p>
                
                <h2>Endpoint-uri API disponibile:</h2>
                
                <div class="endpoint">
                    <h3>/api/auth</h3>
                    <p>Endpoint-uri pentru autentificare și gestionarea conturilor:</p>
                    <pre>/api/auth/login - Autentificare utilizator (POST)
/api/auth/register - Înregistrare utilizator nou (POST)
/api/auth/refresh - Reîmprospătare token (POST)
/api/auth/me - Informații profil utilizator (GET)
/api/auth/change-password - Schimbare parolă (PUT)</pre>
                </div>
                
                <div class="endpoint">
                    <h3>/api/student</h3>
                    <p>Endpoint-uri pentru studenți:</p>
                    <pre>/api/student/reservations - Gestionare rezervări (GET, POST)
/api/student/reservations/&lt;id&gt; - Detalii rezervare (GET, PUT, DELETE)</pre>
                </div>
                
                <div class="endpoint">
                    <h3>/api/secretary</h3>
                    <p>Endpoint-uri pentru secretariat:</p>
                    <pre>/api/secretary/reservations - Gestionare toate rezervările (GET)
/api/secretary/rooms - Gestionare săli (GET, POST)
/api/secretary/reports - Generare rapoarte (GET)</pre>
                </div>
                
                <div class="endpoint">
                    <h3>/api/admin</h3>
                    <p>Endpoint-uri pentru administratori:</p>
                    <pre>/api/admin/users - Gestionare utilizatori (GET, POST)
/api/admin/settings - Setări instituționale (GET, PUT)</pre>
                </div>
                
                <div class="endpoint">
                    <h3>/api/courses</h3>
                    <p>Endpoint-uri pentru gestionarea disciplinelor:</p>
                    <pre>/api/courses - Listare discipline (GET)
/api/courses/sync - Sincronizare discipline cu Orar (POST)</pre>
                </div>
                
                <div class="endpoint">
                    <h3>/api/group-leaders</h3>
                    <p>Endpoint-uri pentru gestionarea șefilor de grupă:</p>
                    <pre>/api/group-leaders - Listare șefi de grupă (GET)
/api/group-leaders/upload - Încărcare listă șefi de grupă (POST)
/api/group-leaders/template - Descărcare template (GET)</pre>
                </div>
                
                <p>Pentru a utiliza API-ul, este necesară autentificarea și obținerea unui token JWT.</p>
            </body>
        </html>
        """
    
    # Shell context
    @app.shell_context_processor
    def shell_context():
        return {'app': app, 'db': db}
    
    return app
