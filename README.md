# Sistem de Programare Examene - Backend

Aplicație backend pentru gestionarea programării examenelor și rezervării sălilor din cadrul facultății.

## Descriere

Acest proiect reprezintă partea de backend pentru o aplicație de gestionare a rezervărilor sălilor de examen din cadrul unei universități. Sistemul permite studenților să verifice disponibilitatea sălilor și să trimită cereri de rezervare, secretariatului să aprobe sau să respingă cererile, iar administratorilor să gestioneze orarul și configurația sistemului.

## Tehnologii utilizate

- Python 3.9+
- Flask (framework web)
- PostgreSQL 14 (bază de date)
- Docker & Docker Compose (containerizare)
- JWT pentru autentificare
- SQLAlchemy ORM
- Flask-Migrate pentru migrări de bază de date
- Alembic pentru versionarea schemei bazei de date
- Pandas pentru procesarea datelor
- Flask-Mail pentru notificări prin email

## Structura proiectului

```
.
├── app/                    # Directorul principal al aplicației
│   ├── __init__.py         # Inițializare aplicație Flask
│   ├── config.py           # Configurații aplicație
│   ├── models/             # Modele de date
│   ├── routes/             # Rutele API
│   ├── services/           # Servicii business logic
│   └── utils/              # Utilități
│       ├── availability.py         # Verificare disponibilitate săli
│       ├── email_service.py        # Serviciu de notificări email
│       ├── report_generator.py     # Generare rapoarte
│       ├── schedule_importer.py    # Import orar din Excel/API
│       └── usv_api_client.py       # Client pentru API-ul USV
├── migrations/             # Migrări bază de date
├── tests/                  # Teste unitare și de integrare
├── docker-compose.yml      # Configurare Docker Compose
├── Dockerfile              # Configurare Docker pentru aplicație
├── requirements.txt        # Dependințe Python
└── README.md               # Documentație proiect
```

## Instalare și rulare

### Cerințe preliminare

- Docker și Docker Compose instalate
- Git (opțional, pentru clonarea repository-ului)

### Pași de instalare

1. Clonați repository-ul (sau descărcați arhiva)
   ```
   git clone <repository-url>
   cd TWAOOS-programari-examene-backend-flask-python
   ```

2. Construiți și porniți containerele Docker
   ```
   docker-compose up -d
   ```

3. Aplicația va fi disponibilă la adresa `http://localhost:5000`

4. Pentru a opri aplicația
   ```
   docker-compose down
   ```

## Endpoints API

Documentația completă a API-ului este disponibilă la endpoint-ul `/api/docs` după pornirea aplicației.

### Principalele endpoint-uri

- `/api/auth` - Autentificare și gestionare conturi
- `/api/student` - Endpoint-uri pentru studenți (rezervări)
- `/api/secretary` - Endpoint-uri pentru secretariat (aprobare rezervări, gestionare săli)
- `/api/admin` - Endpoint-uri pentru administratori (gestionare utilizatori, setări)

## Funcționalități principale

### Integrare cu API-ul USV

Sistemul permite importul automat al sălilor și orarelor direct din sistemul USV prin intermediul API-ului oficial. Funcționalitățile includ:

- Import săli și detalii (capacitate, clădire, etc.)
- Import orar semestrial pentru toate cadrele didactice
- Sincronizare automată a datelor

### Notificări prin email

Sistemul trimite notificări automate prin email în următoarele situații:

- Notificare către secretariat la primirea unei noi cereri de rezervare
- Notificare către student la aprobarea/respingerea cererii
- Rapoarte zilnice către administratori

### Generare rapoarte

Sistemul poate genera rapoarte detaliate în format Excel despre:

- Rezervările din ziua curentă
- Statistici de utilizare a sălilor
- Istoricul rezervărilor

### Import orar din Excel

Pe lângă integrarea cu API-ul USV, sistemul permite și importul manual al orarelor din fișiere Excel sau CSV, oferind flexibilitate în gestionarea datelor.

## Configurarea bazei de date

Aplicația folosește PostgreSQL ca sistem de gestiune a bazei de date. Configurarea este realizată automat prin Docker Compose.

### Detalii configurare PostgreSQL

- **Versiune**: PostgreSQL 14
- **Nume bază de date**: `exam_scheduling`
- **Utilizator**: `postgres`
- **Parolă**: `postgres`
- **Port**: `5432`
- **Persistență date**: Volumul Docker `postgres_data`

### Modele de date principale

Baza de date include următoarele modele principale:

- **User**: Gestionează utilizatorii sistemului (studenți, secretariat, administratori)
- **Room**: Informații despre sălile disponibile (nume, capacitate, clădire, etaj)
- **Schedule**: Orarul săptămânal al sălilor (zi, interval orar, materie, profesor)
- **Reservation**: Cererile de rezervare a sălilor (utilizator, sală, dată, interval orar, scop)
- **Settings**: Setări instituționale (nume, adresă, semestru curent)

### Inițializare bază de date

La prima rulare, baza de date este inițializată automat cu date implicite:

- Un utilizator administrator (`admin@example.com` / `admin123`)
- Setări instituționale de bază

Pentru a inițializa manual baza de date, rulați:

```
python init_db.py
```

### Configurare în medii diferite

- **Development**: SQLite local sau PostgreSQL configurat prin variabila de mediu `DATABASE_URL`
- **Testing**: SQLite în memorie pentru teste
- **Production**: PostgreSQL configurat în docker-compose.yml

## Dezvoltare

Pentru a rula aplicația în modul de dezvoltare:

```
docker-compose -f docker-compose.dev.yml up
```

## Licență

Acest proiect este licențiat sub [MIT License](LICENSE).
