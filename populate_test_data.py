"""
Script pentru popularea bazei de date cu date de test pentru discipline, șefi de grupă și examene
"""
from app import create_app, db
from app.models.user import User, UserRole
from app.models.room import Room
from app.models.course import Course, ExamType
from app.models.group_leader import GroupLeader
from app.models.exam import Exam, ExamRegistration
from app.models.settings import InstitutionSettings
from datetime import datetime, timedelta, time, date
import random

app = create_app()

def populate_disciplines():
    """Populate database with sample courses/disciplines"""
    print("Populating disciplines...")
    
    # Get teachers from the database
    teachers = User.query.filter(User.role == UserRole.SECRETARY).all()
    
    # List to store created courses
    courses = []
    
    # Sample faculties
    faculties = ["Facultatea de Inginerie Electrică și Știința Calculatoarelor", 
                 "Facultatea de Inginerie Mecanică", 
                 "Facultatea de Litere și Științe ale Comunicării"]
    
    # Sample departments
    departments = {
        "Facultatea de Inginerie Electrică și Știința Calculatoarelor": [
            "Calculatoare, Electronică și Automatică",
            "Electrotehnică",
            "Calculatoare și Tehnologia Informației"
        ],
        "Facultatea de Inginerie Mecanică": [
            "Mecanică și Tehnologii",
            "Mecanică Aplicată"
        ],
        "Facultatea de Litere și Științe ale Comunicării": [
            "Limba și Literatura Română",
            "Limbi și Literaturi Străine"
        ]
    }
    
    # Sample study programs
    study_programs = {
        "Facultatea de Inginerie Electrică și Știința Calculatoarelor": [
            "Calculatoare",
            "Electronică Aplicată",
            "Automatică și Informatică Aplicată",
            "Ingineria Sistemelor Electroenergetice"
        ],
        "Facultatea de Inginerie Mecanică": [
            "Inginerie Mecanică",
            "Ingineria și Protecția Mediului în Industrie"
        ],
        "Facultatea de Litere și Științe ale Comunicării": [
            "Limba și Literatura Română - Engleză",
            "Limba și Literatura Română - Franceză",
            "Comunicare și Relații Publice"
        ]
    }
    
    # Sample course names
    course_names = {
        "Calculatoare": [
            "Programare Orientată pe Obiecte",
            "Structuri de Date și Algoritmi",
            "Rețele de Calculatoare",
            "Baze de Date",
            "Ingineria Programării",
            "Inteligență Artificială",
            "Arhitectura Calculatoarelor",
            "Sisteme de Operare",
            "Algoritmi Paraleli și Distribuiți",
            "Securitatea Sistemelor Informatice"
        ],
        "Electronică Aplicată": [
            "Dispozitive și Circuite Electronice",
            "Măsurări în Electronică",
            "Instrumentație Electronică",
            "Electronică de Putere",
            "Sisteme Embedded"
        ],
        "Automatică și Informatică Aplicată": [
            "Teoria Sistemelor Automate",
            "Programarea Aplicațiilor de Timp Real",
            "Sisteme Automate",
            "Ingineria Reglării Automate"
        ],
        "Inginerie Mecanică": [
            "Mecanică",
            "Rezistența Materialelor",
            "Organe de Mașini",
            "Termotehnică",
            "Mașini Unelte"
        ],
        "Limba și Literatura Română - Engleză": [
            "Lingvistică Generală",
            "Literatura Română",
            "Literatura Engleză",
            "Gramatică Comparată"
        ]
    }
    
    # Sample groups
    groups = {
        "Calculatoare": ["3201A", "3202B", "3203A", "3301A", "3302B", "3401A", "3402B"],
        "Electronică Aplicată": ["3101A", "3102B", "3201A"],
        "Automatică și Informatică Aplicată": ["3301A", "3302B"],
        "Inginerie Mecanică": ["3101A", "3102B"],
        "Limba și Literatura Română - Engleză": ["3101A", "3102B"]
    }
    
    # Create courses
    courses = []
    course_code = 1000
    
    # Create settings if not exists
    settings = InstitutionSettings.query.first()
    if not settings:
        settings = InstitutionSettings(
            name="Universitatea Ștefan cel Mare din Suceava",
            address="Strada Universității 13, Suceava 720229",
            current_semester="2024-2025-2"
        )
        db.session.add(settings)
        db.session.commit()
    
    semester = settings.current_semester.split("-")[2]  # Get the semester number (1 or 2)
    academic_year = settings.current_semester.split("-")[0] + "-" + settings.current_semester.split("-")[1]  # Get the academic year (e.g., 2024-2025)
    
    for faculty in faculties:
        selected_departments = departments[faculty]
        selected_study_programs = study_programs[faculty]
        
        for study_program in selected_study_programs:
            if study_program in course_names:
                for course_name in course_names[study_program]:
                    # Only add if course doesn't already exist
                    existing_course = Course.query.filter_by(name=course_name).first()
                    if existing_course:
                        courses.append(existing_course)
                        continue
                    
                    course_code += 1
                    code = f"C{course_code}"
                    
                    # Random year of study (1-4)
                    year_of_study = random.randint(1, 4)
                    
                    # Random teacher
                    teacher = random.choice(teachers) if teachers else None
                    
                    # Random exam type
                    exam_type_choices = [ExamType.EXAM, ExamType.COLLOQUIUM, ExamType.PROJECT]
                    exam_type = random.choice(exam_type_choices)
                    
                    # Random group from the study program
                    if study_program in groups:
                        # Filter groups by year of study
                        year_groups = [g for g in groups[study_program] if str(year_of_study) in g]
                        if year_groups:
                            group_name = random.choice(year_groups)
                        else:
                            group_name = random.choice(groups[study_program])
                    else:
                        group_name = f"{year_of_study}101A"  # Default group name
                    
                    # Create course
                    course = Course(
                        code=code,
                        name=course_name,
                        faculty=faculty,
                        department=random.choice(selected_departments),
                        study_program=study_program,
                        year_of_study=year_of_study,
                        semester=semester,
                        credits=random.randint(3, 6),
                        group_name=group_name,
                        exam_type=exam_type,
                        teacher_id=teacher.id if teacher else None
                    )
                    
                    db.session.add(course)
                    courses.append(course)
    
    db.session.commit()
    return courses

