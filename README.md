# ChatLens

**Your conversations, rediscovered.** A privacy-first, self-hosted application for importing conversations, exploring deterministic analytics and optional Gemini insights, and making shareable Chat Wrap videos and PDF keepsakes. Gemini can be enabled once per conversation at upload. There are no embeddings, vector databases, authentication, or cloud deployment.

## Run locally with Docker

Install Docker with Compose, start Docker, and run from this repository:

```sh
cp .env.example .env
docker compose up --build
```

- App: http://localhost:3000
- API: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs

The backend runs Alembic migrations before serving. PostgreSQL has a persistent named volume. Both published HTTP ports bind to loopback; PostgreSQL is accessible only inside the Compose network. No authentication is included: keep this installation on a trusted local machine. Stop with `docker compose down`. The database survives restarts; `docker compose down -v` deliberately removes **all** stored data.

Open **Import**, select `examples/whatsapp_group.txt`, confirm WhatsApp, inspect the preview, choose yourself, and import. Open Report, Statistics, Messages, and Participants. Use the trash icon to delete the conversation and its associated data.

## Features

- TXT, JSON, SQLite, and protected ZIP uploads; source detection with manual override.
- Direct and group conversations from four platforms, normalized into one schema.
- Multi-conversation selection for account exports and Messages databases.
- Preview title, participants, dates, and message count before persistence; choose the current user and merge export aliases such as `You` with their displayed name.
- Paginated message browser, literal text search, sender/type/date filters, reply and reaction indicators.
- Daily/weekly/monthly activity, participant share, hourly and weekday charts using Recharts.
- Participant statistics, session initiation, response-time percentiles, measurable interaction matrices, reactions where exposed.
- Participant drilldown with activity, message types, active hours, and basic metrics.
- Light/dark/system themes, responsive layout, browser-local preferences.
- Ranked discoveries, micro-insights, participant style cards, pair dynamics, superlatives, activity eras, and turning points.
- Fun (default), Balanced, and Analytical tones with identical underlying measurements.
- Clickable source evidence and nearby messages; local PNG finding cards.
- Durable server-side Gemini analysis with upload-time consent, resumable passages, contextual covers, story timelines and evidence-based follow-up questions.
- Cascading deletion of messages, participants, reports and queued jobs; no telemetry.

### Screenshots

- [Placeholder: conversation overview, light theme]
- [Placeholder: import preview]
- [Placeholder: messages and participant drilldown, dark theme]

## Architecture and layout

```text
chatlens/                    # repository root (may be named chat-analyzer locally)
├── frontend/                # Next.js App Router, TypeScript, Tailwind, shadcn/ui primitives, Recharts
│   └── src/{app,components,lib}/
├── backend/
│   ├── app/
│   │   ├── api/             # import and conversation endpoints
│   │   ├── models/          # SQLAlchemy models, engine and sessions
│   │   ├── schemas/         # normalized Pydantic contracts
│   │   ├── parsers/         # platform adapters and detection registry
│   │   ├── analytics/       # deterministic calculation modules
│   │   ├── insights/        # ranked pattern discovery and report assembly
│   │   ├── synthesis/       # optional Gemini, sampling, prompts, validation
│   │   ├── services/        # batched transactional import persistence
│   │   └── utils/           # protected ZIP handling and Unicode repair
│   └── alembic/             # versioned database migrations
├── tests/                   # synthetic parser, analytics, API and security fixtures
├── examples/                # fictional chats only
├── docker-compose.yml
├── .env.example
└── LICENSE                  # MIT
```

Browser requests use same-origin `/api` routes. Next.js proxies to `http://backend:8000` inside Docker, or `http://127.0.0.1:8000` in development. No public backend hostname is baked into browser JavaScript. If building for another server, set `BACKEND_URL` when running `next build` because Next.js rewrites are compiled at build time.

`ALLOWED_ORIGINS` controls browser origins accepted by the API and defaults to `http://localhost:3000`. Keep the default for the local Compose setup; set it to the exact HTTPS origin only when placing ChatLens behind a trusted reverse proxy.

