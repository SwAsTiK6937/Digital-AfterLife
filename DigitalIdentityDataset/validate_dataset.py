"""
Validation script - proves the synthetic dataset is internally consistent
and privacy-safe. Run after generate_dataset.py:

    python validate_dataset.py

Every check prints PASS or FAIL. A trustworthy dataset should be all PASS.
"""

import csv
import os
import re
from collections import Counter
from datetime import datetime

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


users = load("users.csv")
assets = load("digital_assets.csv")
contacts = load("trusted_contacts.csv")
requests = load("access_requests.csv")
events = load("security_events.csv")
ml = load("ml_security_events.csv")

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {detail}" if detail and not ok else ""))


U = {u["user_id"]: u for u in users}
A = {a["asset_id"]: a for a in assets}
C = {c["contact_id"]: c for c in contacts}
R = {r["request_id"]: r for r in requests}

print("\n--- 1. Primary keys ---")
for name, rows, key in [("users", users, "user_id"), ("assets", assets, "asset_id"), ("contacts", contacts, "contact_id"),
                        ("requests", requests, "request_id"), ("events", events, "event_id")]:
    ids = [r[key] for r in rows]
    check(f"{name}: {key} unique and non-empty", len(ids) == len(set(ids)) and all(ids))

print("\n--- 2. Foreign keys ---")
check("assets.user_id exists in users", all(a["user_id"] in U for a in assets))
check("contacts.user_id exists in users", all(c["user_id"] in U for c in contacts))
check("requests.user_id / asset_id exist", all(r["user_id"] in U and r["asset_id"] in A for r in requests))
check("requests.asset_id belongs to the same user", all(A[r["asset_id"]]["user_id"] == r["user_id"] for r in requests))
check("requests.contact_id exists and belongs to same user",
      all(r["contact_id"] == "" or (r["contact_id"] in C and C[r["contact_id"]]["user_id"] == r["user_id"]) for r in requests))
check("events.asset_id belongs to events.user_id", all(A[e["asset_id"]]["user_id"] == e["user_id"] for e in events))
check("events.related_request_id exists and matches user",
      all(e["related_request_id"] == "" or (e["related_request_id"] in R and R[e["related_request_id"]]["user_id"] == e["user_id"]) for e in events))
check("every user has >= 1 email asset", all(any(a["user_id"] == u and a["asset_category"] == "Email" for a in assets) for u in U))

print("\n--- 3. Logical consistency ---")
check("all users are adults (18+)", all(int(u["age"]) >= 18 for u in users))
check("students are <= 30, retired are >= 55",
      all(not (u["occupation_category"] == "Student" and int(u["age"]) > 30) and
          not (u["occupation_category"] == "Retired" and int(u["age"]) < 55) for u in users))
check("unverified contacts have No Authorization",
      all(c["verification_status"] == "Verified" or c["authorization_level"] == "No Authorization" for c in contacts))
check("contact added after user account created",
      all(c["added_on"] >= U[c["user_id"]]["created_at"] for c in contacts))
check("request made after the contact was added",
      all(r["contact_id"] == "" or r["request_date"] > C[r["contact_id"]]["added_on"] for r in requests))

bad = [r["request_id"] for r in requests if not (
    (r["verification_status"] == "Pending" and r["authorization_status"] == "Pending" and r["request_status"] == "Pending") or
    (r["verification_status"] == "Rejected" and r["authorization_status"] == "Denied" and r["request_status"] in ("Denied", "Closed")) or
    (r["verification_status"] == "Verified" and (
        (r["authorization_status"] == "Approved" and r["request_status"] in ("Approved", "Closed")) or
        (r["authorization_status"] == "Denied" and r["request_status"] in ("Denied", "Closed")) or
        (r["authorization_status"] == "Pending" and r["request_status"] == "Pending"))))]
check("request verification/authorization/status never contradict", not bad, bad[:5])

check("unregistered requesters are never approved",
      all(not (r["requester_type"] == "Unregistered Requester" and r["authorization_status"] == "Approved") for r in requests))


def allowed(level, rtype):
    return level == "Submit Request" or (level == "View Metadata" and rtype == "View Asset Metadata")


check("approved requests respect contact's authorization level",
      all(r["authorization_status"] != "Approved" or allowed(C[r["contact_id"]]["authorization_level"], r["request_type"])
          for r in requests))

