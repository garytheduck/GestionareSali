# Documentație Tehnică - Sistem de Gestionare Săli

## 1. Introducere

### 1.1 Scopul documentului
Acest document reprezintă documentația tehnică a sistemului de gestionare a sălilor din cadrul universității. Documentul descrie arhitectura, modelele de date, fluxurile de lucru și funcționalitățile principale ale aplicației.

### 1.2 Descrierea sistemului
Sistemul de Gestionare Săli este o aplicație web care permite gestionarea eficientă a rezervărilor sălilor din cadrul universității. Aplicația oferă funcționalități pentru trei tipuri de utilizatori: studenți, secretariat și administratori. Studenții pot verifica disponibilitatea sălilor și pot trimite cereri de rezervare, secretariatul poate aproba sau respinge cererile, iar administratorii pot gestiona orarul și configurația sistemului.

### 1.3 Tehnologii utilizate
- **Backend**: Python 3.9+, Flask, SQLAlchemy ORM, Flask-Migrate, Alembic
- **Frontend**: React, Redux, Material-UI
- **Bază de date**: PostgreSQL 14
- **Autentificare**: JWT (JSON Web Tokens)
- **Containerizare**: Docker & Docker Compose
- **Procesare date**: Pandas
- **Notificări**: Flask-Mail

## 2. Arhitectura sistemului

Sistemul este construit pe o arhitectură modernă, bazată pe microservicii, cu separarea clară a responsabilităților între componente.

### 2.1 Diagrama arhitecturală

```
@startuml
title "Architecture Diagram - Gestionare Săli"

package "Frontend Container" {
  [React Application] as react
  [Components] as components
  [Redux Store] as redux
  [API Client] as apiClient
  [Auth Module] as authModule
  
  components --> redux : updates
  redux --> components : provides state
  components --> apiClient : requests
  apiClient --> authModule : auth tokens
}

package "Backend Container" {
  [Flask Application] as flask
  [Routes/Controllers] as routes
  [Services] as services
  [Models] as models
  [Utils] as utils
  [Schedule Importer] as scheduleImporter
  [USV API Client] as usvApiClient
  [Email Service] as emailService
  [Report Generator] as reportGenerator
  [Availability Checker] as availabilityChecker
  
  routes --> services : uses
  services --> models : manipulates
  services --> utils : uses
  utils --> scheduleImporter
  utils --> usvApiClient
  utils --> emailService
  utils --> reportGenerator
  utils --> availabilityChecker
}

database "Database Container" {
  [PostgreSQL] as postgres
  [users]
  [rooms]
  [schedules]
  [reservations]
  [settings]
  
  postgres --> users
  postgres --> rooms
  postgres --> schedules
  postgres --> reservations
  postgres --> settings
}

cloud "USV API" as usvApi

' Relații între containere
react --> flask : HTTP/JSON API
flask --> postgres : SQL via SQLAlchemy
usvApiClient --> usvApi : HTTP Requests

' Relații între componente specifice
apiClient ..> routes : REST API calls
models ..> users : ORM Mapping
scheduleImporter ..> usvApiClient : uses

@enduml
```

### 2.2 Descrierea componentelor

#### 2.2.1 Frontend Container
- **React Application**: Aplicația client care rulează în browser-ul utilizatorului
- **Components**: Componentele UI reutilizabile
- **Redux Store**: Stocarea centralizată a stării aplicației
- **API Client**: Modul pentru comunicarea cu backend-ul
- **Auth Module**: Gestionarea autentificării și autorizării

#### 2.2.2 Backend Container
- **Flask Application**: Aplicația server care expune API-urile
- **Routes/Controllers**: Definirea rutelor API și gestionarea cererilor HTTP
- **Services**: Logica de business a aplicației
- **Models**: Definirea modelelor de date și interacțiunea cu baza de date
- **Utils**: Module utilitare pentru diverse funcționalități:
  - **Schedule Importer**: Import orar din Excel/API USV
  - **USV API Client**: Comunicare cu API-ul universității
  - **Email Service**: Trimitere notificări prin email
  - **Report Generator**: Generare rapoarte
  - **Availability Checker**: Verificare disponibilitate săli

#### 2.2.3 Database Container
- **PostgreSQL**: Sistemul de gestiune a bazei de date
- **Tabele principale**: users, rooms, schedules, reservations, settings

## 3. Modele de date

### 3.1 Diagrama de clase