FastAPI parses temporary local files into Pydantic models, then writes normalized conversations, participants, and messages to PostgreSQL using batches of 2,000 messages in one transaction. JSONB holds mentions, reactions, attachments, and uncommon metadata. Replies preserve source message IDs and resolve within their conversation. DB indexes cover conversation, timestamp, sender, type, and ordered pagination. Foreign keys cascade deletion. No original media bytes are retained or served.

Parser `parse()` returns a list of normalized conversations because a single Telegram/Meta archive or iMessage database can contain multiple conversations. Each import saves the selected conversation. Detection and preview do not persist messages. Each request removes its temporary files, including failed parses; preview/save re-upload and re-parse the selected file, avoiding abandoned staging data.

## Supported exports

| Platform | Formats | Scope |
| --- | --- | --- |
| WhatsApp | Android/iOS `.txt`, or ZIP containing TXT | 12/24-hour times, optional seconds, multiline Unicode text, direct/group, common English system/media/call/deletion markers |
| Telegram | Desktop JSON `result.json`, one chat or full account `chats.list` | Personal/group/supergroup, fragments, replies, forwarded/edited metadata, media, reactions and service events |
| Instagram | Meta message JSON, or ZIP with per-thread `message_N.json` files | Merge each folder chronologically, DMs/groups, Unicode repair, reactions, shares, media references, call duration and unsent flags |
| iMessage | Consistent macOS Messages `chat.db` snapshot (`.db`, `.sqlite`, `.sqlite3`) | All chats, handles, names, plain text, seconds/nanoseconds Apple timestamps and attachment metadata |

### WhatsApp export

In WhatsApp, open a chat's menu or contact/group info and choose **Export chat**. Export without media for a smaller file; including media also works, but media bytes are skipped. Upload the TXT or ZIP. Export menu wording depends on OS/version. WhatsApp may limit how much history it exports.

Ambiguous numeric dates default to day/month/year. Choose month/day/year when appropriate in the import wizard. WhatsApp imports require you to choose the timezone used by the exporting phone (an IANA name such as Asia/Kolkata). ChatLens converts that wall time to UTC for storage and uses the chosen timezone for report habits and activity charts. Repeated daylight-saving hours use the first occurrence with a warning; nonexistent clock-gap times require correcting the timezone. Existing imports are not shifted retroactively. A two-person group without group system events can look like a direct chat; override the type in preview.

### Telegram export

Use Telegram Desktop's chat menu → **Export chat history**, or Settings → Advanced → **Export Telegram data**. Select **JSON**, then upload `result.json` or a ZIP containing it. HTML exports are not supported in Phase 1. Reactions given are counted only for actors included in the export; aggregate reaction totals may be larger.

### Instagram export

In Meta Accounts Center, request a download of your information with **Messages** and **JSON** selected. Find `messages/inbox/<conversation>/message_1.json`. Upload a single JSON file or ZIP the relevant conversation folder to include every `message_N.json` segment. A ZIP containing multiple thread folders offers a conversation selector. Photos and videos remain metadata references. Safe, reversible Latin-1/UTF-8 repair handles common Meta text encoding issues.

### iMessage import

The source is usually `~/Library/Messages/chat.db`. macOS may require Full Disk Access for your terminal. Use a consistent SQLite backup rather than copying a live database while Messages is writing:

```sh
sqlite3 -readonly "$HOME/Library/Messages/chat.db" ".backup '/tmp/chatlens-messages.db'"
```

Upload `/tmp/chatlens-messages.db` and choose a conversation. This command reads the source and writes a separate snapshot. ChatLens itself opens uploads in read-only, immutable mode and does not modify source databases. A bare copy missing live WAL data may omit recent messages. Do not upload WAL/SHM sidecars in lieu of a proper backup.

Recent macOS messages whose text exists only in `attributedBody` are marked **body unavailable**. Binary typedstream extraction, attachment playback, tapback association and iMessage reply decoding are not supported. Available messages and attachment metadata still import.

## Analytics definitions

