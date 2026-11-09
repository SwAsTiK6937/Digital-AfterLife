"""
End-to-end checks for the app. Run:  python test_app.py
Needs: pip install httpx   (used by FastAPI's TestClient)

Your identity.db is backed up first and restored afterwards, so the tests
don't leave any changes behind.
"""
import os
import re
import shutil

from fastapi.testclient import TestClient

from database import BASE_DIR

DB = os.path.join(BASE_DIR, "identity.db")
shutil.copy(DB, DB + ".bak")

import main  # noqa: E402  (import after the backup)

results = []


def check(name, ok):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")


def login(email, pw):
    c = TestClient(main.app, follow_redirects=False)
    r = c.post("/login", data={"email": email, "password": pw})
    return c, r


try:
    anon = TestClient(main.app, follow_redirects=False)
    check("health endpoint", anon.get("/health").json() == {"status": "ok"})
    check("dashboard redirects to login when signed out", anon.get("/dashboard").headers["location"] == "/login")

    _, r = login("parth.patel@example.com", "wrong")
    check("wrong password rejected", r.status_code == 200 and "incorrect" in r.text)

    parth, r = login("parth.patel@example.com", "Demo@1234")
    check("correct password logs in", r.status_code == 303 and r.headers["location"] == "/dashboard")
    for path in ["/dashboard", "/assets", "/contacts", "/requests", "/alerts", "/alerts?risk=High", "/assets?status=Inactive"]:
        check(f"GET {path} -> 200", parth.get(path).status_code == 200)
    dash = parth.get("/dashboard").text
    check("dashboard shows Parth's own data", "Welcome back, Parth" in dash and "Backup email" in dash)

    # --- access control
    check("cannot open another user's asset action", parth.post("/assets/A0004/review").status_code == 404)
    check("cannot change another user's contact", parth.post("/contacts/C0002/send-verification").status_code == 404)
    check("cannot resolve another user's alert", parth.post("/alerts/E0004/resolve", data={"answer": "me"}).status_code == 404)
    check("other users' requests not listed", "R0016" not in parth.get("/requests?id=R0016").text)
    check("member gets 404 on admin page", parth.get("/admin").status_code == 404)

    # --- tampered cookie
    forged = TestClient(main.app, follow_redirects=False)
    forged.cookies.set("dip_session", parth.cookies.get("dip_session").replace("U0004", "U0002"))
    check("forged session cookie rejected", forged.get("/dashboard").headers.get("location") == "/login")

    # --- assets
    r = parth.post("/assets", data={"asset_category": "Financial Service", "platform_name": "UPI Payment App",
                                    "asset_label": "UPI 9876543210", "importance_level": "High", "mfa_enabled": "Yes"})
    check("secret-looking text refused", "err=" in r.headers["location"])
    r = parth.post("/assets", data={"asset_category": "Financial Service", "platform_name": "UPI Payment App",
                                    "asset_label": "UPI payments", "importance_level": "High", "mfa_enabled": "Yes"})
    check("valid asset created", "msg=" in r.headers["location"] and "UPI payments" in parth.get("/assets").text)
    check("mark reviewed works", "msg=" in parth.post("/assets/A0010/review").headers["location"])

    # --- contacts: add -> send link -> verify -> give authority
    r = parth.post("/contacts", data={"contact_name": "Rakesh Desai", "relationship_category": "Friend",
                                      "contact_email": "rakesh@gmail.com"})
    check("real-looking email refused for contacts", "err=" in r.headers["location"])
    parth.post("/contacts", data={"contact_name": "Rakesh Desai", "relationship_category": "Friend"})
    cid = re.findall(r"/contacts/(C\d+)/send-verification", parth.get("/contacts").text)[-1]
    r = parth.post(f"/contacts/{cid}/authority", data={"authorization_level": "Submit Request"})
    check("unverified contact cannot get authority", "err=" in r.headers["location"])
    parth.post(f"/contacts/{cid}/send-verification")
    parth.post(f"/contacts/{cid}/confirm")
    r = parth.post(f"/contacts/{cid}/authority", data={"authorization_level": "Submit Request"})
    check("verified contact can be given authority", "msg=" in r.headers["location"])

    # --- requests
    r = parth.post("/requests/simulate", data={"requester": "unregistered", "asset_id": "A0009",
                                               "request_type": "View Asset Metadata"})
    rid = re.search(r"id=(R\d+)", r.headers["location"]).group(1)
    page = parth.get(f"/requests?id={rid}").text
    check("unregistered request auto-denied", "Identity check failed" in page and "Denied" in page)
    check("unregistered request raised an alert", rid in parth.get("/alerts").text)

    r = parth.post("/requests/simulate", data={"requester": cid, "asset_id": "A0011",
                                               "request_type": "Request Account Review"})
    rid2 = re.search(r"id=(R\d+)", r.headers["location"]).group(1)
    check("verified contact request waits for owner", "Waiting for your decision" in parth.get(f"/requests?id={rid2}").text)
    parth.post(f"/requests/{rid2}/decide", data={"decision": "approve"})
    check("owner can approve", "Approved" in parth.get(f"/requests?id={rid2}").text)
    r = parth.post(f"/requests/{rid}/decide", data={"decision": "approve"})
    check("denied request cannot be approved", "err=" in r.headers["location"])

    # --- alerts
    r = parth.post("/alerts/simulate", data={"asset_id": "A0009", "event_type": "Unusual Login",
                                             "location_region": "Chennai, Tamil Nadu", "device_category": "Desktop",
                                             "is_new_device": "Yes", "hour": "2", "failed_attempt_count": "0"})
    check("simulated risky login scored High", "High" in r.headers["location"] or "High" in parth.get(r.headers["location"]).text)
    r = parth.post("/alerts/simulate", data={"asset_id": "A0011", "event_type": "Normal Activity",
                                             "location_region": "Surat, Gujarat", "device_category": "Mobile",
                                             "hour": "14", "failed_attempt_count": "0"})
    check("simulated normal activity scored Low", "Low" in parth.get(r.headers["location"]).text)
    check("resolve alert as 'not me'", "msg=" in parth.post("/alerts/E0347/resolve", data={"answer": "not_me"}).headers["location"])

    # --- admin
    admin, r = login("admin@example.com", "Admin@1234")
    check("admin logs in to /admin", r.headers["location"] == "/admin")
    a = admin.get("/admin")
    check("admin sees all 100 users", a.status_code == 200 and "(100)" in a.text)
    check("admin search works", "Parth Patel" in admin.get("/admin?q=Surat").text)
    check("admin is redirected away from member pages", admin.get("/dashboard").headers["location"] == "/admin")

    # --- lockout
    for _ in range(5):
        login("priya.sharma@example.com", "nope")
    _, r = login("priya.sharma@example.com", "Demo@1234")
    check("5 wrong passwords lock the account", "locked" in r.text)

    # --- logout
    parth.post("/logout")
    parth.cookies.clear()
    check("logout ends session", parth.get("/dashboard").headers["location"] == "/login")
finally:
    main_engine = __import__("database").engine
    main_engine.dispose()
    shutil.move(DB + ".bak", DB)

print(f"\n{sum(results)}/{len(results)} checks passed.")
