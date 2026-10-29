# Receipt Intelligence frontend

A React/Vite frontend intended to be served from the same origin as your FastAPI backend.

## Install and build
```bash
npm install
npm run build
```

## Development server
Run FastAPI on port 8000 and in another terminal run:
```bash
npm run dev
```
For Vite development mode, configure a proxy in `vite.config.js` if you want API calls to reach FastAPI:
```js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/auth": "http://127.0.0.1:8000", "/expenses": "http://127.0.0.1:8000", "/analytics": "http://127.0.0.1:8000" } }
});
```

## Expected backend routes
- `POST /auth/register` accepts `{ "email": "...", "password": "..." }`
- `POST /auth/login` accepts form-encoded `username` and `password`
- `GET /analytics/summary`
- `GET /analytics/insights`
- `GET /expenses/`
- `POST /expenses/upload` with form field `file`
- `POST /expenses/{receipt_id}/complete` with `{ "purchase_date": "YYYY-MM-DD" }`
- `PATCH /expenses/{expense_id}`
- `DELETE /expenses/{expense_id}`

The UI expects expense list items to include `id`, `description`, `category`, `purchase_date`, `quantity`, `unit_price`, `total_price`, and optionally `currency`, `merchant`, and `receipt_id`.

## Important
- Keep your existing FastAPI static-serving setup that serves `frontend/dist`.
- The frontend uses same-origin API paths (`/auth/...`, `/expenses/...`, `/analytics/...`).
- Check `AnalyticsSummary`, `ExpenseOut`, and `ReceiptComplete` schemas match the request/response shapes described above.
