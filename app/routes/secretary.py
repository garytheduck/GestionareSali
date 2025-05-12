from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app.models.user import User, UserRole
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room
from app.models.group_leader import GroupLeader
from app import db
from app.utils.email_service import send_approval_notification, send_rejection_notification
from app.utils.report_generator import generate_reservations_report
import io
import os
import tempfile
import pandas as pd
import xlsxwriter

secretary_bp = Blueprint('secretary', __name__)

@secretary_bp.route('/rooms', methods=['GET'])
@jwt_required()
def get_rooms():
    """Get all rooms available for reservations"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get query parameters for filtering
    building = request.args.get('building')
    room_type = request.args.get('room_type')
    min_capacity = request.args.get('min_capacity', type=int)
    
    # Build query
    query = Room.query.filter(Room.is_active == True)
    
    # Apply filters
    if building:
        query = query.filter(Room.building == building)
    
    if room_type:
        query = query.filter(Room.room_type == room_type)
    
    if min_capacity:
        query = query.filter(Room.capacity >= min_capacity)
    
    # Order by building and name
    query = query.order_by(Room.building, Room.name)
    
    rooms = query.all()
    
    # Debug log pentru a vedea ce date sunt trimise către frontend
    room_data = [room.to_dict() for room in rooms]
    print(f"Sending {len(room_data)} rooms to frontend")
    for i, room in enumerate(room_data[:5]):  # Afișăm primele 5 săli pentru depanare
        print(f"Room {i+1}: {room}")
    
    return jsonify({
        'rooms': room_data
    }), 200

@secretary_bp.route('/reservations/pending', methods=['GET'])
@jwt_required()
def get_pending_reservations():
    """Get all pending reservations"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get query parameters
    room_id = request.args.get('room_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build query
    query = Reservation.query.filter(Reservation.status == ReservationStatus.PENDING)
    
    # Apply filters
    if room_id:
        query = query.filter(Reservation.room_id == room_id)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Reservation.date >= date_from_obj)
        except ValueError:
            pass  # Ignore invalid date
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Reservation.date <= date_to_obj)
        except ValueError:
            pass  # Ignore invalid date
    
    # Order by date and time
    query = query.order_by(Reservation.date.asc(), Reservation.start_time.asc())
    
    reservations = query.all()
    
    return jsonify({
        'reservations': [reservation.to_dict() for reservation in reservations]
    }), 200

@secretary_bp.route('/reservations/<int:reservation_id>/approve', methods=['PUT'])
@jwt_required()
def approve_reservation(reservation_id):
    """Approve a pending reservation"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    reservation = Reservation.query.get(reservation_id)
    
    if not reservation:
        return jsonify({'message': 'Rezervare negăsită'}), 404
    
    if reservation.status != ReservationStatus.PENDING:
        return jsonify({'message': 'Doar rezervările în așteptare pot fi aprobate'}), 400
    
    # Approve the reservation
    reservation.approve(user.id)
    db.session.commit()
    
    # Send notification to student
    send_approval_notification(reservation)
    
    return jsonify({
        'message': 'Rezervarea a fost aprobată cu succes',
        'reservation': reservation.to_dict()
    }), 200

@secretary_bp.route('/reservations/<int:reservation_id>/reject', methods=['PUT'])
@jwt_required()
def reject_reservation(reservation_id):
    """Reject a pending reservation"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    reservation = Reservation.query.get(reservation_id)
    
    if not reservation:
        return jsonify({'message': 'Rezervare negăsită'}), 404
    
    if reservation.status != ReservationStatus.PENDING:
        return jsonify({'message': 'Doar rezervările în așteptare pot fi respinse'}), 400
    
    data = request.get_json()
    
    if not data or not data.get('rejection_reason'):
        return jsonify({'message': 'Motivul respingerii este obligatoriu'}), 400
    
    # Reject the reservation
    reservation.reject(user.id, data.get('rejection_reason'))
    db.session.commit()
    
    # Send notification to student
    send_rejection_notification(reservation)
    
    return jsonify({
        'message': 'Rezervarea a fost respinsă',
        'reservation': reservation.to_dict()
    }), 200