- All imported records count toward total messages and activity, including system events. Participant share uses that total, so shares can sum to less than 100%.
- Text length is Python Unicode code-point count of text messages, not bytes or grapheme clusters. Media means image/video/audio/file/sticker; calls are separate.
- Active day means a calendar day with at least one imported message. Messages/day divides by active days, not elapsed days.
- Weeks follow ISO week numbering. New WhatsApp activity charts use the selected source timezone; older imports without one retain UTC wall time.
- A session breaks when the gap **exceeds** the configured threshold (4 hours by default). Session length is elapsed seconds, including zero for a single message. System messages can belong to a session, but the first non-system participant initiates it.
- Direct responses measure the gap from the last message in one sender's turn to the first message from the next sender. System messages are skipped. Gaps above the session threshold are excluded. Percentiles use linear interpolation.
- Group response times use explicit replies to another sender within the threshold. Mentions identify interactions but do not, by themselves, establish which prior message was answered. Missing reliable responses remain unavailable.
- Interaction matrix rows give interactions and columns receive them. Each explicit reply, resolved mention, and identifiable reaction is a separate measurable signal; none indicates relationship strength. Unknown actors are excluded.
- Reactions are unavailable (`null`) for WhatsApp and iMessage adapters. Supported JSON formats return zero when none were exported.

The settings page stores session gap, display format, and theme per browser. `SESSION_GAP_HOURS` configures the API default; the UI defaults to four hours until changed in Settings.

## Development (uv and fnm)

Use Python 3.12+ and Node 22. Start PostgreSQL, then run:

