"""
Migrare pentru adăugarea câmpului group_name în tabela users
"""
import sys
import os

# Adaug directorul rădăcină al proiectului la calea de căutare
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  
from app import db, create_app
from flask_migrate import Migrate
import os

app = create_app(os.getenv('FLASK_ENV', 'development'))
migrate = Migrate(app, db)

def upgrade():
    """Adaugă coloana group_name în tabela users"""
    with app.app_context():
        with db.engine.connect() as conn:
            conn.execute(db.text('ALTER TABLE users ADD COLUMN group_name VARCHAR(50)'))
            conn.commit()
        print("Coloana group_name a fost adăugată în tabela users")

def downgrade():
    """Elimină coloana group_name din tabela users"""
    with app.app_context():
        with db.engine.connect() as conn:
            conn.execute(db.text('ALTER TABLE users DROP COLUMN group_name'))
            conn.commit()
        print("Coloana group_name a fost eliminată din tabela users")

if __name__ == '__main__':
    with app.app_context():
        upgrade()
        print("Migrarea a fost aplicată cu succes!")