@secretary_bp.route('/reservations/<int:reservation_id>/edit', methods=['PUT'])
@jwt_required()
def edit_reservation(reservation_id):
    """Edit a reservation (for corrections)"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    reservation = Reservation.query.get(reservation_id)
    
    if not reservation:
        return jsonify({'message': 'Rezervare negăsită'}), 404
    
    data = request.get_json()
    
    # Update allowed fields
    if data.get('room_id'):
        room = Room.query.get(data.get('room_id'))
        if not room or not room.is_active:
            return jsonify({'message': 'Sala nu a fost găsită sau este inactivă'}), 404
        reservation.room_id = room.id
    
    if data.get('purpose'):
        reservation.purpose = data.get('purpose')
    
    if data.get('date'):
        try:
            date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
            reservation.date = date
        except ValueError:
            return jsonify({'message': 'Format de dată invalid'}), 400
    
    if data.get('start_time'):
        try:
            start_time = datetime.strptime(data.get('start_time'), '%H:%M').time()
            reservation.start_time = start_time
        except ValueError:
            return jsonify({'message': 'Format de oră invalid'}), 400
    
    if data.get('end_time'):
        try:
            end_time = datetime.strptime(data.get('end_time'), '%H:%M').time()
            reservation.end_time = end_time
        except ValueError:
            return jsonify({'message': 'Format de oră invalid'}), 400
    
    # Validate start time is before end time
    if reservation.start_time >= reservation.end_time:
        return jsonify({'message': 'Ora de început trebuie să fie înainte de ora de sfârșit'}), 400
    
    db.session.commit()
    
    return jsonify({
        'message': 'Rezervarea a fost actualizată cu succes',
        'reservation': reservation.to_dict()
    }), 200

@secretary_bp.route('/reservations/history', methods=['GET'])
@jwt_required()
def get_reservation_history():
    """Get reservation history with filters"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get query parameters
    status = request.args.get('status')
    room_id = request.args.get('room_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query
    query = Reservation.query
    
    # Apply filters
    if status:
        try:
            status_enum = ReservationStatus(status)
            query = query.filter(Reservation.status == status_enum)
        except ValueError:
            pass  # Ignore invalid status
    
    if room_id:
        query = query.filter(Reservation.room_id == room_id)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Reservation.date >= date_from_obj)
        except ValueError:
            pass  # Ignore invalid date
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Reservation.date <= date_to_obj)
        except ValueError:
            pass  # Ignore invalid date
    
    # Order by date and time
    query = query.order_by(Reservation.date.desc(), Reservation.start_time.desc())
    
    # Paginate results
    paginated_reservations = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'reservations': [reservation.to_dict() for reservation in paginated_reservations.items],
        'total': paginated_reservations.total,
        'pages': paginated_reservations.pages,
        'current_page': page
    }), 200

