<div align="center">
  <img src="frontend/public/tag-image.jpeg" alt="TopoScribe AI — Agentic AI for Network Topology Design & Configuration" width="75%" />
</div>

<br />

Multi-agent system that turns a natural-language campus description into a
network topology, Cisco IOS-style configuration, a reachability check, and an
exportable report.

The UI is a Next.js app. Agents run in a FastAPI + LangGraph backend.

## How it works

1. **Planning** (OpenAI) — extracts departments, devices, and protocols, or asks a clarifying question.
2. **Topology** (Groq first; OpenAI if the quality gate rejects the draft) — builds nodes and links.
3. **Configuration** (deterministic Python) — addressing and Cisco CLI.
4. **Validation** (deterministic Python) — retries configuration when checks fail.

## Repository layout

```
backend/     FastAPI app, LangGraph workflow, agents, tests, evaluation logs
frontend/    Next.js UI (canvas, chat, saved designs)
```

## Requirements

| Mandatory | Minimum | Recommend |
| --------- | ------- | --------- |
| Python | 3.11 | >= 3.11 |
| Node.js | 18 | >= 20 |
| Groq API key | — | required for topology (attempt 0) |
| OpenAI API key | — | required for planning and topology escalation |
| PostgreSQL (`DATABASE_URL`) | — | required for saved designs |

| Optional | Minimum | Recommend |
| -------- | ------- | --------- |
| LangWatch | — | tracing / evaluation |
| Docker | — | local compose stack |

## Setup

**Backend**

```bash
cd backend
cp .env.example .env   # fill in the values; never commit .env
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend** (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The UI calls
`http://localhost:8000` unless you set `NEXT_PUBLIC_API_URL`.

## Environment

Copy `backend/.env.example`. Required names:

- `GROQ_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_PLANNING_MODEL` (default in code: `gpt-5.5`)
- `OPENAI_ESCALATION_MODEL` (default in code: `gpt-5.5`)
- `LANGWATCH_API_KEY` / `LANGWATCH_PROJECT_ID` (optional)
- `DATABASE_URL`

Default Groq topology model: `qwen/qwen3.8-27b`.

## Evaluation data

`backend/data/` holds scenario run logs, a time survey, notebooks, and
`Findings/findings.md`. Those files are research artifacts, not runtime config.

## License

MIT. See [LICENSE](LICENSE).
