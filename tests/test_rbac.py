"""The most important tests in the project: prove nobody sees what they shouldn't."""
from app.rbac import ROLES, can_access, chroma_filter
from conftest import login


def sources(resp):
    return {s["source"] for s in resp.json()["sources"]}


def test_unauthenticated_is_rejected(client):
    assert client.post("/query", json={"question": "what is the salary band"}).status_code == 401
    assert client.get("/documents").status_code == 401


def test_bad_password_rejected(client):
    r = client.post("/auth/login", data={"username": "alice", "password": "nope"})
    assert r.status_code == 401


def test_employee_cannot_reach_hr_finance_or_security(client):
    h = login(client, "alice")
    for q in ["what are the salary bands for software engineers",
              "what is the Q3 revenue forecast",
              "what is the data breach response plan and incident bridge"]:
        r = client.post("/query", json={"question": q}, headers=h)
        assert r.status_code == 200
        leaked = sources(r) & {"salary_bands_2026.txt", "q3_financial_forecast.txt", "data_breach_response_plan.txt"}
        assert not leaked, f"LEAK for {q}: {leaked}"
        assert "lakh" not in r.json()["answer"] and "42 million" not in r.json()["answer"]


def test_employee_can_read_general_docs(client):
    h = login(client, "alice")
    r = client.post("/query", json={"question": "how many days can I work remotely"}, headers=h)
    assert "remote_work_policy.txt" in sources(r)


def test_hr_manager_sees_salary_but_not_finance(client):
    h = login(client, "hannah")
    r = client.post("/query", json={"question": "what are the salary bands for software engineers"}, headers=h)
    assert "salary_bands_2026.txt" in sources(r)
    r = client.post("/query", json={"question": "Q3 revenue forecast operating margin"}, headers=h)
    assert "q3_financial_forecast.txt" not in sources(r)


def test_only_compliance_and_admin_see_restricted_breach_plan(client):
    q = {"question": "breach response plan regulators notified 72 hours"}
    for user, expected in [("alice", False), ("hannah", False), ("frank", False), ("carl", True), ("root", True)]:
        r = client.post("/query", json=q, headers=login(client, user))
        assert ("data_breach_response_plan.txt" in sources(r)) is expected, user


def test_document_listing_hides_forbidden_docs(client):
    names = {d["source"] for d in client.get("/documents", headers=login(client, "alice")).json()}
    assert names == {"code_of_conduct.txt", "remote_work_policy.txt"}


def test_only_admin_can_ingest_and_delete(client):
    files = {"file": ("note.txt", b"A short public note about the cafeteria menu on Fridays.", "text/plain")}
    data = {"department": "general", "classification": "public"}
    assert client.post("/documents", files=files, data=data, headers=login(client, "hannah")).status_code == 403
    r = client.post("/documents", files=files, data=data, headers=login(client, "root"))
    assert r.status_code == 200
    doc_id = r.json()["doc_id"]
    assert client.delete(f"/documents/{doc_id}", headers=login(client, "alice")).status_code == 403
    assert client.delete(f"/documents/{doc_id}", headers=login(client, "root")).status_code == 200


def test_audit_log_access_and_content(client):
    client.post("/query", json={"question": "gift limit from vendors"}, headers=login(client, "alice"))
    assert client.get("/audit", headers=login(client, "alice")).status_code == 403
    log = client.get("/audit", headers=login(client, "carl")).json()
    assert any(e["event"] == "query" and e["username"] == "alice" for e in log)
    assert all(e["detail"].get("policy_mismatch_blocked", 0) == 0 for e in log if e["event"] == "query")


def test_role_change_takes_effect_without_new_token(client):
    h = login(client, "hannah")
    client.app.state.db.create_user("hannah", "Passw0rd!", "employee")      # demote
    r = client.post("/query", json={"question": "salary bands software engineer"}, headers=h)
    assert "salary_bands_2026.txt" not in sources(r)


def test_db_filter_and_python_policy_agree(client):
    """Defence-in-depth consistency: whatever Chroma lets through, can_access must allow."""
    store = client.app.state.vectors
    everything = store.col.get(include=["metadatas"])["metadatas"]
    for role in ROLES.values():
        via_db = {m["doc_id"] for m in store.col.get(where=chroma_filter(role), include=["metadatas"])["metadatas"]}
        via_py = {m["doc_id"] for m in everything if can_access(role, m)}
        assert via_db == via_py, role.name


def test_policy_fails_closed_on_missing_metadata():
    assert can_access(ROLES["admin"], {}) is False
