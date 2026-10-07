# Bulk Certificate Generator

Backend API that takes a list of recipients and a certificate title, and
generates a certificate image for each recipient against a fixed template.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

SQLite is used by default so there's nothing extra to install. If you want
Postgres instead, set `DATABASE_URL` before running:

```bash
export DATABASE_URL="postgresql+psycopg2://user:pass@localhost/certgen"
```

## Running the app

```bash
uvicorn app.main:app --reload
```

The API comes up on `http://127.0.0.1:8000`. Interactive docs (Swagger UI)
are at `http://127.0.0.1:8000/docs`.

## Running tests

```bash
pytest -v
```

9 tests, covering job creation, input validation, certificate generation,
job status/progress, individual failure isolation, and certificate retrieval.

## Submitting a certificate generation request

```
POST /api/jobs
Content-Type: application/json

{
  "title": "Python Bootcamp 2026",
  "recipients": [
    { "name": "Asha Rao", "email": "asha@example.com", "extra_text": "Full Stack Development — Oct 2026" },
    { "name": "Vikram Shah", "email": "vikram@example.com" }
  ]
}
```

Response (201):

```json
{ "job_id": "6c0f0da0-...", "status": "PENDING", "total": 2 }
```

`extra_text` is optional — it's the line printed under the name (course
name, date, score, whatever the certificate needs).

## Checking progress / result

```
GET /api/jobs/{job_id}
```

```json
{
  "job_id": "6c0f0da0-...",
  "title": "Python Bootcamp 2026",
  "status": "COMPLETED",
  "total": 2,
  "completed": 2,
  "failed": 0,
  "pending": 0,
  "created_at": "...",
  "updated_at": "..."
}
```

`status` is one of `PENDING`, `PROCESSING`, `COMPLETED`,
`COMPLETED_WITH_ERRORS`, `FAILED`.

To see per-recipient results (including why a specific one failed):

```
GET /api/jobs/{job_id}/certificates
```

## Retrieving a generated certificate

```
GET /api/certificates/{certificate_id}/download
```

Returns the PNG file. 404 if the certificate doesn't exist, 409 if it
exists but failed/hasn't generated yet.

## Design decisions

**Sync vs async processing.** Drawing one certificate (open template,
write the name, save a PNG) is fast — tens of milliseconds — but a bulk
request could have hundreds or thousands of recipients, and I didn't want
the client sitting on one HTTP call that long or risking a timeout. So
`POST /api/jobs` just creates the job and recipient rows (status
`PENDING`) and returns immediately with a `job_id`; the actual generation
runs afterward via FastAPI's `BackgroundTasks`. The client polls
`GET /api/jobs/{id}` for progress, same pattern as most async job APIs.

I didn't reach for Celery/Redis here — for the scope of this assignment,
an in-process background task is simpler to set up and run, and there's
nothing in the requirements that needs the job to survive a server
restart. The trade-off is real though: `BackgroundTasks` run in the same
process as the API, so if the server crashes mid-job, that job is stuck
half-done with no retry. If this were going into production with real
traffic, I'd move this to Celery or RQ with Redis as the broker — that
gets you persistence, retries, and the ability to run workers on separate
machines from the API.

**Failure isolation.** Each recipient is processed in its own try/except
inside the loop in `job_service.process_job`. A bad recipient (missing
name, or something going wrong in PIL while drawing/saving) is marked
`FAILED` with an error message and the loop moves on — it doesn't raise
and kill the rest of the job. The job's final status reflects the mix:
`COMPLETED` if everything generated, `FAILED` if nothing did,
`COMPLETED_WITH_ERRORS` if it's a mix of both — so the client doesn't have
to guess, they can read it straight off the job status.

**Certificate generation.** One fixed template (`app/templates/certificate_template.png`),
generated once with Pillow — a bordered card with a title and a blank area
with a divider line. At generation time, the app re-opens that template
per recipient and draws the name + the optional extra line over the
blank area with `ImageDraw`, then saves it as a new PNG per recipient
under `storage/certificates/`. Opening the template fresh for every
recipient (instead of mutating one shared image in memory) was a
deliberate choice — it's slightly more I/O but means one request can't
leave artifacts on another's certificate if something goes wrong
mid-draw.

**Storage.** Generated PNGs are saved to disk under `storage/certificates/`
and the DB just stores the file path. For a cloud deployment I'd point
this at S3 (or equivalent) instead of local disk, but local storage is
fine for running this locally / in the assignment's scope.

**IDs.** Jobs and certificate records both use UUIDs rather than
auto-increment integers, mainly so certificate IDs in download URLs
aren't easily guessable/enumerable.

## What I'd add with more time

- Rate limiting / a max recipients-per-request cap, so one request can't
  accidentally queue a huge job.
- Moving background processing to Celery + Redis for durability and the
  ability to scale workers independently of the API.
- Signed, expiring download URLs instead of a plain certificate ID in the
  path.
- A way to re-run just the failed recipients in a job instead of
  resubmitting the whole batch.
