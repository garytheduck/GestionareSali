"""
Utilitar pentru generarea rapoartelor de examene în format Excel și PDF
"""
import pandas as pd
import io
from datetime import datetime
from app.models.course import Course, ExamType
from app.models.exam import Exam
from app.models.settings import InstitutionSettings
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm
import logging

logger = logging.getLogger(__name__)

def generate_exam_schedule_excel(filters=None):
    """
    Generează un raport Excel cu programarea examenelor
    
    Args:
        filters (dict): Filtre opționale (faculty, department, etc.)
        
    Returns:
        bytes: Conținutul fișierului Excel
    """
    # Obținem setările instituției
    settings = InstitutionSettings.get_settings()
    
    # Construim query-ul pentru cursuri cu examene programate
    query = Course.query.filter(
        Course.status == 'approved',
        Course.approved_date.isnot(None),
        Course.is_active == True
    )
    
    if filters:
        if 'faculty' in filters and filters['faculty']:
            query = query.filter(Course.faculty == filters['faculty'])
        if 'department' in filters and filters['department']:
            query = query.filter(Course.department == filters['department'])
        if 'study_program' in filters and filters['study_program']:
            query = query.filter(Course.study_program == filters['study_program'])
        if 'year_of_study' in filters and filters['year_of_study']:
            query = query.filter(Course.year_of_study == int(filters['year_of_study']))
        if 'semester' in filters and filters['semester']:
            query = query.filter(Course.semester == filters['semester'])
        if 'group_name' in filters and filters['group_name']:
            query = query.filter(Course.group_name == filters['group_name'])
        if 'exam_type' in filters and filters['exam_type']:
            query = query.filter(Course.exam_type == ExamType(filters['exam_type']))
    
    # Executăm query-ul
    courses = query.all()
    
    # Creăm dataframe-ul
    data = []
    for course in courses:
        teacher_name = f"{course.teacher.academic_title or ''} {course.teacher.first_name} {course.teacher.last_name}".strip() if course.teacher else "Nedefinit"
        assistant_name = f"{course.assistant.academic_title or ''} {course.assistant.first_name} {course.assistant.last_name}".strip() if course.assistant else "Nedefinit"
        
        data.append({
            'Facultate': course.faculty,
            'Program de studiu': course.study_program,
            'An de studiu': course.year_of_study,
            'Grupa': course.group_name,
            'Disciplina': course.name,
            'Tip evaluare': course.exam_type.value if course.exam_type else "Nedefinit",
            'Profesor': teacher_name,
            'Asistent': assistant_name,
            'Data examen': course.approved_date.strftime('%d.%m.%Y') if course.approved_date else "Nedefinit",
            'Ora': course.approved_date.strftime('%H:%M') if course.approved_date else "Nedefinit",
            'Durata (ore)': course.exam_duration or "Nedefinit",
            'Sala': course.exam_room.name if course.exam_room else "Nedefinit",
            'Capacitate sala': course.exam_room.capacity if course.exam_room else "Nedefinit"
        })
    
    df = pd.DataFrame(data)
    
    # Creăm fișierul Excel în memorie
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Adăugăm foaia cu informații despre instituție
        info_data = {
            'Informație': ['Nume instituție', 'Adresă', 'Data generării raportului'],
            'Valoare': [
                settings.name if settings else "Universitatea Ștefan cel Mare din Suceava",
                settings.address if settings else "Str. Universității 13, Suceava",
                datetime.now().strftime('%d.%m.%Y %H:%M')
            ]
        }
        info_df = pd.DataFrame(info_data)
        info_df.to_excel(writer, sheet_name='Informații', index=False)
        
        # Adăugăm foaia cu programarea examenelor
        if not data:
            # Creăm un dataframe gol cu antetele dacă nu există date
            empty_df = pd.DataFrame(columns=[
                'Facultate', 'Program de studiu', 'An de studiu', 'Grupa', 'Disciplina',
                'Tip evaluare', 'Profesor', 'Asistent', 'Data examen', 'Ora',
                'Durata (ore)', 'Sala', 'Capacitate sala'
            ])
            empty_df.to_excel(writer, sheet_name='Programare examene', index=False)
        else:
            # Sortăm datele după facultate, program, an, grupă și dată
            df = df.sort_values(by=['Facultate', 'Program de studiu', 'An de studiu', 'Grupa', 'Data examen', 'Ora'])
            df.to_excel(writer, sheet_name='Programare examene', index=False)
        
        # Adăugăm foaia cu statistici
        if data:
            # Statistici pe facultăți
            faculty_stats = df.groupby('Facultate').size().reset_index(name='Număr examene')
            faculty_stats.to_excel(writer, sheet_name='Statistici', index=False, startrow=0)
            
            # Statistici pe tipuri de evaluare
            exam_type_stats = df.groupby('Tip evaluare').size().reset_index(name='Număr')
            exam_type_stats.to_excel(writer, sheet_name='Statistici', index=False, startrow=len(faculty_stats) + 3)
        else:
            # Creăm un dataframe gol cu statistici
            empty_stats = pd.DataFrame(columns=['Categorie', 'Număr'])
            empty_stats.to_excel(writer, sheet_name='Statistici', index=False)
    
    output.seek(0)
    return output.getvalue()

