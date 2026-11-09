"""
Builds identity.db from the synthetic CSV files in ./data.

    python seed.py          -> deletes and rebuilds the database

Login accounts it creates (demo only):
    every dataset user : <firstname>.<lastname>@example.com   password: Demo@1234
    administrator      : admin@example.com                     password: Admin@1234
"""
import csv
import os
import re
from datetime import date, datetime, timedelta

from auth import hash_password
from database import BASE_DIR, Base, SessionLocal, engine
from models import AccessRequest, DigitalAsset, SecurityEvent, TrustedContact, User

DATA_DIR = os.path.join(BASE_DIR, "data")
DEMO_PASSWORD = "Demo@1234"
ADMIN_PASSWORD = "Admin@1234"
# The dataset's "days since review" values were counted from this date.
DATASET_REFERENCE_DATE = date(2026, 11, 1)


def read_csv(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_email(full_name, taken):
    base = re.sub(r"[^a-z.]", "", full_name.lower().replace(" ", "."))
    email, n = f"{base}@example.com", 2
    while email in taken:
        email, n = f"{base}{n}@example.com", n + 1
    taken.add(email)
    return email


def d(text):
    return datetime.strptime(text, "%Y-%m-%d").date()


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("Hashing demo passwords (takes a few seconds)...")
    taken = set()
    for row in read_csv("users.csv"):
        db.add(User(
            user_id=row["user_id"], full_name=row["full_name"],
            email=make_email(row["full_name"], taken),
            password_hash=hash_password(DEMO_PASSWORD), is_admin=False,
            age=int(row["age"]), city=row["city"], state=row["state"],
            preferred_language=row["preferred_language"],
            occupation_category=row["occupation_category"],
            digital_literacy_level=row["digital_literacy_level"],
            account_security_awareness=row["account_security_awareness"],
            created_at=d(row["created_at"]),
        ))
    db.add(User(user_id="ADMIN", full_name="System Administrator", email="admin@example.com",
                password_hash=hash_password(ADMIN_PASSWORD), is_admin=True,
                city="—", state="—", created_at=date(2024, 1, 1)))

    for row in read_csv("digital_assets.csv"):
        db.add(DigitalAsset(
            asset_id=row["asset_id"], user_id=row["user_id"], asset_category=row["asset_category"],
            platform_name=row["platform_name"], asset_label=row["asset_label"],
            importance_level=row["importance_level"], management_status=row["management_status"],
            mfa_enabled=row["mfa_enabled"],
            last_reviewed_on=DATASET_REFERENCE_DATE - timedelta(days=int(row["last_reviewed_days_ago"])),
            contains_sensitive_data=row["contains_sensitive_data"],
        ))

    for row in read_csv("trusted_contacts.csv"):
        db.add(TrustedContact(
            contact_id=row["contact_id"], user_id=row["user_id"], contact_name=row["contact_name"],
            relationship_category=row["relationship_category"],
            verification_status=row["verification_status"],
            authorization_level=row["authorization_level"],
            contact_email=row["contact_email"], added_on=d(row["added_on"]),
        ))

    for row in read_csv("access_requests.csv"):
        db.add(AccessRequest(
            request_id=row["request_id"], user_id=row["user_id"], asset_id=row["asset_id"],
            contact_id=row["contact_id"] or None, requester_type=row["requester_type"],
            request_type=row["request_type"], request_reason=row["request_reason"],
            request_date=d(row["request_date"]), verification_status=row["verification_status"],
            authorization_status=row["authorization_status"], request_status=row["request_status"],
        ))

    for row in read_csv("security_events.csv"):
        db.add(SecurityEvent(
            event_id=row["event_id"], user_id=row["user_id"], asset_id=row["asset_id"],
            event_type=row["event_type"],
            event_time=datetime.strptime(row["event_time"], "%Y-%m-%d %H:%M:%S"),
            device_category=row["device_category"], is_new_device=row["is_new_device"],
            location_region=row["location_region"],
            failed_attempt_count=int(row["failed_attempt_count"]),
            is_suspicious=row["is_suspicious"], risk_level=row["risk_level"],
            recommended_action=row["recommended_action"],
            related_request_id=row["related_request_id"] or None,
            data_origin=row["data_origin"], resolution=None,
        ))

    db.commit()
    counts = {m.__tablename__: db.query(m).count() for m in (User, DigitalAsset, TrustedContact, AccessRequest, SecurityEvent)}
    db.close()
    print("Database ready:", counts)
    print(f"Log in as any user with password {DEMO_PASSWORD}, e.g. parth.patel@example.com")
    print(f"Admin: admin@example.com / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    seed()
