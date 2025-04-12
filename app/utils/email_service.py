from flask import render_template, current_app
from flask_mail import Message
from app import mail
from app.models.settings import InstitutionSettings
from app.models.reservation import Reservation
import threading

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