def populate_group_leaders():
    """Populate database with sample group leaders"""
    print("Populating group leaders...")
    
    # Settings
    settings = InstitutionSettings.query.first()
    if not settings:
        print("Error: No institution settings found. Please run populate_disciplines first.")
        return []
    
    semester = settings.current_semester.split("-")[2]  # Get the semester number (1 or 2)
    academic_year = settings.current_semester.split("-")[0] + "-" + settings.current_semester.split("-")[1]  # Get the academic year (e.g., 2024-2025)
    
    # Get all courses to extract unique groups
    courses = Course.query.all()
    
    # Extract all faculties, study programs, and groups
    faculties = set()
    study_programs = {}
    groups_by_program = {}
    
    for course in courses:
        faculties.add(course.faculty)
        
        if course.faculty not in study_programs:
            study_programs[course.faculty] = set()
        study_programs[course.faculty].add(course.study_program)
        
        if course.study_program not in groups_by_program:
            groups_by_program[course.study_program] = set()
        groups_by_program[course.study_program].add(course.group_name)
    
    # Get student users
    students = User.query.filter_by(role=UserRole.STUDENT).all()
    
    # Create student users if none exist
    if not students:
        names = [
            ("Alexandru", "Popescu"),
            ("Maria", "Ionescu"),
            ("Andrei", "Popa"),
            ("Elena", "Dumitru"),
            ("Ion", "Georgescu"),
            ("Ana", "Constantinescu"),
            ("Mihai", "Stanescu"),
            ("Cristina", "Radu"),
            ("Florin", "Munteanu"),
            ("Adriana", "Stoica")
        ]
        
        for i, (first_name, last_name) in enumerate(names):
            email = f"student{i+1}@student.usv.ro"
            student = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.STUDENT,
                password="student123",
                auth_provider="local"
            )
            db.session.add(student)
        
        db.session.commit()
        students = User.query.filter_by(role=UserRole.STUDENT).all()
    
    # Create group leaders
    group_leaders = []
    student_index = 0
    
    # For each study program
    for study_program, groups in groups_by_program.items():
        # For each group
        for group in groups:
            # Skip if group leader already exists for this group
            existing_group_leader = GroupLeader.query.filter_by(group_name=group).first()
            if existing_group_leader:
                group_leaders.append(existing_group_leader)
                continue
            
            # Determine faculty
            faculty = None
            for f, programs in study_programs.items():
                if study_program in programs:
                    faculty = f
                    break
            
            if not faculty:
                continue
            
            # Get year of study from group name
            try:
                year_of_study = int(group[0])
            except:
                year_of_study = random.randint(1, 4)
            
            # Get student for this group leader
            if student_index < len(students):
                student = students[student_index]
                student_index += 1
            else:
                student_index = 0
                student = students[student_index]
            
            # Create group leader
            group_leader = GroupLeader(
                user_id=student.id,
                group_name=group,
                faculty=faculty,
                study_program=study_program,
                year_of_study=year_of_study,
                current_semester=semester,
                academic_year=academic_year
            )
            
            db.session.add(group_leader)
            group_leaders.append(group_leader)
    
    db.session.commit()
    return group_leaders

