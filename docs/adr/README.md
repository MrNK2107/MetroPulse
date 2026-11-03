# Architecture decision records

Each record states one decision: its status, the context that forced it, the decision, and what follows
from it. Records are short (under 300 words) and are not edited after acceptance; a changed decision gets
a new record that supersedes the old one.

| No. | Decision | Status |
|-----|----------|--------|
| [0001](0001-browser-first-core-loop.md) | The core loop is deterministic TypeScript that runs in the browser | Accepted |
| [0002](0002-client-side-data-import.md) | A user's own city data is imported client-side and never uploaded | Accepted |
| [0003](0003-remove-the-simulator.md) | The retired city simulator is removed from the repository | Accepted |
| [0004](0004-public-api-in-the-nextjs-app.md) | The public JSON API lives in the Next.js app as route handlers | Accepted |
