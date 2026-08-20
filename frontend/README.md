v0.1 policymaker dashboard for CivicPrior.

## Data contract

The UI does **not** hard-code portfolios. It reads a static JSON export of the
frozen Python decision pipeline:

1. `python3 src/pipeline/export_dashboard.py` (from repo root)
2. Writes `data/dashboard-v01.json` and copies it to
   `frontend/public/data/dashboard-v01.json`
3. The Next.js app fetches `/data/dashboard-v01.json`

Regenerate the JSON whenever pipeline inputs change. Do not edit portfolio
results by hand in React components.

## Run

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000