```
@startuml Class Diagram - Gestionare Săli

' Stilizare
skinparam classAttributeIconSize 0
skinparam classFontStyle bold
skinparam classFontSize 14
skinparam classBackgroundColor #f0f8ff
skinparam classBorderColor #2c3e50

' Enumerări
enum UserRole {
  STUDENT
  SECRETARY
  ADMIN
}

enum DayOfWeek {
  MONDAY
  TUESDAY
  WEDNESDAY
  THURSDAY
  FRIDAY
  SATURDAY
  SUNDAY
}

enum ReservationStatus {
  PENDING
  APPROVED
  REJECTED
}

' Clase principale
class User {
  +id: Integer
  +email: String
  +password_hash: String
  +first_name: String
  +last_name: String
  +role: UserRole
  +is_active: Boolean
  +created_at: DateTime
  +updated_at: DateTime
  --
  +full_name(): String
  +check_password(password): Boolean
  +set_password(password): void
}

class Room {
  +id: Integer
  +name: String
  +capacity: Integer
  +building: String
  +floor: Integer
  +room_type: String
  +description: String
  +usv_id: Integer
  +is_active: Boolean
  --
  +get_availability(date, start_time, end_time): Boolean
}

class Schedule {
  +id: Integer
  +room_id: Integer
  +day_of_week: DayOfWeek
  +start_time: Time
  +end_time: Time
  +subject: String
  +professor: String
  +group_name: String
  +semester: String
  +is_active: Boolean
  --
  +is_overlapping(other_schedule): Boolean
}

class Reservation {
  +id: Integer
  +reference_number: String
  +user_id: Integer
  +room_id: Integer
  +date: Date
  +start_time: Time
  +end_time: Time
  +purpose: String
  +status: ReservationStatus
  +rejection_reason: String
  +created_at: DateTime
  +updated_at: DateTime
  --
  +is_available(): Boolean
  +approve(): void
  +reject(reason): void
}

class InstitutionSettings {
  +id: Integer
  +name: String
  +address: String
  +current_semester: String
  +working_hours_start: Time
  +working_hours_end: Time
  +daily_report_time: Time
  +logo: Binary
  +updated_at: DateTime
  --
  +get_settings(): InstitutionSettings
}

' Relații
User "1" -- "many" Reservation : creates >
Room "1" -- "many" Schedule : has >
Room "1" -- "many" Reservation : reserved for >
UserRole -- User : has >
DayOfWeek -- Schedule : occurs on >
ReservationStatus -- Reservation : has >

@enduml
```

### 3.2 Descrierea modelelor

#### 3.2.1 User
Modelul User reprezintă utilizatorii sistemului, cu diferite roluri: student, secretariat sau administrator.

#### 3.2.2 Room
Modelul Room conține informații despre sălile disponibile în cadrul universității, inclusiv capacitate, clădire, etaj și tip.

#### 3.2.3 Schedule
Modelul Schedule reprezintă orarul săptămânal al sălilor, cu informații despre ziua săptămânii, intervalul orar, materia și profesorul.

#### 3.2.4 Reservation
Modelul Reservation reprezintă cererile de rezervare a sălilor, cu informații despre utilizatorul care a făcut cererea, sala rezervată, data și intervalul orar.

#### 3.2.5 InstitutionSettings
Modelul InstitutionSettings conține setările instituționale, cum ar fi numele instituției, adresa, semestrul curent și orele de lucru.

## 4. Cazuri de utilizare

### 4.1 Diagrama cazurilor de utilizare

