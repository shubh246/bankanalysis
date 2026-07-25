# Bank Statement Analysis

Upload a PDF or CSV bank statement, search ("trail") for transactions by amount, and visualize
the fund flow between your account and counterparties (with names extracted from UPI/NEFT/IMPS/RTGS
narrations).

## Structure

- `backend/` — FastAPI + SQLite. Parses statements, stores transactions, serves search & fund-flow APIs.
- `frontend/` — React + Vite. Upload UI, amount-trail search, fund-flow graph (React Flow).

## Running locally

### Backend

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API runs at `http://127.0.0.1:8000` (docs at `/docs`). Data is stored in `backend/data/bankstatements.db`.

### Frontend

```
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:5173`.

## How it works

- **Upload**: CSV is parsed with pandas (flexible column detection for Date/Description/Debit/Credit/Balance).
  PDF is parsed with pdfplumber's table extraction, then normalized the same way.
- **Name extraction**: narrations like `UPI/name@bank/...`, `NEFT-ref-NAME-IFSC`, `IMPS/ref/NAME/IFSC`,
  `RTGS-ref-NAME-IFSC` are parsed with regex to pull out the counterparty name; ATM/cheque transactions
  are labeled accordingly; anything else falls back to the raw description.
- **Trail**: the Trail & Fund Flow tab searches transactions by exact amount (with optional tolerance),
  name, direction, statement, and date range.
- **Fund flow**: for the current search filter, transactions are aggregated into a graph — a central
  "My Account" node connected to each counterparty, with edges labeled by total amount and transaction count,
  colored green (money in) / red (money out).
