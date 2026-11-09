# CampusAsk web

Next.js App Router UI for CampusAsk.

```bash
npm install
cp .env.example .env.local
npm run dev
```

Requires the FastAPI service (`uvicorn api.main:app`) and `NEXT_PUBLIC_API_URL`.

## Vercel

On team [https://vercel.com/sajithakonda0909-7027](https://vercel.com/sajithakonda0909-7027): Import `AI_Project`, set **Root Directory** to `web`, and set `NEXT_PUBLIC_API_URL` to your API base URL (local API is fine for demos).
