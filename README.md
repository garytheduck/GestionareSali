# Sistem de Programare Examene - Backend

Aplicație backend pentru gestionarea programării examenelor și rezervării sălilor din cadrul facultății.

## Descriere

Acest proiect reprezintă partea de backend pentru o aplicație de gestionare a rezervărilor sălilor de examen din cadrul unei universități. Sistemul permite studenților să verifice disponibilitatea sălilor și să trimită cereri de rezervare, secretariatului să aprobe sau să respingă cererile, iar administratorilor să gestioneze orarul și configurația sistemului.

## Tehnologii utilizate

- Python 3.9+
- Flask (framework web)
- PostgreSQL (bază de date)
- Docker & Docker Compose (containerizare)
- JWT pentru autentificare
- SQLAlchemy ORM
- Flask-Migrate pentru migrări de bază de date
- Alembic pentru versionarea schemei bazei de date

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

## Dezvoltare

Pentru a rula aplicația în modul de dezvoltare:

```
docker-compose -f docker-compose.dev.yml up
```

## Licență

Acest proiect este licențiat sub [MIT License](LICENSE).