def populate_exams(courses):
    """Populate database with sample exams"""
    print("Populating exams...")
    
    # Return empty list if no courses provided
    if not courses:
        print("No courses provided. Skipping exam population.")
        return []
    
    # Settings
    settings = InstitutionSettings.query.first()
    semester = settings.current_semester.split("-")[2]  # Get the semester number (1 or 2)
    academic_year = settings.current_semester.split("-")[0] + "-" + settings.current_semester.split("-")[1]  # Get the academic year
    
    # Get all rooms
    rooms = Room.query.all()
    if not rooms:
        print("Error: No rooms found. Please make sure rooms are populated.")
        return []
    
    # Get all students
    students = User.query.filter_by(role=UserRole.STUDENT).all()
    
    # Check if there are students
    if not students:
        print("Error: No students found. Please make sure students are populated.")
        return []
    
    # Current date
    today = date.today()
    
    # Create exams
    exams = []
    
    # For each course, create an exam
    for course in courses:
        # Skip if exam already exists for this course
        existing_exam = Exam.query.filter_by(course_id=course.id).first()
        if existing_exam:
            exams.append(existing_exam)
            continue
        
        # Random room
        room = random.choice(rooms)
        
        # Random date (in 2-5 weeks)
        exam_date = today + timedelta(days=random.randint(14, 35))
        
        # Random start time (9:00, 11:00, 13:00, 15:00, 17:00)
        start_hours = [9, 11, 13, 15, 17]
        start_hour = random.choice(start_hours)
        start_time = datetime.combine(exam_date, time(start_hour, 0))
        
        # Random duration (1.5 - 3 hours)
        duration_hours = random.choice([1.5, 2, 2.5, 3])
        end_time = start_time + timedelta(hours=duration_hours)
        
        # Create exam
        exam = Exam(
            course_id=course.id,
            room_id=room.id,
            start_time=start_time,
            end_time=end_time,
            exam_type=course.exam_type.value,
            semester=semester,
            academic_year=academic_year,
            max_students=room.capacity,
            notes=f"Examen pentru {course.name}, grupa {course.group_name}"
        )
        
        db.session.add(exam)
        db.session.commit()  # Commit to get the exam ID
        
        exams.append(exam)
        
        # Add exam registrations for some students
        students_for_exam = []
        
        # Filter students by suffix in email that matches the course group
        # (This is just a simplification - in reality, we'd need a proper mapping)
        for student in students:
            # Random selection (30% chance of registering)
            if random.random() < 0.3:
                students_for_exam.append(student)
        
        # Ensure we have at least some students per exam, but no more than the room capacity
        # Set a maximum number of attempts to prevent infinite loops
        attempts = 0
        max_attempts = 50
        
        while len(students_for_exam) < min(5, len(students)) and len(students_for_exam) < room.capacity and attempts < max_attempts:
            student = random.choice(students)
            if student not in students_for_exam:
                students_for_exam.append(student)
            attempts += 1
        
        if len(students_for_exam) == 0:
            print(f"Warning: No students assigned to exam for course {course.name}")
        
        # Create exam registrations
        for student in students_for_exam:
            registration = ExamRegistration(
                exam_id=exam.id,
                student_id=student.id,
                status=random.choice(['registered', 'confirmed', 'cancelled']),
                notes="Înregistrare test"
            )
            db.session.add(registration)
    
    db.session.commit()
    return exams

def main():
    """Main function to populate database with test data"""
    with app.app_context():
        try:
            # Populate disciplines
            courses = populate_disciplines()
            print(f"Added {len(courses)} disciplines")
            
            # Populate group leaders
            group_leaders = populate_group_leaders()
            print(f"Added {len(group_leaders)} group leaders")
            
            # Populate exams
            exams = populate_exams(courses)
            print(f"Added {len(exams)} exams")
            
            print("Database successfully populated with test data!")
        except Exception as e:
            print(f"Error populating database: {e}")

if __name__ == "__main__":
    main()
