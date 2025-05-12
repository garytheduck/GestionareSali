from flask import render_template, current_app
from flask_mail import Message
from app import mail
from app.models.settings import InstitutionSettings
from app.models.reservation import Reservation
from app.models.course import Course
from app.models.group_leader import GroupLeader
from app.models.user import User
import threading
import pandas as pd
import io
from datetime import datetime

def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, html_body, attachments=None):
    """Send email with the given subject and body to the specified recipients"""
    app = current_app._get_current_object()
    settings = InstitutionSettings.get_settings()
    
    msg = Message(
        subject=f"{settings.name} - {subject}",
        recipients=recipients,
        html=html_body,
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    
    if attachments:
        for attachment in attachments:
            msg.attach(
                filename=attachment['filename'],
                content_type=attachment['content_type'],
                data=attachment['data']
            )
    
    # Send email asynchronously
    threading.Thread(target=send_async_email, args=(app, msg)).start()

def send_reservation_notification(reservation):
    """Send notification to secretariat about new reservation request"""
    # Get secretariat users
    from app.models.user import User, UserRole
    secretaries = User.query.filter(
        User.role.in_([UserRole.SECRETARY, UserRole.ADMIN]),
        User.is_active == True
    ).all()
    
    if not secretaries:
        return
    
    recipients = [secretary.email for secretary in secretaries]
    subject = f"Nouă cerere de rezervare: {reservation.reference_number}"
    
    # Build email body
    html_body = f"""
    <h2>Nouă cerere de rezervare</h2>
    <p>A fost primită o nouă cerere de rezervare cu următoarele detalii:</p>
    <ul>
        <li><strong>Număr de referință:</strong> {reservation.reference_number}</li>
        <li><strong>Solicitant:</strong> {reservation.user.full_name} ({reservation.user.email})</li>
        <li><strong>Sala:</strong> {reservation.room.name}</li>
        <li><strong>Data:</strong> {reservation.date.strftime('%d.%m.%Y')}</li>
        <li><strong>Interval orar:</strong> {reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}</li>
        <li><strong>Scop:</strong> {reservation.purpose}</li>
    </ul>
    <p>Vă rugăm să aprobați sau să respingeți această cerere din panoul de administrare.</p>
    """
    
    send_email(subject, recipients, html_body)

def send_approval_notification(reservation):
    """Send notification to student about approved reservation"""
    recipient = reservation.user.email
    subject = f"Cerere de rezervare aprobată: {reservation.reference_number}"
    
    # Build email body
    html_body = f"""
    <h2>Cerere de rezervare aprobată</h2>
    <p>Cererea dumneavoastră de rezervare a fost aprobată:</p>
    <ul>
        <li><strong>Număr de referință:</strong> {reservation.reference_number}</li>
        <li><strong>Sala:</strong> {reservation.room.name}</li>
        <li><strong>Data:</strong> {reservation.date.strftime('%d.%m.%Y')}</li>
        <li><strong>Interval orar:</strong> {reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}</li>
        <li><strong>Scop:</strong> {reservation.purpose}</li>
    </ul>
    <p>Vă mulțumim pentru utilizarea sistemului nostru de rezervări.</p>
    """
    
    send_email(subject, [recipient], html_body)

def send_rejection_notification(reservation):
    """Send notification to student about rejected reservation"""
    recipient = reservation.user.email
    subject = f"Cerere de rezervare respinsă: {reservation.reference_number}"
    
    # Build email body
    html_body = f"""
    <h2>Cerere de rezervare respinsă</h2>
    <p>Din păcate, cererea dumneavoastră de rezervare a fost respinsă:</p>
    <ul>
        <li><strong>Număr de referință:</strong> {reservation.reference_number}</li>
        <li><strong>Sala:</strong> {reservation.room.name}</li>
        <li><strong>Data:</strong> {reservation.date.strftime('%d.%m.%Y')}</li>
        <li><strong>Interval orar:</strong> {reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}</li>
        <li><strong>Scop:</strong> {reservation.purpose}</li>
    </ul>
    <p><strong>Motivul respingerii:</strong> {reservation.rejection_reason}</p>
    <p>Vă rugăm să faceți o nouă cerere ținând cont de motivul respingerii.</p>
    """
    
    send_email(subject, [recipient], html_body)

def send_daily_report(report_data, recipients):
    """Send daily report to specified recipients"""
    subject = f"Raport zilnic rezervări: {report_data['date']}"
    
    # Build email body
    html_body = f"""
    <h2>Raport zilnic rezervări</h2>
    <p>Data: {report_data['date']}</p>
    <p>Total rezervări: {report_data['total']}</p>
    <ul>
        <li>Aprobate: {report_data['approved']}</li>
        <li>Respinse: {report_data['rejected']}</li>
        <li>În așteptare: {report_data['pending']}</li>
    </ul>
    <p>Raportul detaliat este atașat acestui email.</p>
    """
    
    # Attach report file
    attachments = [{
        'filename': f"rezervari_{report_data['date']}.xlsx",
        'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'data': report_data['file_data']
    }]
    
    send_email(subject, recipients, html_body, attachments)

# Funcții pentru notificări legate de șefi de grupă
def send_group_leaders_import_notification(import_data):
    """Trimite notificare despre importul șefilor de grupă"""
    # Obținem utilizatorii cu rol de secretariat și admin
    from app.models.user import UserRole
    recipients = User.query.filter(
        User.role.in_([UserRole.SECRETARY, UserRole.ADMIN]),
        User.is_active == True
    ).with_entities(User.email).all()
    
    recipients = [r.email for r in recipients]
    
    if not recipients:
        return
    
    subject = "Import șefi de grupă finalizat"
    
    # Construim corpul emailului
    html_body = f"""
    <h2>Import șefi de grupă finalizat</h2>
    <p>Importul șefilor de grupă a fost finalizat cu succes.</p>
    <p><strong>Detalii import:</strong></p>
    <ul>
        <li>Șefi de grupă importați: {import_data.get('imported', 0)}</li>
        <li>Șefi de grupă actualizați: {import_data.get('updated', 0)}</li>
        <li>Erori: {import_data.get('errors', 0)}</li>
    </ul>
    <p>Puteți vizualiza lista completă a șefilor de grupă în panoul de administrare.</p>
    """
    
    send_email(subject, recipients, html_body)

def send_group_leader_welcome_email(group_leader):
    """Trimite email de bun venit pentru un șef de grupă nou"""
    if not group_leader.email:
        return
    
    subject = "Bun venit în sistemul de gestionare a examenelor"
    
    # Construim corpul emailului
    html_body = f"""
    <h2>Bun venit în sistemul de gestionare a examenelor!</h2>
    <p>Dragă {group_leader.first_name} {group_leader.last_name},</p>
    <p>Ai fost desemnat(ă) șef de grupă pentru grupa {group_leader.group_name} de la programul de studiu {group_leader.study_program}, anul {group_leader.year_of_study}, Facultatea {group_leader.faculty}.</p>
    <p>În calitate de șef de grupă, vei putea:</p>
    <ul>
        <li>Propune date pentru examenele din acest semestru</li>
        <li>Vizualiza statusul propunerilor</li>
        <li>Comunica cu profesorii și secretariatul</li>
    </ul>
    <p>Te rugăm să accesezi platforma și să îți activezi contul cât mai curând.</p>
    <p>Mulțumim pentru implicare!</p>
    """
    
    send_email(subject, [group_leader.email], html_body)

# Funcții pentru notificări legate de examene
def send_exam_proposal_notification(course):
    """Trimite notificare către profesor despre o propunere de dată pentru examen"""
    if not course.teacher or not course.teacher.email:
        return
    
    subject = f"Propunere nouă de dată pentru examen: {course.name}"
    
    # Construim corpul emailului
    html_body = f"""
    <h2>Propunere nouă de dată pentru examen</h2>
    <p>A fost primită o propunere nouă de dată pentru examenul la disciplina <strong>{course.name}</strong>.</p>
    <p><strong>Detalii propunere:</strong></p>
    <ul>
        <li><strong>Disciplina:</strong> {course.name}</li>
        <li><strong>Grupa:</strong> {course.group_name}</li>
        <li><strong>Program de studiu:</strong> {course.study_program}</li>
        <li><strong>Anul de studiu:</strong> {course.year_of_study}</li>
        <li><strong>Data propusă:</strong> {course.proposed_date.strftime('%d.%m.%Y %H:%M') if course.proposed_date else 'Nedefinită'}</li>
    </ul>
    <p>Vă rugăm să aprobați sau să respingeți această propunere din panoul de administrare.</p>
    """
    
    send_email(subject, [course.teacher.email], html_body)

def send_exam_approval_notification(course):
    """Trimite notificare către șeful de grupă despre aprobarea datei de examen"""
    # Găsim șeful de grupă pentru acest curs
    group_leader = GroupLeader.query.filter(
        GroupLeader.group_name == course.group_name,
        GroupLeader.faculty == course.faculty,
        GroupLeader.study_program == course.study_program,
        GroupLeader.year_of_study == course.year_of_study,
        GroupLeader.is_active == True
    ).first()
    
    if not group_leader or not group_leader.email:
        return
    
    subject = f"Propunere de examen aprobată: {course.name}"
    
    # Construim corpul emailului
    html_body = f"""
    <h2>Propunere de examen aprobată</h2>
    <p>Propunerea pentru examenul la disciplina <strong>{course.name}</strong> a fost aprobată.</p>
    <p><strong>Detalii examen:</strong></p>
    <ul>
        <li><strong>Disciplina:</strong> {course.name}</li>
        <li><strong>Grupa:</strong> {course.group_name}</li>
        <li><strong>Program de studiu:</strong> {course.study_program}</li>
        <li><strong>Anul de studiu:</strong> {course.year_of_study}</li>
        <li><strong>Data aprobată:</strong> {course.approved_date.strftime('%d.%m.%Y %H:%M') if course.approved_date else 'Nedefinită'}</li>
        <li><strong>Sala:</strong> {course.exam_room.name if course.exam_room else 'Nedefinită'}</li>
        <li><strong>Durata:</strong> {course.exam_duration} ore</li>
    </ul>
    <p>Vă rugăm să informați colegii despre programarea examenului.</p>
    """
    
    send_email(subject, [group_leader.email], html_body)

def send_exam_rejection_notification(course):
    """Trimite notificare către șeful de grupă despre respingerea datei de examen"""
    # Găsim șeful de grupă pentru acest curs
    group_leader = GroupLeader.query.filter(
        GroupLeader.group_name == course.group_name,
        GroupLeader.faculty == course.faculty,
        GroupLeader.study_program == course.study_program,
        GroupLeader.year_of_study == course.year_of_study,
        GroupLeader.is_active == True
    ).first()
    
    if not group_leader or not group_leader.email:
        return
    
    subject = f"Propunere de examen respinsă: {course.name}"
    
    # Construim corpul emailului
    html_body = f"""
    <h2>Propunere de examen respinsă</h2>
    <p>Din păcate, propunerea pentru examenul la disciplina <strong>{course.name}</strong> a fost respinsă.</p>
    <p><strong>Detalii propunere:</strong></p>
    <ul>
        <li><strong>Disciplina:</strong> {course.name}</li>
        <li><strong>Grupa:</strong> {course.group_name}</li>
        <li><strong>Program de studiu:</strong> {course.study_program}</li>
        <li><strong>Anul de studiu:</strong> {course.year_of_study}</li>
        <li><strong>Data propusă:</strong> {course.proposed_date.strftime('%d.%m.%Y %H:%M') if course.proposed_date else 'Nedefinită'}</li>
        <li><strong>Motivul respingerii:</strong> {course.rejection_reason or 'Nemotivat'}</li>
    </ul>
    <p>Vă rugăm să propuneți o nouă dată pentru examen, ținând cont de motivul respingerii.</p>
    """
    
    send_email(subject, [group_leader.email], html_body)
