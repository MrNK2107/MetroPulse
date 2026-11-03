# Needs input from the owner

Decisions the builder made provisionally, or could not make, during the 2.0 work. Each needs the
owner's confirmation or a replacement. Remove an entry once it is settled.

1. **Licence.** The repository is now licensed under Apache-2.0 (`LICENSE`, copyright "2026 MetroPulse
   contributors"), chosen for its explicit patent grant and because it permits commercial use and a
   future paid tier. Confirm, or pick another licence (MIT, a source-available licence, or proprietary)
   before the repository is made public.
2. **Pricing wording.** Any pricing or "paid features" wording on the landing page and in the docs is
   placeholder copy (workspaces as the first paid feature). Confirm the wording, or say what to show.
3. **Terms of service.** Not written. A `/privacy` page states that imported data never leaves the
   browser, but there are no terms of service or acceptable-use terms for the site or the public API.
   These need the owner, and probably a lawyer.
4. **Security contact.** `SECURITY.md` names `security@metropulse.in`, which is a placeholder. Confirm a
   monitored address (and that the domain is owned), or replace it.
5. **`INGEST_TOKEN` deployment policy.** `POST /api/ingest` is open when `INGEST_TOKEN` is unset. Decide
   whether production deployments must set it (recommended for any publicly reachable backend), and
   whether the backend should refuse to start without it outside development.