@secretary_bp.route('/reports/daily', methods=['GET'])
@jwt_required()
def generate_daily_report():
    """Generate a daily report of reservations"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get date parameter, default to today
    date_str = request.args.get('date')
    
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'message': 'Format de dată invalid. Folosiți YYYY-MM-DD'}), 400
    else:
        date = datetime.now().date()
    
    # Generate report
    report_bytes = generate_reservations_report(date, date)
    
    # Create in-memory file
    report_io = io.BytesIO(report_bytes)
    report_io.seek(0)
    
    # Generate filename
    filename = f"rezervari_{date.strftime('%Y-%m-%d')}.xlsx"
    
    return send_file(
        report_io,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@secretary_bp.route('/reports/period', methods=['GET'])
@jwt_required()
def generate_period_report():
    """Generate a report for a specific period"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get date parameters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if not date_from or not date_to:
        return jsonify({'message': 'Parametrii date_from și date_to sunt obligatorii'}), 400
    
    try:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'message': 'Format de dată invalid. Folosiți YYYY-MM-DD'}), 400
    
    # Generate report
    report_bytes = generate_reservations_report(date_from_obj, date_to_obj)
    
    # Create in-memory file
    report_io = io.BytesIO(report_bytes)
    report_io.seek(0)
    
    # Generate filename
    filename = f"rezervari_{date_from_obj.strftime('%Y-%m-%d')}_{date_to_obj.strftime('%Y-%m-%d')}.xlsx"
    
    return send_file(
        report_io,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@secretary_bp.route('/exam-stats', methods=['GET'])
@jwt_required()
def get_exam_stats():
    """Get statistics about exams (total, completed, incomplete)"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get all exam/colloquium reservations
    exams = Reservation.query.filter(
        Reservation.purpose.like('%examen%') | Reservation.purpose.like('%colocviu%')
    ).all()
    
    # Count total and completed
    total = len(exams)
    completed = sum(1 for exam in exams if exam.status == ReservationStatus.APPROVED)
    
    # Get incomplete exams
    incomplete_exams = []
    for exam in exams:
        if exam.status != ReservationStatus.APPROVED:
            student = User.query.get(exam.user_id)
            
            # Extract discipline name from purpose
            purpose_parts = exam.purpose.split(' de ')
            discipline_name = purpose_parts[1] if len(purpose_parts) > 1 else exam.purpose
            
            incomplete_exams.append({
                'id': exam.id,
                'name': discipline_name,
                'group': student.group if hasattr(student, 'group') else 'N/A',
                'status': exam.status.value
            })
    
    return jsonify({
        'total': total,
        'completed': completed,
        'incomplete': incomplete_exams
    }), 200


@secretary_bp.route('/disciplines/import', methods=['POST'])
@jwt_required()
def import_disciplines():
    """Import disciplines from an Excel file"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Verificăm dacă a fost încărcat un fișier
    if 'file' not in request.files:
        return jsonify({'message': 'Nu a fost furnizat niciun fișier'}), 400
    
    file = request.files['file']
    
    # Verificăm dacă numele fișierului este gol
    if file.filename == '':
        return jsonify({'message': 'Nu a fost selectat niciun fișier'}), 400
    
    # Verificăm extensia fișierului
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'message': 'Formatul fișierului nu este suportat. Vă rugăm să încărcați un fișier Excel (.xlsx sau .xls)'}), 400
    
    try:
        # Citim fișierul Excel
        df = pd.read_excel(file)
        
        # Verificăm dacă fișierul are coloanele necesare pentru discipline
        required_columns = ['discipline_name', 'faculty', 'study_program', 'year_of_study', 'semester']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return jsonify({
                'message': f'Fișierul nu conține toate coloanele necesare. Lipsesc: {", ".join(missing_columns)}'
            }), 400
        
        # Procesăm datele și le salvăm în baza de date
        from app.models.course import Course, ExamType
        inserted = 0
        errors = []
        for idx, row in df.iterrows():
            try:
                # Verifică dacă există deja disciplina după cod sau nume+facultate+an+sem
                code = str(row.get('code') or f"{row['discipline_name']}-{row['faculty']}-{row['study_program']}-{row['year_of_study']}-{row['semester']}")
                existing = Course.query.filter_by(code=code).first()
                if existing:
                    errors.append(f"Linia {idx+2}: Disciplina deja există (code={code})")
                    continue
                # Asigură-te că group_name are o valoare implicită dacă nu există în Excel
                group_name = row.get('group_name')
                if not group_name or pd.isna(group_name):
                    # Generează un nume de grup implicit bazat pe program și an
                    group_name = f"{row['study_program'][:3]}{row['year_of_study']}"
                
                course = Course(
                    code=code,
                    name=row['discipline_name'],
                    faculty=row['faculty'],
                    study_program=row['study_program'],
                    year_of_study=int(row['year_of_study']),
                    semester=str(row['semester']),
                    credits=int(row['credits']) if 'credits' in row and pd.notnull(row['credits']) else None,
                    group_name=group_name,
                    exam_type=ExamType.EXAM,  # Valoare implicită
                    department=row.get('department') if row.get('department') and not pd.isna(row.get('department')) else None
                )
                db.session.add(course)
                inserted += 1
            except Exception as e:
                errors.append(f"Linia {idx+2}: {str(e)}")
        db.session.commit()
        
        # Notifică frontend-ul că datele au fost actualizate
        # Putem returna datele actualizate direct pentru a fi afișate imediat
        from app.routes.course_management import get_courses_data
        updated_courses = get_courses_data()
        
        # Redirectăm către pagina de discipline pentru a forța reîncărcarea datelor
        # Trimitem și un semnal către frontend pentru a reîmprospăta lista
        response = jsonify({
            'status': 'success',
            'message': f'Au fost importate cu succes {inserted} discipline',
            'count': inserted,
            'errors': errors,
            'data': updated_courses,
            'refresh': True  # Semnal pentru frontend să reîmprospăteze datele
        })
        
        # Adăugăm un header special pentru a indica că datele trebuie reîmprospătate
        response.headers['X-Refresh-Data'] = 'true'
        
        return response, 200
        
    except Exception as e:
        return jsonify({'message': f'Eroare la procesarea fișierului: {str(e)}'}), 500