```
@startuml Use Case Diagram - Gestionare Săli

' Stilizare
skinparam actorStyle awesome
skinparam usecaseBackgroundColor #f0f8ff
skinparam usecaseBorderColor #2c3e50
skinparam actorBackgroundColor #ffe6cc

' Actori
actor "Student" as student
actor "Secretariat" as secretary
actor "Administrator" as admin
actor "Sistem USV" as usvSystem

' Cazuri de utilizare pentru Student
rectangle "Sistem de Gestionare Săli" {
  ' Cazuri de utilizare comune
  usecase "Autentificare" as login
  usecase "Vizualizare profil" as viewProfile
  usecase "Schimbare parolă" as changePassword
  
  ' Cazuri de utilizare pentru Student
  usecase "Vizualizare săli disponibile" as viewRooms
  usecase "Verificare disponibilitate sală" as checkAvailability
  usecase "Creare cerere de rezervare" as createReservation
  usecase "Vizualizare rezervări proprii" as viewOwnReservations
  usecase "Anulare rezervare" as cancelReservation
  
  ' Cazuri de utilizare pentru Secretariat
  usecase "Vizualizare toate rezervările" as viewAllReservations
  usecase "Aprobare/Respingere rezervări" as approveReservations
  usecase "Gestionare săli" as manageRooms
  usecase "Generare rapoarte" as generateReports
  usecase "Vizualizare orar săli" as viewSchedule
  
  ' Cazuri de utilizare pentru Administrator
  usecase "Gestionare utilizatori" as manageUsers
  usecase "Configurare setări instituționale" as manageSettings
  usecase "Import orar din Excel" as importScheduleExcel
  usecase "Import orar din API USV" as importScheduleAPI
  usecase "Backup bază de date" as backupDatabase
  
  ' Relații pentru Student
  student --> login
  student --> viewProfile
  student --> changePassword
  student --> viewRooms
  student --> checkAvailability
  student --> createReservation
  student --> viewOwnReservations
  student --> cancelReservation
  
  ' Relații pentru Secretariat
  secretary --> login
  secretary --> viewProfile
  secretary --> changePassword
  secretary --> viewAllReservations
  secretary --> approveReservations
  secretary --> manageRooms
  secretary --> generateReports
  secretary --> viewSchedule
  
  ' Relații pentru Administrator
  admin --> login
  admin --> viewProfile
  admin --> changePassword
  admin --> manageUsers
  admin --> manageSettings
  admin --> importScheduleExcel
  admin --> importScheduleAPI
  admin --> backupDatabase
  admin --> viewAllReservations
  admin --> approveReservations
  admin --> manageRooms
  admin --> generateReports
  
  ' Relații pentru Sistem USV
  usvSystem --> importScheduleAPI
  
  ' Relații de includere și extindere
  login <.. viewProfile : <<include>>
  checkAvailability <.. createReservation : <<include>>
  viewAllReservations <.. approveReservations : <<include>>
  viewSchedule <.. checkAvailability : <<include>>
}

@enduml
```

### 4.2 Descrierea cazurilor de utilizare

#### 4.2.1 Student
- **Vizualizare săli disponibile**: Studentul poate vizualiza lista sălilor disponibile
- **Verificare disponibilitate sală**: Studentul poate verifica disponibilitatea unei săli pentru o anumită dată și interval orar
- **Creare cerere de rezervare**: Studentul poate crea o cerere de rezervare pentru o sală disponibilă
- **Vizualizare rezervări proprii**: Studentul poate vizualiza lista rezervărilor proprii
- **Anulare rezervare**: Studentul poate anula o rezervare proprie

#### 4.2.2 Secretariat
- **Vizualizare toate rezervările**: Secretariatul poate vizualiza toate rezervările
- **Aprobare/Respingere rezervări**: Secretariatul poate aproba sau respinge cererile de rezervare
- **Gestionare săli**: Secretariatul poate gestiona informațiile despre săli
- **Generare rapoarte**: Secretariatul poate genera rapoarte despre utilizarea sălilor
- **Vizualizare orar săli**: Secretariatul poate vizualiza orarul săptămânal al sălilor

#### 4.2.3 Administrator
- **Gestionare utilizatori**: Administratorul poate gestiona conturile de utilizator
- **Configurare setări instituționale**: Administratorul poate configura setările instituționale
- **Import orar din Excel**: Administratorul poate importa orarul din fișiere Excel
- **Import orar din API USV**: Administratorul poate importa orarul din API-ul USV
- **Backup bază de date**: Administratorul poate realiza backup-uri ale bazei de date

## 5. Fluxuri de lucru

### 5.1 Diagrama de activități pentru procesul de rezervare