def generate_exam_schedule_pdf(filters=None):
    """
    Generează un raport PDF cu programarea examenelor
    
    Args:
        filters (dict): Filtre opționale (faculty, department, etc.)
        
    Returns:
        bytes: Conținutul fișierului PDF
    """
    # Obținem setările instituției
    settings = InstitutionSettings.get_settings()
    
    # Construim query-ul pentru cursuri cu examene programate
    query = Course.query.filter(
        Course.status == 'approved',
        Course.approved_date.isnot(None),
        Course.is_active == True
    )
    
    if filters:
        if 'faculty' in filters and filters['faculty']:
            query = query.filter(Course.faculty == filters['faculty'])
        if 'department' in filters and filters['department']:
            query = query.filter(Course.department == filters['department'])
        if 'study_program' in filters and filters['study_program']:
            query = query.filter(Course.study_program == filters['study_program'])
        if 'year_of_study' in filters and filters['year_of_study']:
            query = query.filter(Course.year_of_study == int(filters['year_of_study']))
        if 'semester' in filters and filters['semester']:
            query = query.filter(Course.semester == filters['semester'])
        if 'group_name' in filters and filters['group_name']:
            query = query.filter(Course.group_name == filters['group_name'])
        if 'exam_type' in filters and filters['exam_type']:
            query = query.filter(Course.exam_type == ExamType(filters['exam_type']))
    
    # Executăm query-ul și sortăm rezultatele
    courses = query.order_by(
        Course.faculty,
        Course.study_program,
        Course.year_of_study,
        Course.group_name,
        Course.approved_date
    ).all()
    
    # Creăm buffer-ul pentru PDF
    buffer = io.BytesIO()
    
    # Configurăm documentul PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    # Stiluri pentru text
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Elemente pentru document
    elements = []
    
    # Titlu
    institution_name = settings.name if settings else "Universitatea Ștefan cel Mare din Suceava"
    elements.append(Paragraph(f"{institution_name}", title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Subtitlu
    elements.append(Paragraph("Programarea examenelor", subtitle_style))
    elements.append(Paragraph(f"Data generării: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Filtre aplicate
    if filters:
        filter_text = "Filtre aplicate: "
        filter_parts = []
        if 'faculty' in filters and filters['faculty']:
            filter_parts.append(f"Facultate = {filters['faculty']}")
        if 'study_program' in filters and filters['study_program']:
            filter_parts.append(f"Program = {filters['study_program']}")
        if 'year_of_study' in filters and filters['year_of_study']:
            filter_parts.append(f"An = {filters['year_of_study']}")
        if 'group_name' in filters and filters['group_name']:
            filter_parts.append(f"Grupa = {filters['group_name']}")
        if 'exam_type' in filters and filters['exam_type']:
            filter_parts.append(f"Tip = {filters['exam_type']}")
        
        filter_text += ", ".join(filter_parts)
        elements.append(Paragraph(filter_text, normal_style))
        elements.append(Spacer(1, 0.5*cm))
    
    # Tabel cu examene
    if courses:
        # Antet tabel
        table_data = [
            ['Facultate', 'Program', 'An', 'Grupa', 'Disciplina', 'Tip', 'Data', 'Ora', 'Sala', 'Profesor']
        ]
        
        # Adăugăm datele
        for course in courses:
            teacher_name = f"{course.teacher.academic_title or ''} {course.teacher.first_name} {course.teacher.last_name}".strip() if course.teacher else "Nedefinit"
            
            table_data.append([
                course.faculty,
                course.study_program,
                str(course.year_of_study),
                course.group_name,
                course.name,
                course.exam_type.value if course.exam_type else "Nedefinit",
                course.approved_date.strftime('%d.%m.%Y') if course.approved_date else "Nedefinit",
                course.approved_date.strftime('%H:%M') if course.approved_date else "Nedefinit",
                course.exam_room.name if course.exam_room else "Nedefinit",
                teacher_name
            ])
        
        # Creăm tabelul
        table = Table(table_data, repeatRows=1)
        
        # Stilul tabelului
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(table)
    else:
        elements.append(Paragraph("Nu există examene programate care să corespundă criteriilor de filtrare.", normal_style))
    
    # Generăm PDF-ul
    doc.build(elements)
    
    buffer.seek(0)
    return buffer.getvalue()

def generate_exam_completion_stats():
    """
    Generează statistici despre gradul de completare a programării examenelor
    
    Returns:
        dict: Dicționar cu statistici
    """
    # Obținem toate cursurile active
    total_courses = Course.query.filter(Course.is_active == True).count()
    
    # Cursuri cu examene programate
    scheduled_courses = Course.query.filter(
        Course.status == 'approved',
        Course.approved_date.isnot(None),
        Course.is_active == True
    ).count()
    
    # Cursuri cu propuneri în așteptare
    pending_courses = Course.query.filter(
        Course.status == 'pending',
        Course.is_active == True
    ).count()
    
    # Cursuri cu propuneri respinse
    rejected_courses = Course.query.filter(
        Course.status == 'rejected',
        Course.is_active == True
    ).count()
    
    # Cursuri fără propuneri
    no_proposal_courses = total_courses - (scheduled_courses + pending_courses + rejected_courses)
    
    # Obținem lista cursurilor fără programare (pentru detalii)
    incomplete_courses = Course.query.filter(
        Course.status != 'approved',
        Course.is_active == True
    ).all()
    
    incomplete_details = []
    for course in incomplete_courses:
        teacher_name = f"{course.teacher.academic_title or ''} {course.teacher.first_name} {course.teacher.last_name}".strip() if course.teacher else "Nedefinit"
        
        incomplete_details.append({
            'id': course.id,
            'name': course.name,
            'faculty': course.faculty,
            'study_program': course.study_program,
            'year_of_study': course.year_of_study,
            'group_name': course.group_name,
            'teacher': teacher_name,
            'status': course.status,
            'rejection_reason': course.rejection_reason
        })
    
    # Calculăm procentajul de completare
    completion_percentage = (scheduled_courses / total_courses * 100) if total_courses > 0 else 0
    
    return {
        'total': total_courses,
        'scheduled': scheduled_courses,
        'pending': pending_courses,
        'rejected': rejected_courses,
        'no_proposal': no_proposal_courses,
        'completion_percentage': round(completion_percentage, 2),
        'incomplete_courses': incomplete_details
    }