@secretary_bp.route('/group-leaders', methods=['GET'])
@jwt_required()
def get_group_leaders():
    """Get all group leaders with optional filtering"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get query parameters for filtering
    faculty = request.args.get('faculty')
    study_program = request.args.get('study_program')
    year_of_study = request.args.get('year_of_study')
    group_name = request.args.get('group_name')
    current_semester = request.args.get('current_semester')
    academic_year = request.args.get('academic_year')
    
    # Build query
    query = GroupLeader.query
    
    # Apply filters
    if faculty:
        query = query.filter(GroupLeader.faculty == faculty)
    
    if study_program:
        query = query.filter(GroupLeader.study_program == study_program)
    
    if year_of_study:
        query = query.filter(GroupLeader.year_of_study == year_of_study)
    
    if group_name:
        query = query.filter(GroupLeader.group_name == group_name)
    
    if current_semester:
        query = query.filter(GroupLeader.current_semester == current_semester)
    
    if academic_year:
        query = query.filter(GroupLeader.academic_year == academic_year)
    
    # Order by faculty, study program, and year
    query = query.order_by(GroupLeader.faculty, GroupLeader.study_program, GroupLeader.year_of_study)
    
    group_leaders = query.all()
    
    # Debug log
    print(f"Returning {len(group_leaders)} group leaders")
    
    return jsonify({
        'group_leaders': [gl.to_dict() for gl in group_leaders]
    }), 200

@secretary_bp.route('/group-leaders/upload', methods=['POST'])
@jwt_required()
def upload_group_leaders():
    """Upload group leaders from an Excel file"""
    from app.models.user import User, UserRole
    from app.models.group_leader import GroupLeader
    
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Verificăm dacă a fost încărcat un fișier
    if 'file' not in request.files:
        return jsonify({'message': 'Nu a fost furnizat niciun fișier'}), 400
    
    file = request.files['file']
    
    # Verificăm dacă numele fișierului este gol
    if file.filename == '':
        return jsonify({'message': 'Nu a fost selectat niciun fișier'}), 400
    
    # Verificăm extensia fișierului
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'message': 'Formatul fișierului nu este suportat. Vă rugăm să încărcați un fișier Excel (.xlsx sau .xls)'}), 400
    
    # Obținem parametrii suplimentari (opționali)
    faculty = request.form.get('faculty', '')
    study_program = request.form.get('study_program', '')
    year_of_study = request.form.get('year_of_study', '')
    semester = request.form.get('semester', '')
    academic_year = request.form.get('academic_year', '')
    
    try:
        # Citim fișierul Excel
        df = pd.read_excel(file)
        
        # Verificăm dacă fișierul are coloanele necesare
        required_columns = ['email', 'group_name']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return jsonify({
                'message': f'Fișierul nu conține toate coloanele necesare. Lipsesc: {", ".join(missing_columns)}'
            }), 400
        
        # Procesăm datele și le salvăm în baza de date
        inserted = 0
        errors = []
        for idx, row in df.iterrows():
            try:
                try:
                    # Verifică dacă toate câmpurile obligatorii există
                    required_fields = ['email', 'group_name', 'faculty', 'study_program', 'year_of_study']
                    missing = [f for f in required_fields if f not in row or pd.isna(row[f])]
                    if missing:
                        errors.append(f"Linia {idx+2}: Lipsesc câmpuri obligatorii: {', '.join(missing)}")
                        continue
                        
                    # Caută user după email sau creează dacă nu există
                    email = str(row['email']).strip()
                    if not email or '@' not in email:
                        errors.append(f"Linia {idx+2}: Email invalid: {email}")
                        continue
                        
                    user = User.query.filter_by(email=email).first()
                    if not user:
                        # Creează un utilizator nou
                        first_name = str(row.get('first_name', '')).strip() or 'Student'
                        last_name = str(row.get('last_name', '')).strip() or 'Nou'
                        user = User(
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            role=UserRole.STUDENT
                        )
                        db.session.add(user)
                        db.session.flush()  # pentru a obține user.id
                        
                    # Verifică dacă există deja GroupLeader pentru grupă și user
                    group_name = str(row['group_name']).strip()
                    existing = GroupLeader.query.filter_by(user_id=user.id, group_name=group_name).first()
                    if existing:
                        errors.append(f"Linia {idx+2}: Șeful de grupă deja există ({email}, {group_name})")
                        continue
                        
                    # Pregătește valorile pentru câmpuri
                    faculty = str(row['faculty']).strip()
                    study_program = str(row['study_program']).strip()
                    year_of_study = int(row['year_of_study'])
                    current_semester = str(row.get('semester', '')).strip() or '1'
                    academic_year = str(row.get('academic_year', '')).strip() or '2024-2025'
                    
                    group_leader = GroupLeader(
                        user_id=user.id,
                        group_name=group_name,
                        faculty=faculty,
                        study_program=study_program,
                        year_of_study=year_of_study,
                        current_semester=current_semester,
                        academic_year=academic_year
                    )
                except Exception as e:
                    errors.append(f"Linia {idx+2}: Eroare la procesare: {str(e)}")
                    continue
                db.session.add(group_leader)
                inserted += 1
            except Exception as e:
                errors.append(f"Linia {idx+2}: {str(e)}")
        db.session.commit()
        
        # Notifică frontend-ul că datele au fost actualizate
        # Putem returna datele actualizate direct pentru a fi afișate imediat
        from app.routes.group_leader_management import get_group_leaders_data
        updated_group_leaders = get_group_leaders_data()
        
        # Redirectăm către pagina de șefi de grupă pentru a forța reîncărcarea datelor
        # Trimitem și un semnal către frontend pentru a reîmprospăta lista
        response = jsonify({
            'status': 'success',
            'message': f'Au fost importați cu succes {inserted} șefi de grupă',
            'count': inserted,
            'errors': errors,
            'data': updated_group_leaders,
            'refresh': True  # Semnal pentru frontend să reîmprospăteze datele
        })
        
        # Adăugăm un header special pentru a indica că datele trebuie reîmprospătate
        response.headers['X-Refresh-Data'] = 'true'
        
        return response, 200
        
    except Exception as e:
        return jsonify({'message': f'Eroare la procesarea fișierului: {str(e)}'}), 500


@secretary_bp.route('/templates/disciplines', methods=['GET'])
@jwt_required()
def get_disciplines_template():
    """Generate and return a template for disciplines import"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Creăm un fișier Excel temporar
    try:
        # Folosim un fișier temporar care nu va fi șters automat
        tmp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        tmp_path = tmp_file.name
        tmp_file.close()
        
        print(f"Generez template pentru discipline la: {tmp_path}")
        
        # Creăm workbook-ul Excel
        workbook = xlsxwriter.Workbook(tmp_path)
        worksheet = workbook.add_worksheet('Disciplines')
        
        # Adăugăm antetul
        headers = ['discipline_name', 'faculty', 'study_program', 'year_of_study', 'semester', 'credits', 'teacher_name', 'teacher_email']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        
        # Adăugăm câteva exemple
        example_data = [
            ['Programare în Java', 'FIESC', 'Calculatoare', '2', '1', '5', 'Prof. Ionescu', 'ionescu@usv.ro'],
            ['Baze de date', 'FIESC', 'Calculatoare', '2', '2', '6', 'Prof. Popescu', 'popescu@usv.ro'],
        ]
        
        for row, data in enumerate(example_data, start=1):
            for col, value in enumerate(data):
                worksheet.write(row, col, value)
        
        # Închide workbook-ul pentru a salva modificările
        workbook.close()
        
        print(f"Template generat cu succes, dimensiune: {os.path.getsize(tmp_path)} bytes")
        
        # Trimite fișierul către client
        response = send_file(
            tmp_path,
            as_attachment=True,
            download_name='disciplines_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Setăm un callback pentru a șterge fișierul după ce a fost trimis
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    print(f"Fișierul temporar {tmp_path} a fost șters")
            except Exception as e:
                print(f"Eroare la ștergerea fișierului temporar: {e}")
        
        return response
        
    except Exception as e:
        print(f"Eroare la generarea template-ului pentru discipline: {e}")
        return jsonify({'message': f'Eroare la generarea template-ului: {str(e)}'}), 500


@secretary_bp.route('/templates/group-leaders', methods=['GET'])
@jwt_required()
def get_group_leaders_template():
    """Generate and return a template for group leaders import"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Creăm un fișier Excel temporar
    try:
        # Folosim un fișier temporar care nu va fi șters automat
        tmp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        tmp_path = tmp_file.name
        tmp_file.close()
        
        print(f"Generez template pentru șefi de grupă la: {tmp_path}")
        
        # Creăm workbook-ul Excel
        workbook = xlsxwriter.Workbook(tmp_path)
        worksheet = workbook.add_worksheet('Group Leaders')
        
        # Adăugăm antetul
        headers = ['email', 'first_name', 'last_name', 'group_name', 'faculty', 'study_program', 'year_of_study', 'semester']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        
        # Adăugăm câteva exemple
        example_data = [
            ['student1@student.usv.ro', 'Ion', 'Popescu', '3201A', 'FIESC', 'Calculatoare', '3', '1'],
            ['student2@student.usv.ro', 'Maria', 'Ionescu', '3202B', 'FIESC', 'Automatică', '3', '2'],
        ]
        
        for row, data in enumerate(example_data, start=1):
            for col, value in enumerate(data):
                worksheet.write(row, col, value)
        
        # Închide workbook-ul pentru a salva modificările
        workbook.close()
        
        print(f"Template pentru șefi de grupă generat cu succes, dimensiune: {os.path.getsize(tmp_path)} bytes")
        
        # Trimite fișierul către client
        response = send_file(
            tmp_path,
            as_attachment=True,
            download_name='group_leaders_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Setăm un callback pentru a șterge fișierul după ce a fost trimis
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    print(f"Fișierul temporar {tmp_path} a fost șters")
            except Exception as e:
                print(f"Eroare la ștergerea fișierului temporar: {e}")
        
        return response
        
    except Exception as e:
        print(f"Eroare la generarea template-ului pentru șefi de grupă: {e}")
        return jsonify({'message': f'Eroare la generarea template-ului: {str(e)}'}), 500