ranges = {"Active": (0, 179), "Inactive": (180, 720), "Unmanaged": (366, 99999), "Under Review": (0, 29)}
check("management_status matches last_reviewed_days_ago",
      all(ranges[a["management_status"]][0] <= int(a["last_reviewed_days_ago"]) <= ranges[a["management_status"]][1] for a in assets))

check("is_suspicious = No  <=>  risk_level = Low",
      all((e["is_suspicious"] == "No") == (e["risk_level"] == "Low") for e in events))
check("Normal Activity is never suspicious", all(e["is_suspicious"] == "No" for e in events if e["event_type"] == "Normal Activity"))
check("Low risk -> Monitor; Medium/High never Monitor",
      all((e["risk_level"] == "Low") == (e["recommended_action"] == "Monitor") for e in events))
check("Review/Block Request actions only on access-request events",
      all(e["recommended_action"] != "Review Request" or e["event_type"] == "Unusual Access Request" for e in events))
check("Repeated Failed Login has >= 3 failed attempts",
      all(int(e["failed_attempt_count"]) >= 3 for e in events if e["event_type"] == "Repeated Failed Login"))
check("Inactive Account Review only on Inactive/Unmanaged assets",
      all(A[e["asset_id"]]["management_status"] in ("Inactive", "Unmanaged") for e in events if e["event_type"] == "Inactive Account Review"))
check("events occur after the user account was created",
      all(e["event_time"][:10] >= U[e["user_id"]]["created_at"] for e in events))
check("all events tagged SIMULATED", all(e["data_origin"] == "SIMULATED" for e in events))

print("\n--- 4. Privacy safety ---")
all_text = ""
for fname in os.listdir(DATA):
    with open(os.path.join(DATA, fname), encoding="utf-8") as f:
        all_text += f.read()
emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", all_text)
check("only reserved example.com emails", all(e.endswith("@example.com") for e in emails))
check("no 10-digit phone-like numbers", not re.search(r"(?<!\d)[6-9]\d{9}(?!\d)", all_text))
check("no 12-digit Aadhaar-like numbers", not re.search(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)", all_text))
check("no PAN-like codes (AAAAA9999A)", not re.search(r"\b[A-Z]{5}\d{4}[A-Z]\b", all_text))
check("no card-number-like 16-digit sequences", not re.search(r"(?<!\d)\d{16}(?!\d)", all_text))
check("no password / seed / key columns",
      not any(k in col.lower() for rows in (users, assets, contacts, requests, events) for col in rows[0]
              for k in ("password", "seed", "private_key", "aadhaar", "pan_", "otp")))
check("no religion/caste/health/orientation columns",
      not any(k in col.lower() for rows in (users, contacts) for col in rows[0]
              for k in ("religion", "caste", "health", "orientation", "ethnicity", "gender")))
names = [u["full_name"] for u in users] + [c["contact_name"] for c in contacts]
check("all person names unique across users + contacts", len(names) == len(set(names)))

print("\n--- 5. ML file leakage check ---")
feature_cols = [c for c in ml[0] if not c.startswith("target_") and c != "event_id"]
check("no ID columns used as features", not any(c.endswith("_id") for c in feature_cols))
check("recommended_action not in ML features", "recommended_action" not in feature_cols)
check("ML rows match events 1:1", len(ml) == len(events) and {m["event_id"] for m in ml} == {e["event_id"] for e in events})

print("\n--- 6. Distribution summary (for your report) ---")
print("Users by state (top 8):", Counter(u["state"] for u in users).most_common(8))
print("Languages:", dict(Counter(u["preferred_language"] for u in users)))
print("Asset categories:", dict(Counter(a["asset_category"] for a in assets)))
print("Asset status:", dict(Counter(a["management_status"] for a in assets)))
print("MFA:", dict(Counter(a["mfa_enabled"] for a in assets)))
print("Event types:", dict(Counter(e["event_type"] for e in events)))
print("Risk levels:", dict(Counter(e["risk_level"] for e in events)))
print("Suspicious:", dict(Counter(e["is_suspicious"] for e in events)))
print("Request status:", dict(Counter(r["request_status"] for r in requests)))
print("Requester type:", dict(Counter(r["requester_type"] for r in requests)))

print(f"\n{sum(results)}/{len(results)} checks passed.")
