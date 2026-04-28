# Playto Payout Engine

Cross-border payment payout system for Indian merchants. Built as the Playto Founding Engineer Challenge 2026.

## What it does
Merchants accumulate balance from international customer payments and can withdraw to their Indian bank accounts. The system handles the hardest parts: concurrency, idempotency, and money integrity.

## Tech Stack
- **Backend:** Django 6.0 + Django REST Framework
- **Frontend:** React + Vite
- **Database:** PostgreSQL
- **Background Jobs:** Django-Q2

## Setup Instructions

### Prerequisites
- Python 3.10+
- PostgreSQL 16
- Node.js 18+

### Backend Setup
```bash
git clone https://github.com/Harshitaraj0210/playto-payout.git
cd playto-payout
python -m venv venv
venv\Scripts\activate
pip install django djangorestframework psycopg2-binary django-q2 django-cors-headers python-dotenv
```

Create `.env` file:
```
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=playto_payout
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

```bash
python manage.py migrate
python payout/seed.py
python manage.py runserver
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`

### Run Tests
```bash
python manage.py test payout --verbosity=2
```

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/v1/merchants/ | List all merchants |
| GET | /api/v1/merchants/:id/ | Merchant detail with balance |
| POST | /api/v1/merchants/:id/payouts/request/ | Request payout |
| GET | /api/v1/merchants/:id/payouts/ | Payout history |
| GET | /api/v1/payouts/:id/ | Payout detail |

## Key Design Decisions

**Money Integrity:** All amounts stored as BigInteger in paise. Balance always derived from SUM of ledger entries, never stored as a column.

**Concurrency:** Uses PostgreSQL SELECT FOR UPDATE to lock merchant row during payout creation. Prevents two simultaneous requests from overdrawing balance.

**Idempotency:** Idempotency-Key header scoped per merchant with unique_together DB constraint as safety net.

**State Machine:** Legal transitions only: pending → processing → completed/failed. Failed payouts atomically return funds in same transaction.