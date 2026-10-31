# TableTurn

A restaurant waitlist for Kothari's, Baner: parties are quoted a wait, seated by size, and the tables turn over all
 evening. This folder is the finished project.

## What is here

| Part | What it does |
|---|---|
| Tables | 22 tables in three sections loaded once from `seed/tables.csv`; `GET /branches/{branch}/tables` filterable by section and state, state derived from the seating — no stored flag |
| Waitlist | `POST /waitlist` with real constraints; 422 for a malformed body, 400 party-too-big for a size no table could seat; `GET /parties/{id}` |
| Quote | The quote stamped at join and the real wait stamped at seating, both from an injected clock |
| Seating | `POST /seatings` with refusals — table-too-small, already-seated, table-not-cleared, and overtaking — raised in the service, mapped once |
| Turn | `POST /seatings/{id}/leave` and `/clear`: turn time is seated → left, the clear is one transaction, both idempotent by refusal |
| Events | An append-only event log per party (joined, quoted, seated, left, cleared); the database refuses UPDATE and DELETE |
| The API | Routers per resource, one error shape for every error, docs that list what each endpoint can answer |
| Rules | `tests/rules.csv` — the rule table under all three `SMALL_PARTY_UPGRADE` settings; `GET /settings` |
| The image | A Dockerfile; the app binds `HOST=0.0.0.0`, so the floor is reachable from the kitchen screen |
| Running it | Data on a volume, every setting from an env-file, `.dockerignore`, logs on stdout |

## Run it

The two commands:

```bash
docker build -t tableturn .
docker run -p 8080:8080 tableturn
```

For the till PC, run it with the database on a named volume and the settings from the env-file — copy
`.env.example` to `.env` first:

```bash
docker run -d --name tableturn -p 8080:8080 -v tableturn-data:/data --env-file .env tableturn
```

## How the image starts

The image starts the app with

```dockerfile
CMD ["sh", "-c", "exec uvicorn tableturn.app:app --host \"$HOST\" --port \"$PORT\""]
```

so `HOST` and `PORT` come from the environment: the image sets `HOST=0.0.0.0` and `PORT=8080`, and the env-file can
change them without a rebuild. `DATABASE_URL` is not baked into the image; the env-file points it at the volume.

Open `http://<till-pc-ip>:8080/` from the kitchen screen — the floor, the waitlist, one party, the rule book, the API
and the runtime, with a walkthrough. Docs at `/docs`, health at `/healthz`, logs with
`docker logs -f tableturn`.

The nightly power cut: `docker rm -f tableturn`, then the same `docker run` — every party and their quoted time
are still on the list, because the database lives on the `tableturn-data` volume. To change a rule, edit one line of
the env-file and run the container again; no rebuild:

```
DATABASE_URL=sqlite:////data/tableturn.db
DEFAULT_QUOTE_MINUTES=40
SMALL_PARTY_UPGRADE=when_nobody_larger_waits     # never | when_nobody_larger_waits | always
SEED_DIR=seed
HOST=0.0.0.0
PORT=8080
```

## Verified on this build

Docker is not installed in the build workspace, so image build, host-to-container networking, browser walkthrough, and the runtime transcript below still need to be recorded on a Docker machine. Do not treat example IDs or timestamps as a verified run.

- The Python test suite is run with `python -m pytest`.
- Run on the Docker machine: record date, Docker version, image tag, host port <port>, a named
  volume and a copy of `.env.example` as the env-file.
- After building, record the actual date, Docker version, image tag, port, image size and byte count here.
- Verify `GET /healthz` from the host and another container; verify `GET /branches/Baner/tables` returns 200 with 22 tables.
- Exercise join → seat → leave → clear and record the generated IDs and table numbers. Then `docker rm -f` and the same `docker run` on the same volume: `GET /parties/<first id>..<last id>`
  and the seated tables compared byte for byte before and after — unchanged.
