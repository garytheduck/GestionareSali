"""
API endpoints pentru managementul șefilor de grupă
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import GroupLeader, User
from werkzeug.exceptions import BadRequest, NotFound
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_
from datetime import datetime
import re
import csv
import io
import logging
import pandas as pd
from werkzeug.utils import secure_filename
import os

logger = logging.getLogger(__name__)

# Creăm un Blueprint pentru managementul șefilor de grupă
group_leader_bp = Blueprint('group_leader', __name__, url_prefix='/api/group-leaders')

# Pattern pentru validarea adreselor de email
STUDENT_EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@student\.usv\.ro$'

def get_group_leaders_data(filters=None):
    """
    Funcție utilitară pentru a obține datele șefilor de grupă cu filtre opționale.
    Poate fi importată și folosită de alte module.
    
    Args:
        filters (dict): Filtre opționale (faculty, study_program, etc.)
        
    Returns:
        list: Lista de șefi de grupă serializată
    """
    try:
        # Construim query-ul
        query = GroupLeader.query.join(User)
        
        if filters:
            if 'faculty' in filters and filters['faculty']:
                query = query.filter(GroupLeader.faculty == filters['faculty'])
            if 'study_program' in filters and filters['study_program']:
                query = query.filter(GroupLeader.study_program == filters['study_program'])
            if 'year_of_study' in filters and filters['year_of_study']:
                query = query.filter(GroupLeader.year_of_study == int(filters['year_of_study']))
            if 'group_name' in filters and filters['group_name']:
                query = query.filter(GroupLeader.group_name == filters['group_name'])
            if 'current_semester' in filters and filters['current_semester']:
                query = query.filter(GroupLeader.current_semester == filters['current_semester'])
            if 'academic_year' in filters and filters['academic_year']:
                query = query.filter(GroupLeader.academic_year == filters['academic_year'])
        
        # Includem doar șefii de grupă activi
        query = query.filter(GroupLeader.is_active == True)
        
        # Executăm query-ul
        group_leaders = query.all()
        
        # Serializăm rezultatele
        result = []
        for gl in group_leaders:
            result.append({
                'id': gl.id,
                'user': {
                    'id': gl.user.id,
                    'first_name': gl.user.first_name,
                    'last_name': gl.user.last_name,
                    'email': gl.user.email,
                },
                'group_name': gl.group_name,
                'faculty': gl.faculty,
                'study_program': gl.study_program,
                'year_of_study': gl.year_of_study,
                'current_semester': gl.current_semester,
                'academic_year': gl.academic_year,
                'created_at': gl.created_at.isoformat() if gl.created_at else None,
                'updated_at': gl.updated_at.isoformat() if gl.updated_at else None
            })
        
        return result
    except Exception as e:
        logger.error(f"Error in get_group_leaders_data: {str(e)}")
        return []

@group_leader_bp.route('/', methods=['GET'])
@jwt_required()
def get_group_leaders():
    """
    Obține lista șefilor de grupă cu opțiuni de filtrare
    
    Query params:
        faculty (str): Filtrare după facultate
        study_program (str): Filtrare după program de studiu
        year_of_study (int): Filtrare după an de studiu
        group_name (str): Filtrare după grupă
        current_semester (str): Filtrare după semestrul curent
        academic_year (str): Filtrare după anul academic
    """
    try:
        # Preluăm parametrii din query string pentru filtrare
        filters = {
            'faculty': request.args.get('faculty'),
            'study_program': request.args.get('study_program'),
            'year_of_study': request.args.get('year_of_study'),
            'group_name': request.args.get('group_name'),
            'current_semester': request.args.get('current_semester'),
            'academic_year': request.args.get('academic_year')
        }
        
        # Folosim funcția utilitară pentru a obține datele
        result = get_group_leaders_data(filters)
        
        # Asigurăm formatul corect pentru frontend
        # Verificăm dacă există date și trimitem un mesaj corespunzător
        if not result:
            message = "Nu există șefi de grupă încă. Încărcați un fișier pentru a adăuga."
        else:
            message = f"Au fost găsiți {len(result)} șefi de grupă."
            
        return jsonify({
            'status': 'success',
            'message': message,
            'data': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting group leaders: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve group leaders',
            'error': str(e)
        }), 500


@group_leader_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_group_leaders():
    """
    Încarcă lista șefilor de grupă din fișier CSV sau Excel
    
    Form params:
        file: Fișierul CSV sau Excel cu lista șefilor de grupă
        faculty (str): Facultatea pentru care se încarcă șefii de grupă
        current_semester (str): Semestrul curent
        academic_year (str): Anul academic
    """
    try:
        # Verificăm dacă a fost încărcat un fișier
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        
        # Verificăm dacă numele fișierului este gol
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        # Verificăm dacă extensia fișierului este validă
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in ['.csv', '.xlsx', '.xls']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid file format. Only CSV and Excel files are allowed'
            }), 400
        
        # Verificăm parametrii obligatorii
        faculty = request.form.get('faculty')
        current_semester = request.form.get('current_semester')
        academic_year = request.form.get('academic_year')
        
        if not faculty or not current_semester or not academic_year:
            return jsonify({
                'status': 'error',
                'message': 'Faculty, current semester, and academic year are required'
            }), 400
        
        # Citim fișierul în funcție de extensie
        if file_ext == '.csv':
            # Citim fișierul CSV
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            df = pd.read_csv(stream)
        else:
            # Citim fișierul Excel
            df = pd.read_excel(file)
        
        # Verificăm dacă există coloanele obligatorii
        required_columns = ['first_name', 'last_name', 'email', 'group_name', 'study_program', 'year_of_study']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return jsonify({
                'status': 'error',
                'message': f'Missing required columns: {", ".join(missing_columns)}'
            }), 400
        
        # Rezultatele procesării
        results = {
            'total': len(df),
            'created': 0,
            'updated': 0,
            'failed': 0,
            'invalid_emails': [],
            'details': []
        }
        
        # Procesăm fiecare rând din fișier
        for index, row in df.iterrows():
            try:
                # Verificăm dacă adresa de email este validă
                email = row['email'].strip()
                if not re.match(STUDENT_EMAIL_PATTERN, email):
                    results['failed'] += 1
                    results['invalid_emails'].append(email)
                    results['details'].append({
                        'row': index + 2,  # +2 pentru a compensa header-ul și indexarea de la 0
                        'error': f'Invalid email format: {email}. Must match @student.usv.ro pattern'
                    })
                    continue
                
                # Verificăm dacă utilizatorul există deja în baza de date
                user = User.query.filter_by(email=email).first()
                
                if not user:
                    # Creăm un nou utilizator
                    user = User(
                        first_name=row['first_name'].strip(),
                        last_name=row['last_name'].strip(),
                        email=email,
                        role='student',
                        is_active=True,
                        group_name=row['group_name'].strip()  # Setăm grupa pentru utilizator
                    )
                    db.session.add(user)
                    db.session.flush()  # Pentru a obține ID-ul utilizatorului
                
                # Verificăm dacă șeful de grupă există deja
                group_leader = GroupLeader.query.filter(
                    and_(
                        GroupLeader.user_id == user.id,
                        GroupLeader.academic_year == academic_year,
                        GroupLeader.current_semester == current_semester
                    )
                ).first()
                
                if not group_leader:
                    # Creăm un nou șef de grupă
                    group_leader = GroupLeader(
                        user_id=user.id,
                        group_name=row['group_name'].strip(),
                        faculty=faculty,
                        study_program=row['study_program'].strip(),
                        year_of_study=int(row['year_of_study']),
                        current_semester=current_semester,
                        academic_year=academic_year,
                        is_active=True
                    )
                    db.session.add(group_leader)
                    results['created'] += 1
                else:
                    # Actualizăm șeful de grupă existent
                    group_leader.group_name = row['group_name'].strip()
                    group_leader.faculty = faculty
                    group_leader.study_program = row['study_program'].strip()
                    group_leader.year_of_study = int(row['year_of_study'])
                    group_leader.current_semester = current_semester
                    group_leader.academic_year = academic_year
                    group_leader.is_active = True
                    group_leader.updated_at = datetime.utcnow()
                    results['updated'] += 1
                    
                # Actualizăm și câmpul group_name din tabela User
                user.group_name = row['group_name'].strip()
                    
            except Exception as e:
                logger.error(f"Error processing row {index + 2}: {str(e)}")
                results['failed'] += 1
                results['details'].append({
                    'row': index + 2,
                    'error': str(e)
                })
        
        # Salvăm modificările în baza de date
        db.session.commit()
        
        # Returnăm rezultatul
        return jsonify({
            'status': 'success',
            'message': 'Group leaders uploaded successfully',
            'results': results
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uploading group leaders: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to upload group leaders',
            'error': str(e)
        }), 500


@group_leader_bp.route('/template', methods=['GET'])
@jwt_required()
def get_template():
    """
    Generează și returnează un template Excel pentru lista șefilor de grupă
    """
    try:
        # Creăm un DataFrame gol cu coloanele necesare
        df = pd.DataFrame(columns=[
            'first_name', 'last_name', 'email', 'group_name', 'study_program', 'year_of_study'
        ])
        
        # Adăugăm câteva exemple
        examples = [
            {
                'first_name': 'Ion',
                'last_name': 'Popescu',
                'email': 'ion.popescu@student.usv.ro',
                'group_name': '3211A',
                'study_program': 'Calculatoare',
                'year_of_study': 2
            },
            {
                'first_name': 'Maria',
                'last_name': 'Ionescu',
                'email': 'maria.ionescu@student.usv.ro',
                'group_name': '3211B',
                'study_program': 'Calculatoare',
                'year_of_study': 2
            }
        ]
        
        # Adăugăm exemplele în DataFrame
        for example in examples:
            df = df.append(example, ignore_index=True)
        
        # Creăm un buffer pentru fișierul Excel
        output = io.BytesIO()
        
        # Scriem DataFrame-ul în fișierul Excel
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Group Leaders', index=False)
            
            # Formatăm foaia Excel
            workbook = writer.book
            worksheet = writer.sheets['Group Leaders']
            
            # Formatăm header-ul
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Aplicăm formatul pentru header
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Ajustăm lățimea coloanelor
            worksheet.set_column('A:B', 15)  # first_name, last_name
            worksheet.set_column('C:C', 30)  # email
            worksheet.set_column('D:E', 20)  # group_name, study_program
            worksheet.set_column('F:F', 15)  # year_of_study
        
        # Setăm pointerul la începutul buffer-ului
        output.seek(0)
        
        # Returnăm fișierul Excel
        return jsonify({
            'status': 'success',
            'message': 'Template generated successfully',
            'download_url': '/api/group-leaders/download-template'
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate template',
            'error': str(e)
        }), 500


@group_leader_bp.route('/download-template', methods=['GET'])
def download_template():
    """
    Descarcă template-ul Excel pentru lista șefilor de grupă
    """
    try:
        # Creăm un DataFrame gol cu coloanele necesare
        df = pd.DataFrame(columns=[
            'first_name', 'last_name', 'email', 'group_name', 'study_program', 'year_of_study'
        ])
        
        # Adăugăm câteva exemple
        examples = [
            {
                'first_name': 'Ion',
                'last_name': 'Popescu',
                'email': 'ion.popescu@student.usv.ro',
                'group_name': '3211A',
                'study_program': 'Calculatoare',
                'year_of_study': 2
            },
            {
                'first_name': 'Maria',
                'last_name': 'Ionescu',
                'email': 'maria.ionescu@student.usv.ro',
                'group_name': '3211B',
                'study_program': 'Calculatoare',
                'year_of_study': 2
            }
        ]
        
        # Adăugăm exemplele în DataFrame
        for example in examples:
            df = pd.concat([df, pd.DataFrame([example])], ignore_index=True)
        
        # Creăm un buffer pentru fișierul Excel
        output = io.BytesIO()
        
        # Scriem DataFrame-ul în fișierul Excel
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Group Leaders', index=False)
            
            # Formatăm foaia Excel
            workbook = writer.book
            worksheet = writer.sheets['Group Leaders']
            
            # Formatăm header-ul
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Aplicăm formatul pentru header
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Ajustăm lățimea coloanelor
            worksheet.set_column('A:B', 15)  # first_name, last_name
            worksheet.set_column('C:C', 30)  # email
            worksheet.set_column('D:E', 20)  # group_name, study_program
            worksheet.set_column('F:F', 15)  # year_of_study
        
        # Setăm pointerul la începutul buffer-ului
        output.seek(0)
        
        # Creăm un fișier temporar pentru a fi trimis ca răspuns
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"group_leaders_template_{timestamp}.xlsx"
        
        # Returnăm fișierul Excel ca răspuns
        from flask import send_file
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Error downloading template: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to download template',
            'error': str(e)
        }), 500


@group_leader_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_group_leader(id):
    """
    Obține detaliile unui șef de grupă specific
    
    Path params:
        id (int): ID-ul șefului de grupă
    """
    try:
        group_leader = GroupLeader.query.get(id)
        
        if not group_leader:
            return jsonify({
                'status': 'error',
                'message': f'Group leader with ID {id} not found'
            }), 404
        
        # Serializăm rezultatul
        result = {
            'id': group_leader.id,
            'user': {
                'id': group_leader.user.id,
                'first_name': group_leader.user.first_name,
                'last_name': group_leader.user.last_name,
                'email': group_leader.user.email,
            },
            'group_name': group_leader.group_name,
            'faculty': group_leader.faculty,
            'study_program': group_leader.study_program,
            'year_of_study': group_leader.year_of_study,
            'current_semester': group_leader.current_semester,
            'academic_year': group_leader.academic_year,
            'created_at': group_leader.created_at.isoformat() if group_leader.created_at else None,
            'updated_at': group_leader.updated_at.isoformat() if group_leader.updated_at else None
        }
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting group leader {id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve group leader with ID {id}',
            'error': str(e)
        }), 500


@group_leader_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_group_leader(id):
    """
    Șterge (dezactivează) un șef de grupă
    
    Path params:
        id (int): ID-ul șefului de grupă
    """
    try:
        group_leader = GroupLeader.query.get(id)
        
        if not group_leader:
            return jsonify({
                'status': 'error',
                'message': f'Group leader with ID {id} not found'
            }), 404
        
        # Nu ștergem complet, doar dezactivăm
        group_leader.is_active = False
        group_leader.updated_at = datetime.utcnow()
        
        # Salvăm modificările în baza de date
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Group leader with ID {id} deactivated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting group leader {id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete group leader with ID {id}',
            'error': str(e)
        }), 500