```
@startuml Activity Diagram - Gestionare Săli

' Stilizare
skinparam activityBackgroundColor #f0f8ff
skinparam activityBorderColor #2c3e50
skinparam activityDiamondBackgroundColor #ffe6cc
skinparam activityDiamondBorderColor #2c3e50
skinparam activityStartColor #4CAF50
skinparam activityEndColor #F44336

' Diagrama de activități pentru procesul de rezervare a unei săli
title Diagrama de activități pentru procesul de rezervare a unei săli

|Student|
start
:Autentificare în sistem;
:Accesare pagină rezervări;
:Selectare dată și interval orar;
:Verificare disponibilitate săli;

|Sistem|
if (Există săli disponibile?) then (da)
  :Afișare săli disponibile;
  
  |Student|
  :Selectare sală;
  :Completare formular rezervare;
  :Trimitere cerere;
  
  |Sistem|
  :Validare date cerere;
  if (Date valide?) then (da)
    :Salvare cerere în baza de date;
    :Generare număr de referință;
    :Notificare secretariat;
    
    |Secretariat|
    :Primire notificare;
    :Verificare detalii rezervare;
    if (Rezervare aprobată?) then (da)
      :Aprobare rezervare;
      
      |Sistem|
      :Actualizare status rezervare;
      :Notificare student aprobare;
      
      |Student|
      :Primire confirmare rezervare;
      
    else (nu)
      |Secretariat|
      :Completare motiv respingere;
      :Respingere rezervare;
      
      |Sistem|
      :Actualizare status rezervare;
      :Notificare student respingere;
      
      |Student|
      :Primire notificare respingere;
    endif
    
  else (nu)
    :Afișare erori validare;
    
    |Student|
    :Corectare date;
  endif
  
else (nu)
  :Afișare mesaj indisponibilitate;
  
  |Student|
  :Selectare altă dată/interval;
endif

|Student|
stop

@enduml
```

### 5.2 Diagrama de stări pentru procesul de rezervare

```
@startuml State Diagram - Gestionare Săli

' Stilizare
skinparam stateBorderColor #2c3e50
skinparam stateBackgroundColor #f0f8ff
skinparam stateArrowColor #2c3e50
skinparam stateFontStyle bold

' Diagrama de stări pentru o rezervare
title Diagrama de stări pentru procesul de rezervare a unei săli

[*] --> Inițiată : Student creează rezervare

state Inițiată {
  state "Verificare disponibilitate" as Verificare
  state "Completare formular" as Formular
  
  [*] --> Verificare
  Verificare --> Formular : Sală disponibilă
  Verificare --> [*] : Sală indisponibilă
  Formular --> [*] : Trimitere cerere
}

Inițiată --> Înregistrată : Salvare în sistem

state Înregistrată {
  state "Validare automată" as Validare
  
  [*] --> Validare
  Validare --> [*] : Date valide
  Validare --> Înregistrată : Date invalide\nNotificare student
}

Înregistrată --> ÎnAșteptare : Notificare secretariat

state ÎnAșteptare {
  state "Examinare de către secretariat" as Examinare
  
  [*] --> Examinare
  Examinare --> [*]
}

ÎnAșteptare --> Aprobată : Secretar aprobă
ÎnAșteptare --> Respinsă : Secretar respinge\ncu motiv

state Aprobată {
  state "Notificare student" as NotificareA
  state "Actualizare disponibilitate sală" as Actualizare
  
  [*] --> NotificareA
  NotificareA --> Actualizare
  Actualizare --> [*]
}

state Respinsă {
  state "Notificare student" as NotificareR
  
  [*] --> NotificareR
  NotificareR --> [*]
}

Aprobată --> Finalizată : Data rezervării a trecut
Respinsă --> [*]

state Finalizată {
  state "Arhivare" as Arhivare
  state "Includere în rapoarte" as Rapoarte
  
  [*] --> Arhivare
  Arhivare --> Rapoarte
  Rapoarte --> [*]
}

Finalizată --> [*]

@enduml
```

## 6. API-uri și integrări

### 6.1 Endpoint-uri API

#### 6.1.1 Autentificare
- `POST /api/auth/login` - Autentificare utilizator
- `POST /api/auth/register` - Înregistrare utilizator nou (doar pentru studenți)
- `POST /api/auth/reset-password` - Resetare parolă
- `GET /api/auth/me` - Obținere informații utilizator curent

#### 6.1.2 Student
- `GET /api/student/rooms` - Obținere listă săli disponibile
- `GET /api/student/rooms/{id}/availability` - Verificare disponibilitate sală
- `POST /api/student/reservations` - Creare cerere de rezervare
- `GET /api/student/reservations` - Obținere listă rezervări proprii
- `DELETE /api/student/reservations/{id}` - Anulare rezervare

