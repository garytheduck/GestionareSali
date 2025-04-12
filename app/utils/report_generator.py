import pandas as pd
import io
from datetime import datetime
from app.models.reservation import Reservation, ReservationStatus
from app.models.settings import InstitutionSettings

def generate_reservations_report(start_date, end_date):
    """Generate Excel report for reservations in the given date range"""
    # Get institution settings
    settings = InstitutionSettings.get_settings()
    
    # Query reservations for the date range
    reservations = Reservation.query.filter(
        Reservation.date >= start_date,
        Reservation.date <= end_date
    ).order_by(Reservation.date, Reservation.start_time).all()
    
    # Create dataframe
    data = []
    for reservation in reservations:
        data.append({
            'Număr referință': reservation.reference_number,
            'Data depunerii': reservation.created_at.strftime('%d.%m.%Y %H:%M'),
            'Solicitant': reservation.user.full_name,
            'Email': reservation.user.email,
            'Sala': reservation.room.name,
            'Data': reservation.date.strftime('%d.%m.%Y'),
            'Ora început': reservation.start_time.strftime('%H:%M'),
            'Ora sfârșit': reservation.end_time.strftime('%H:%M'),
            'Scop': reservation.purpose,
            'Status': reservation.status.value,
            'Motiv respingere': reservation.rejection_reason or '',
            'Verificat de': reservation.reviewer.full_name if reservation.reviewer else '',
            'Data verificării': reservation.reviewed_at.strftime('%d.%m.%Y %H:%M') if reservation.reviewed_at else ''
        })
    
    df = pd.DataFrame(data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Add institution info sheet
        info_data = {
            'Informație': ['Nume instituție', 'Adresă', 'Data raportului', 'Perioada raportului'],
            'Valoare': [
                settings.name,
                settings.address,
                datetime.now().strftime('%d.%m.%Y %H:%M'),
                f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
            ]
        }
        info_df = pd.DataFrame(info_data)
        info_df.to_excel(writer, sheet_name='Informații', index=False)
        
        # Add reservations sheet
        if not data:
            # Create empty dataframe with headers if no data
            empty_df = pd.DataFrame(columns=[
                'Număr referință', 'Data depunerii', 'Solicitant', 'Email', 'Sala',
                'Data', 'Ora început', 'Ora sfârșit', 'Scop', 'Status',
                'Motiv respingere', 'Verificat de', 'Data verificării'
            ])
            empty_df.to_excel(writer, sheet_name='Rezervări', index=False)
        else:
            df.to_excel(writer, sheet_name='Rezervări', index=False)
        
        # Add summary sheet
        approved_count = sum(1 for r in reservations if r.status == ReservationStatus.APPROVED)
        rejected_count = sum(1 for r in reservations if r.status == ReservationStatus.REJECTED)
        pending_count = sum(1 for r in reservations if r.status == ReservationStatus.PENDING)
        
        summary_data = {
            'Categorie': ['Total rezervări', 'Aprobate', 'Respinse', 'În așteptare'],
            'Număr': [len(reservations), approved_count, rejected_count, pending_count]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Sumar', index=False)
    
    output.seek(0)
    return output.getvalue()
