# Open Inference: notes for AI agents

Read [docs/one-pager.md](docs/one-pager.md) first. It is Caesey's plan in his own words and wins over every other doc here. Lines labelled `[AI suggestion]` or `[AI research]` are not his decisions.

## Rules
- **Don't change his idea.** Make narrow, additive changes. His latest instruction wins.
- **Free only.** No paid services, APIs, GPUs or cloud resources without his say-so. Build locally first.
- **No GPU commitments until someone is paying** (his rule).
- **Numbers must be honest and traceable.** Every figure gets a source URL and the date it was checked. Keep source facts, calculated results, interpretation and unknowns separate. Never fill a gap with a guess presented as data.
- **Be exact about status.** Say what is mocked, built, and verified live.
- **Nothing goes public or to a git remote without his say-so.** This repo is local only for now.
- **Secrets:** never commit `.env*` files or keys. `legacy/coral` had a `.env.local`; it is not copied.
- **Money is AUD** unless a source is in USD, in which case keep the USD figure, the rate used and its date.
- Caesey is in Brisbane (UTC+10, no daylight saving). Store timestamps in UTC.

## Context
- His wider AI memory is available through the `caesey-memory` MCP tools (`get_memory('topics/open-weights')`, `get_memory('buyers')`, `search_history(...)`). Use it for history; keep the build here.
- `legacy/` is reference only. Don't build on it without asking.