#### 6.1.3 Secretariat
- `GET /api/secretary/reservations` - Obținere listă toate rezervările
- `PUT /api/secretary/reservations/{id}/approve` - Aprobare cerere de rezervare
- `PUT /api/secretary/reservations/{id}/reject` - Respingere cerere de rezervare
- `GET /api/secretary/rooms` - Obținere listă săli
- `POST /api/secretary/rooms` - Adăugare sală nouă
- `PUT /api/secretary/rooms/{id}` - Actualizare informații sală
- `GET /api/secretary/reports` - Generare rapoarte

#### 6.1.4 Administrator
- `GET /api/admin/users` - Obținere listă utilizatori
- `POST /api/admin/users` - Adăugare utilizator nou
- `PUT /api/admin/users/{id}` - Actualizare informații utilizator
- `DELETE /api/admin/users/{id}` - Dezactivare cont utilizator
- `GET /api/admin/settings` - Obținere setări instituționale
- `PUT /api/admin/settings` - Actualizare setări instituționale
- `POST /api/admin/import/excel` - Import orar din Excel
- `POST /api/admin/import/usv` - Import orar din API USV
- `POST /api/admin/backup` - Realizare backup bază de date

### 6.2 Integrare cu API-ul USV

Sistemul se integrează cu API-ul USV pentru a importa automat sălile și orarele. Integrarea este realizată prin intermediul modulului `usv_api_client.py`.

#### 6.2.1 Funcționalități
- Import săli și detalii (capacitate, clădire, etc.)
- Import orar semestrial pentru toate cadrele didactice
- Sincronizare automată a datelor

## 7. Securitate

### 7.1 Autentificare și autorizare
- Autentificarea utilizatorilor este realizată prin JWT (JSON Web Tokens)
- Parolele sunt stocate criptat în baza de date (hash + salt)
- Accesul la endpoint-uri este restricționat în funcție de rolul utilizatorului

### 7.2 Validare date
- Toate datele primite de la client sunt validate înainte de a fi procesate
- Se utilizează mecanisme de protecție împotriva atacurilor de tip SQL Injection și XSS

### 7.3 Rate limiting
- Se aplică rate limiting pentru a preveni atacurile de tip brute force și DDoS

## 8. Testare

### 8.1 Teste unitare
Testele unitare verifică funcționalitatea individuală a componentelor sistemului.

### 8.2 Teste de integrare
Testele de integrare verifică interacțiunea între diferite componente ale sistemului.

### 8.3 Teste end-to-end
Testele end-to-end verifică funcționalitatea completă a sistemului, de la interfața utilizator până la baza de date.

## 9. Deployment

### 9.1 Cerințe hardware și software
- **Procesor**: Minim 2 core-uri
- **Memorie RAM**: Minim 4GB
- **Spațiu de stocare**: Minim 20GB
- **Sistem de operare**: Linux (recomandat), Windows, macOS
- **Docker**: Versiunea 20.10 sau mai nouă
- **Docker Compose**: Versiunea 2.0 sau mai nouă

### 9.2 Pași de instalare
1. Clonare repository
2. Configurare fișier `.env` cu variabilele de mediu necesare
3. Rulare `docker-compose up -d`
4. Accesare aplicație la adresa `http://localhost:5000`

### 9.3 Configurare
Configurarea aplicației se realizează prin intermediul variabilelor de mediu sau al fișierului `.env`.

## 10. Mentenanță și suport

### 10.1 Backup și restaurare
- Backup-ul bazei de date se realizează automat zilnic
- Backup-urile sunt stocate în directorul `backups`
- Restaurarea se poate realiza prin intermediul interfeței de administrare

### 10.2 Monitorizare
- Sistemul generează log-uri detaliate despre activitatea utilizatorilor și erorile apărute
- Log-urile sunt stocate în directorul `logs`

### 10.3 Actualizare
- Actualizarea aplicației se realizează prin rularea comenzii `docker-compose pull && docker-compose up -d`

## 11. Concluzii

Sistemul de Gestionare Săli oferă o soluție completă pentru gestionarea rezervărilor sălilor din cadrul universității. Prin intermediul interfeței intuitive și al funcționalităților avansate, sistemul facilitează procesul de rezervare a sălilor, reducând timpul necesar și eliminând erorile umane.

## 12. Anexe

### 12.1 Glosar de termeni
- **API**: Application Programming Interface
- **JWT**: JSON Web Token
- **ORM**: Object-Relational Mapping
- **REST**: Representational State Transfer

### 12.2 Referințe
- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [React Documentation](https://reactjs.org/docs/getting-started.html)
- [Docker Documentation](https://docs.docker.com/)
