def _payload(recipients):
    return {"title": "Python Bootcamp 2026", "recipients": recipients}


def test_create_job_returns_job_id_and_total(client):
    resp = client.post(
        "/api/jobs",
        json=_payload(
            [
                {"name": "Asha Rao", "email": "asha@example.com"},
                {"name": "Vikram Shah", "email": "vikram@example.com"},
            ]
        ),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == 2
    assert body["job_id"]


def test_create_job_rejects_empty_recipient_list(client):
    resp = client.post("/api/jobs", json=_payload([]))
    assert resp.status_code == 422


def test_invalid_recipient_does_not_block_valid_ones(client):
    # TestClient runs BackgroundTasks synchronously as part of the request,
    # so by the time we get the response the job has already finished processing.
    resp = client.post(
        "/api/jobs",
        json=_payload(
            [
                {"name": "Good Recipient", "email": "good@example.com"},
                {"name": "", "email": "bad@example.com"},  # blank name -> should fail validation
            ]
        ),
    )
    job_id = resp.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}").json()
    assert status["completed"] == 1
    assert status["failed"] == 1
    assert status["status"] == "COMPLETED_WITH_ERRORS"


def test_certificate_is_actually_generated(client):
    resp = client.post("/api/jobs", json=_payload([{"name": "Meera Iyer"}]))
    job_id = resp.json()["job_id"]

    certs = client.get(f"/api/jobs/{job_id}/certificates").json()
    assert len(certs) == 1
    assert certs[0]["status"] == "GENERATED"
    assert certs[0]["download_url"] is not None

    download = client.get(certs[0]["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"] == "image/png"
    assert len(download.content) > 0


def test_job_status_progress_counts_are_consistent(client):
    recipients = [{"name": f"Student {i}"} for i in range(5)]
    resp = client.post("/api/jobs", json=_payload(recipients))
    job_id = resp.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}").json()
    assert status["total"] == 5
    assert status["completed"] == 5
    assert status["failed"] == 0
    assert status["pending"] == 0
    assert status["status"] == "COMPLETED"


def test_individual_failure_does_not_crash_the_job(client):
    recipients = [
        {"name": "Valid One"},
        {"name": None},  # missing name entirely
        {"name": "Valid Two"},
    ]
    resp = client.post("/api/jobs", json=_payload(recipients))
    job_id = resp.json()["job_id"]

    status = client.get(f"/api/jobs/{job_id}").json()
    assert status["completed"] == 2
    assert status["failed"] == 1

    certs = client.get(f"/api/jobs/{job_id}/certificates").json()
    failed = [c for c in certs if c["status"] == "FAILED"]
    assert len(failed) == 1
    assert failed[0]["error_message"]


def test_get_unknown_job_returns_404(client):
    resp = client.get("/api/jobs/does-not-exist")
    assert resp.status_code == 404


def test_download_unknown_certificate_returns_404(client):
    resp = client.get("/api/certificates/does-not-exist/download")
    assert resp.status_code == 404


def test_download_not_available_for_failed_certificate(client):
    resp = client.post("/api/jobs", json=_payload([{"name": None}]))
    job_id = resp.json()["job_id"]
    certs = client.get(f"/api/jobs/{job_id}/certificates").json()
    failed_id = certs[0]["id"]

    download = client.get(f"/api/certificates/{failed_id}/download")
    assert download.status_code == 409