- `DEFAULT_QUOTE_MINUTES=30` in a copy of the env-file, container re-run: `GET /settings` →
  `{"default_quote_minutes":30,…}`; a new party is quoted 30, the parties already on the list keep 40. `PORT=9000` in
  another copy (mapped `-p <port>:9000`): the app logs `ready host=0.0.0.0 port=9000` and answers — no rebuild.
- `docker logs`: one line per request (`request method=POST path=/waitlist status=201 request_id=…`) and one per
  event (`event kind=joined party_id=<id> seating_id=- branch=Baner`); no guest name or phone number appears.
- `docker diff <container>` shows only `A /data` (the volume mount point) — nothing written under `/app`.
- Check the image's pinned packages and confirm it contains no tests, local database, or bytecode cache.

## Run it locally

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
python -m uvicorn tableturn.app:app --host 127.0.0.1 --port 8080
python -m pytest            # each test on its own SQLite file with a clock it controls
```

## One party, door to bill

```bash
curl -s -X POST http://localhost:8080/waitlist -H 'content-type: application/json' -d '{"name":"Kulkarni","covers":6,"phone":"+919876543210"}'
# Example shape: {"party_id":"W001","name":"Kulkarni","covers":6,"position":1,"joined_at":"…","quoted_minutes":40,"quoted_at":"…"}   ← the quote
curl -s http://localhost:8080/parties/W001
# state waiting, quoted 40, the joined and quoted events
curl -s -X POST http://localhost:8080/seatings -H 'content-type: application/json' -d '{"party_id":"W001","table":"T20"}'
# Example shape: {"seating_id":"S001","party_id":"W001","table":"T20","seated_at":"…","waited_minutes":47}             ← the real wait
curl -s -X POST http://localhost:8080/seatings/S001/leave
# the table shows uncleared until Joseph wipes it
curl -s -X POST http://localhost:8080/seatings/S001/clear
# {"seating_id":"S001","table":"T20","turn_minutes":83,"cleared_at":"…"}
curl -s http://localhost:8080/parties/W001
# cleared; events joined → quoted → seated → left → cleared
```

Refusals to try: `{"covers":9}` → 400 party-too-big with `max_covers`; seat a six at `T11` → 409 table-too-small;
seat a seated party again → 409 already-seated; seat anyone at a table whose party has left → 409 table-not-cleared;
seat a two at a four-top while a four is waiting → 409 overtaking with `must_seat_first`.

## Conventions

- Every error is `application/problem+json`: `type, title, status, detail` plus the fields the ticket names — domain
  refusals, validation, an unknown path (404 `/errors/not-found`) or method (405 `/errors/method-not-allowed`), and the
  one 500 (`/errors/internal`, generic detail, a request id).
- Ids are opaque strings (`W031`, `S204`, `T09`); database integers never reach the wire or the logs. Timestamps are
  UTC with a Z.
- A party's size is `covers`; a table's capacity is `seats`. Minutes are whole numbers, rounded down.

<!-- learntube:start -->
---

[![tests](https://github.com/KUBENDHIRAN-V-B/tableturn-python/actions/workflows/tests.yml/badge.svg)](https://github.com/KUBENDHIRAN-V-B/tableturn-python/actions/workflows/tests.yml)

### Progress

- [x] Ticket 1 · The floor, as something you can look at
- [x] Ticket 2 · A party joins the list
- [x] Ticket 3 · The wait you quote, and the wait they actually have
- [x] Ticket 4 · Three ways to say no
- [x] Ticket 5 · The table turns
- [x] Ticket 6 · A board nobody can wipe
- [x] Ticket 7 · One file becomes an app
- [x] Ticket 8 · The rule table, and then the rule changes
- [x] Ticket 9 · It runs on the machine by the till
- [x] Ticket 10 · It survives the nightly power cut

Built by KUBENDHIRAN V B on [LearnTube Guided Projects](https://guidedprojects.learntube.ai).
<!-- learntube:end -->