```sh
# One time
uv python install 3.12
fnm install 22

# Backend; provide a PostgreSQL URL reachable from your host
cd backend
uv sync
export DATABASE_URL='postgresql+psycopg://chatlens:chatlens@localhost:5432/chatlens'
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Compose does not expose PostgreSQL to the host by default. For development, use a separate local PostgreSQL instance or an explicit local-only port override. Alternatively, run backend + PostgreSQL with `docker compose up --build backend` and develop only the frontend locally:

```sh
cd frontend
fnm exec --using=22 npm ci
fnm exec --using=22 npm run dev
```

The bundled shadcn/ui Button source uses Radix Slot, class-variance-authority and the local theme tokens. There are no network font/image dependencies. Next.js telemetry is disabled in scripts and Docker.

## Tests and validation

```sh
cd backend
uv run pytest ../tests -q
uv run ruff check app ../tests --select F
# Back at repository root, or from another terminal:
cd frontend
fnm exec --using=22 npm run lint
fnm exec --using=22 npm run typecheck
fnm exec --using=22 npm run build
fnm exec --using=22 node --experimental-strip-types --test tests/curation.test.mjs
```

Unit/API tests default to an isolated temporary SQLite database with foreign keys enabled, for fast self-contained checks. Production and Docker integration use PostgreSQL. The API acceptance test verifies import, preview, identity selection, paginated messages, literal search, filters, analytics, and cascading deletion. Synthetic iMessage databases are generated at test time. Never commit personal exports.

## Repository hygiene

The repository intentionally ignores local `.env` variants, uploads, database files, temporary exports, caches, logs, editor files, and machine-specific verification notes. `.env.example` remains tracked as the safe configuration template. Do not add exported conversations, generated wraps, API keys, or a real `chat.db` to commits.

GitHub Actions runs the backend parser/API suite plus frontend linting, type checking, and curation tests on every push and pull request. Before the first push, review the staged file list and configure your remote:

```sh
git status
git add README.md .env.example .gitignore backend frontend tests examples docker-compose.yml .github
git diff --cached --check
git commit -m "Initial ChatLens release"
git remote add origin <your-repository-url>
git push -u origin main
```

## Privacy and upload security

Imports, statistics, and measured reports stay on your host. No telemetry, third-party trackers, or external font/image resources are used. **Enabling Gemini sends participant names and original message passages to Google, automatically after upload.** The queued analysis visits the full eligible history in bounded calls, with individual text capped at 2,000 characters. Follow-up questions also send retrieved messages. Google’s API terms/data handling apply. Dependency installation and Docker image downloads require internet access; local reports do not. Data and any UI-configured API key are stored unencrypted in your local PostgreSQL volume, protected by your machine’s controls. Deletion removes live database rows; it does not securely erase old backups or storage blocks.

Uploads default to 100 MB, ZIP expansion to 500 MB and 10,000 entries. Configure limits with `.env`. Archive validation rejects absolute/traversal paths, symlinks, encrypted members, suspicious compression ratios, and oversized expansions before writing selected TXT/JSON/DB files. Unsupported media/nested ZIP files are skipped. Filenames are sanitized, upload contents are never executed, and UI text is React-escaped. Requests have a body-size guard. SQLite reads use query-only mode and a VM-work budget. Serve only on trusted local networks in Phase 1.

## Known limitations and edge cases

- Local report generation loads one conversation into backend memory once per queued job; message browsing is paginated. PostgreSQL stores analysis checkpoints and the local report. Large imports still parse synchronously before enqueueing analysis. A dense interaction matrix scales with participant count squared. Two-year Gemini runs can take hours and many paid calls; full passage coverage is not a guarantee of complete semantic recall.
- WhatsApp date order and timezone can be ambiguous. Common English export placeholders/system events are recognized; other localized export markers may need parser additions. Message contents can be in any language.
- Telegram HTML is not supported. Instagram formats vary by export version. iMessage attributedBody-only text may be unavailable; attachment metadata does not include playable media.
- Media content, audio transcripts and deleted message bodies cannot be inferred from export placeholders.
- Group response times and pair interactions require explicit reply/mention/reaction signals. Exported data often lacks them.
- Long sessions can span model passages. Overlap helps preserve local context but cannot guarantee complete cross-session understanding. Era narration is interpretive, not a measured emotional diagnosis.
- This remains a localhost app without authentication. Use one worker; distributed scheduling, secret encryption, permanent chatbot history and full-text semantic retrieval are not implemented.

## Roadmap

**Phase 2:** optional LLM analysis and evidence-backed reports. Start from the normalized schema and stable message IDs; keep deterministic analytics independent and require explicit provider/privacy configuration. The optional Gemini evidence pipeline and discovery report are implemented; future work can deepen semantic validation and sampling coverage.

**Phase 3:** expanded export customization, advanced UX and production hardening, including performance improvements, additional parser variants and deployment safeguards. Local MP4 and PDF Chat Wrap exports are already available.

## Discovery reports

The **Report** tab is a personal scrapbook: a warm illustrated cover, colorful cards, emoji stickers and actual conversation bubbles. Personal moments lead; measured habits follow. Gemini looks for acts of care, funny exchanges, shared milestones, rituals, tension and supported repair. It does not assume romance or manufacture fights and resolutions. Findings have stable families and a single home: top insights, “Things you probably never noticed”, participant cards, eras, pairs, superlatives, recurring language, or deeper observations. Raw analytics remain in **Statistics**.

Measured discovery spans session starts/ends, 8-hour revivals, long same-sender runs, rapid bursts, response-time contrasts, full-cast days, calendar-normalized weekend habits, daily streaks, ten-minute peaks, one-word/long-message rates, question marks, URLs, emoji-like symbols, recurring phrases, literal word/length associations, explicit pairs, reactions, and complete-month shifts. Candidate interestingness combines magnitude, support, and multiple signals; it is an internal editorial ranking, not a scientific score.

Tone changes presentation without changing measurements. Fun is playful; Balanced uses plainer titles; Analytical exposes the measured facts and methods more directly. New WhatsApp reports use the chat timezone chosen at import; other reports use the timezone preference. Evidence drawers label timestamps in UTC. Older WhatsApp imports without a saved source timezone retain UTC wall time.

Moment highlights are curated for substance and grouped into categories such as conflict, repair, romance, intimacy, friendship, ideas, vulnerability, humor, support and milestones. Only categories with selected findings appear. At most 24 AI moments (four per category) qualify for the main report, with six initially expanded. Lesser findings remain available for final synthesis. Existing AI-enabled reports can be re-curated from saved findings without re-reading all messages.

Group reply networks use explicit resolved reply links only. Edge weights show reply counts in both directions, with original-message evidence. Exports without reliable reply links omit the network; message proximity, mentions and reactions are not used to infer closeness.

Reports aim for 15–30 direct-chat or 20–50 group findings when supported. Sparse or uniform data can yield fewer. A two-day chat cannot honestly have several long-term eras. Missing reply links, partial months, ties, and unidentified reaction actors suppress claims that would otherwise be unreliable. No “ignored”, silent-reading, psychological diagnosis, or friendship inference is fabricated. Topic switching, motives and semantic subgroup detection are not inferred from adjacency.

The fictional `examples/telegram_story_group.json` contains 2,442 messages over six months, with explicit reply/reaction signals. It exercises the richer report acceptance criteria. Regenerate with `uv run --project backend python examples/generate_story.py`. No real conversation data is included.

### Optional Gemini setup

Add the following to the **root `.env`** (never a `NEXT_PUBLIC_` variable, and never commit the key):

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

The default shown here passed live synthetic testing. Choose a Gemini model available to your account that supports structured JSON output; availability varies by model and account. Then recreate the backend so Compose passes the new settings:

```sh
docker compose up -d --build backend worker
```

For backend development outside Docker, export these variables into the backend process or use `uv run --env-file ../.env uvicorn app.main:app --reload --port 8000` from `backend/`.

At upload, check **Automatically analyze with Gemini** to consent once for this conversation. Saving the chat immediately enqueues local analytics and Gemini analysis. Closing the browser has no effect on processing. Leave unchecked for local-only analytics. Existing chats can enable Gemini once in their report. Opening a report or changing tabs never starts another paid analysis. The API key is never returned by settings endpoints; source archives and media bytes are not transmitted.

The PostgreSQL-backed worker visits all participant messages chronologically, with up to eight messages of overlap between passages. It preserves original scripts and code-switching; there is no English keyword filtering, translation or stop-word removal. A conservative UTF-8 byte budget bounds each request and reserves space for instructions. Individual message text is limited to 2,000 characters and truncations are counted. Media placeholders are types, not authored text. A short initial call samples beginning/middle/end to make a provisional cover; the final cover and eras are grounded in validated passage findings. Monthly/category quotas retain diverse moments without allowing one busy period to dominate.

Every AI moment cites at least two supplied message IDs and includes original quotations linked to their actual speakers. Tension and repair require at least three source messages within a contiguous passage. There is no English word-count requirement: CJK text, Hindi, Urdu, transliterated/code-switched messages and emoji are valid source evidence. Unknown citations, nonexistent quoted text, numerical narration outside source quotations, duplicate families, close textual restatements and insulting diagnostic labels are rejected. Figures stay in deterministic cards; Gemini adds contextual prose and can link those measured facts. This is **reference validation, not a proof that an interpretation is correct**. Natural-language paraphrases can still overlap, and the bounded sample cannot establish whole-chat topic prevalence. AI text is rendered as escaped text, labelled “A reading”, and links to source evidence. The model has no tools and is instructed to treat conversation content as untrusted data rather than commands.

Analysis state, local report, passage cursor, token counts and accepted findings live in PostgreSQL. Each successful passage is checkpointed. Temporary provider failures and HTTP 429/5xx retry with exponential backoff (respecting numeric Retry-After); exhausted retries become resumable failures. Output-limit failures shrink the next passage. Expired ten-minute leases recover work after a crashed worker. A crash after a provider response but before its database checkpoint may repeat that one paid call. Exactly-once external billing is not guaranteed. Use one worker per installation to preserve the configured pacing. Deleting a conversation cascades to jobs and results; an already in-flight API request cannot be recalled, but its result is discarded.

API additions:

- `GET /api/analysis/config` — provider readiness, no secret values.
- `GET /api/conversations/{id}/report?tone=fun&session_gap=4&timezone=UTC` — local report plus matching cached synthesis.
- `GET /api/conversations/{id}/report/packet` — exact outbound evidence packet preview.
- `POST /api/conversations/{id}/analysis` — enqueue/resume (`consent: true` to enable AI; `refresh: true` to rebuild a finished report).
- `GET /api/conversations/{id}/analysis` — durable progress, next retry time and sanitized failure.
- `POST /api/conversations/{id}/ask` — question, optional finding ID, up to six prior turns.
- `GET/PATCH /api/settings/ai` — server model/key/pacing/token settings.
- Legacy `/report/synthesize` and `/report/packet` remain for compatibility; the UI uses the durable queue.
- `GET /api/conversations/{id}/evidence?ids=...` — up to 20 messages scoped to the conversation.
- `GET /api/conversations/{id}/messages/{message_id}/context` — three nearby messages on each side.

Source references for the integration: [Gemini structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output?hl=en), [Gemini generateContent API](https://ai.google.dev/api/generate-content). Live provider testing requires your configured key; mocked tests never transmit chat data.


### Worker, settings and question retrieval

Docker Compose now runs **frontend, backend, postgres and worker** (no Redis). In development run `uv run --project backend python -m app.services.jobs` with `PYTHONPATH=backend` and the same `DATABASE_URL` and Gemini environment as the API. The API applies migrations before the Compose worker starts.

Settings → **AI & LLM** lets you configure the model (default `gemini-3.5-flash-lite`), API key, pacing, retries, passage size and token budgets. Keys saved here override `.env` and are stored in the local database, not browser storage; protect database backups accordingly. Environment defaults: `GEMINI_INTERVAL_SECONDS=2`, `GEMINI_MAX_RETRIES=8`, `GEMINI_INPUT_BUDGET=240000` (conservative input bytes), `GEMINI_OUTPUT_TOKENS=8192`, `GEMINI_CHUNK_MESSAGES=2000`. Choose limits supported by your model and quota. The worker honors settings on its next call. Total-history analysis has no arbitrary five-call cap.

Card and report questions use a bounded Gemini search-plan call, conversation-scoped literal SQL search, nearby exchanges, then an evidence-based answer. No embeddings or vector database is needed. Searches can miss paraphrases, cross-language matches, or old context; absence of retrieved evidence is never proof that an event did not happen. A follow-up can make two paid calls; these are separate from the queued report and can encounter provider rate limits. Question history is ephemeral to the open dialog.

Contextual analysis can identify concerning statements, boundary violations, threats, insults, contradictions and repair, with original-message evidence. It cannot prove hidden motives, intentional lying or a clinical diagnosis. Three cited messages from one contiguous session are required for tension/repair findings. Covers and era summaries are interpretations of sampled/validated readings; reference validation does not prove semantic accuracy.

[Thinking Orbs](https://github.com/Jakubantalik/thinking-orbs) provides the loading animation (MIT, Jakub Antalik). UI animations respect reduced-motion preferences. Current-user bubbles align right in messages, quote cards and evidence; everyone else aligns left.

### Chat Wrap exports

Open a report and choose **Make a Chat Wrap**. Pick a peach, lilac, or mint palette,
edit the title, select highlights, and review every page. Participant aliases are
on by default; these replace display names, not every identifying detail. Selected
AI findings may contain message excerpts, so review before sharing.

- **Video:** up to eight highlights plus opening/closing pages and an optional
  final perspective. Portrait 720×1280 MP4 (H.264, 24fps), with gentle movement and
  fades. Choose 4, 6, or 10 seconds per page. Videos are silent; add music in your
  sharing app. Download the file and share it yourself; ChatLens does not post it.
- **PDF:** select individual highlights or all visible report highlights (up to
  fifty). The portrait PDF contains the selected content, with AI readings labelled.
- Exports use saved findings and make no Gemini calls. The server runs Chromium
  offline with escaped content and blocked network requests, then FFmpeg for video.
  One render runs at a time. Temporary files are removed after download or failure.
  Keep the export window open until the download is ready; interrupted exports
  are not persisted or resumable. Existing analysis is unaffected.

Docker installs Chromium, FFmpeg, and multilingual Noto fonts automatically. The
first image build is larger. For native development, run `uv sync`, then
`uv run playwright install chromium --only-shell` in `backend/`, and install
FFmpeg (`brew install ffmpeg` on macOS). Install Noto fonts for multilingual output.
