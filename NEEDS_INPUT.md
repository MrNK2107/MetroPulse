# Decisions for the owner

Everything below has a working default in the repository. Nothing blocks a deploy; each item is a
default to confirm or change.

| Decision | Default in place | Where |
|---|---|---|
| Licence | Apache-2.0 | `LICENSE` |
| Pricing wording | Explorer free, Desk ₹3.5 lakh/city/yr, Authority ₹20–40 lakh, API usage-based | landing page, `docs/PRODUCT.md` |
| Terms of use | Plain-language draft, marked as not yet reviewed by counsel | `/terms` |
| Security contact | GitHub private vulnerability reporting | `SECURITY.md` |
| `INGEST_TOKEN` in deployments | Off (open ingest), as before | `backend/.env.example` |
| Production domain | `NEXT_PUBLIC_SITE_URL`, falls back to localhost | `frontend/.env.example` |
| Cloud workspace | Off until the Supabase env values are set; migration 010 ready | `frontend/.env.example`, `supabase/migrations/010_scenarios.sql` |
