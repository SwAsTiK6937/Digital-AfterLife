"""
Digital Identity Protection System - FastAPI app.

Run:
    python seed.py                 (first time, builds identity.db)
    uvicorn main:app --reload      then open http://127.0.0.1:8000

Every page only ever loads rows WHERE user_id = the logged-in user,
so one user can never see or change another user's records.
"""
import random
import re
from collections import Counter
from datetime import date, datetime
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import (COOKIE_NAME, SESSION_SECONDS, AdminRequired, LoginRequired, clear_failures,
                  current_admin, current_member, is_locked, make_session_cookie, read_session_cookie,
                  record_failure, verify_password)
from database import BASE_DIR, get_db
from models import AccessRequest, DigitalAsset, SecurityEvent, TrustedContact, User
from risk import RISK_ORDER, event_reasons, evaluate_request, request_checks, score_event

import os  # noqa: E402

# First run: build identity.db from the CSV files automatically.
if not os.path.exists(os.path.join(BASE_DIR, "identity.db")):
    from seed import seed
    seed()

app = FastAPI(title="Digital Identity Protection System")
app.mount("/static", StaticFiles(directory=f"{BASE_DIR}/static"), name="static")
templates = Jinja2Templates(directory=f"{BASE_DIR}/templates")

# ---------------------------------------------------------------- constants
CATEGORIES = ["Email", "Social Media", "Cloud Storage", "Shopping", "Subscription",
              "Website/Domain", "Financial Service", "Other"]
LEVELS = ["Low", "Medium", "High"]
MFA_OPTIONS = ["Yes", "No", "Unknown"]
STATUSES = ["Active", "Inactive", "Unmanaged", "Under Review"]
RELATIONSHIPS = ["Family", "Friend", "Colleague", "Other"]
AUTH_LEVELS = ["No Authorization", "View Metadata", "Submit Request"]
REQUEST_TYPES = ["View Asset Metadata", "Flag Suspicious Activity", "Request Account Review"]
EVENT_TYPES = ["Normal Activity", "Unusual Login", "Repeated Failed Login", "Unknown Device",
               "Inactive Account Review"]
DEVICES = ["Mobile", "Desktop", "Tablet", "Unknown"]
# Anything that looks like a secret (long digit runs, emails, OTP/password words) is refused.
SECRET_PATTERN = re.compile(r"\d{6,}|@|password|passwd|\botp\b|\bpin\b|aadhaar|\bpan\b|\bcvv\b|seed phrase", re.I)


# ---------------------------------------------------------------- error handling
@app.exception_handler(LoginRequired)
async def _login_required(request: Request, exc: LoginRequired):
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


@app.exception_handler(AdminRequired)
async def _admin_home(request: Request, exc: AdminRequired):
    return RedirectResponse("/admin", status_code=303)


# ---------------------------------------------------------------- template helpers
def fmt_date(value):
    return value.strftime("%d %b %Y").lstrip("0") if value else "—"


def fmt_dt(value):
    return value.strftime("%d %b %Y, %H:%M") if value else "—"


def days_since(value):
    return (date.today() - value).days if value else None


def initials(name):
    parts = [p for p in name.split() if p]
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


templates.env.filters.update(fmt_date=fmt_date, fmt_dt=fmt_dt, days_since=days_since, initials=initials)
templates.env.globals.update(risk_class=lambda r: (r or "low").lower())


def page(request, name, user, db, **context):
    """Render a template with the values every page needs (sidebar badge, flash message)."""
    open_alerts = 0
    if user and not user.is_admin:
        open_alerts = db.query(SecurityEvent).filter(
            SecurityEvent.user_id == user.user_id, SecurityEvent.is_suspicious == "Yes",
            SecurityEvent.resolution.is_(None)).count()
    context.update(user=user, open_alerts=open_alerts, today=date.today(), msg=request.query_params.get("msg"),
                   err=request.query_params.get("err"))
    return templates.TemplateResponse(request, name, context)


def go(url, msg=None, err=None):
    """Redirect after a form POST (Post/Redirect/Get), optionally with a message."""
    sep = "&" if "?" in url else "?"
    if msg:
        url += f"{sep}msg={quote(msg)}"
    elif err:
        url += f"{sep}err={quote(err)}"
    return RedirectResponse(url, status_code=303)


def owned(db, model, pk, user):
    """Load a record only if it belongs to the logged-in user, otherwise 404."""
    obj = db.get(model, pk)
    if obj is None or obj.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Not found")
    return obj


def next_id(db, model, column, prefix):
    ids = [row[0] for row in db.query(column).all()]
    biggest = max((int(i[len(prefix):]) for i in ids if i.startswith(prefix) and i[len(prefix):].isdigit()), default=0)
    return f"{prefix}{biggest + 1:04d}"


def clean_text(value, field, max_len=80):
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{field} is required.")
    if len(value) > max_len:
        raise ValueError(f"{field} must be {max_len} characters or fewer.")
    if SECRET_PATTERN.search(value):
        raise ValueError(f"{field} looks like it contains a secret or ID number. Never store those here.")
    return value


def pick(value, allowed, field):
    if value not in allowed:
        raise ValueError(f"Invalid {field}.")
    return value


# ---------------------------------------------------------------- auth pages
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home(request: Request):
    return RedirectResponse("/dashboard" if read_session_cookie(request.cookies.get(COOKIE_NAME)) else "/login")


@app.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    demo_ids = ["U0004", "U0002", "U0001"]
    demo_users = [u for uid in demo_ids if (u := db.get(User, uid))]
    return page(request, "login.html", None, db, demo_users=demo_users, email="")


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    email = email.strip().lower()
    demo_users = [u for uid in ["U0004", "U0002", "U0001"] if (u := db.get(User, uid))]
    if is_locked(email):
        return page(request, "login.html", None, db, demo_users=demo_users, email=email,
                    error="Too many wrong passwords. This account is locked for 5 minutes.")
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None or not verify_password(password, user.password_hash):
        record_failure(email)
        return page(request, "login.html", None, db, demo_users=demo_users, email=email,
                    error="Email or password is incorrect.")
    clear_failures(email)
    response = RedirectResponse("/admin" if user.is_admin else "/dashboard", status_code=303)
    response.set_cookie(COOKIE_NAME, make_session_cookie(user.user_id), max_age=SESSION_SECONDS,
                        httponly=True, samesite="lax")
    return response


@app.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


# ---------------------------------------------------------------- dashboard
@app.get("/dashboard")
def dashboard(request: Request, user: User = Depends(current_member), db: Session = Depends(get_db)):
    assets = db.query(DigitalAsset).filter_by(user_id=user.user_id).all()
    contacts = db.query(TrustedContact).filter_by(user_id=user.user_id).all()
    events = (db.query(SecurityEvent).filter_by(user_id=user.user_id)
              .order_by(SecurityEvent.event_time.desc()).all())
    requests_ = db.query(AccessRequest).filter_by(user_id=user.user_id).all()

    cat_counts = Counter(a.asset_category for a in assets)
    attention_assets = [a for a in assets if a.management_status in ("Inactive", "Unmanaged", "Under Review")]
    status_counts = Counter(a.management_status for a in attention_assets)
    high_events = [e for e in events if e.risk_level == "High"]
    verified = [c for c in contacts if c.verification_status == "Verified"]

    todo = []
    for e in [e for e in events if e.is_suspicious == "Yes" and e.resolution is None][:3]:
        todo.append({"level": e.risk_level, "title": f"{e.event_type} on {e.asset.asset_label}",
                     "meta": f"{e.device_category}{' (new device)' if e.is_new_device == 'Yes' else ''} · "
                             f"{e.location_region} · {fmt_dt(e.event_time)}",
                     "link": f"/alerts?focus={e.event_id}",
                     "button": "Verify it was you" if e.event_type in ("Unusual Login", "Unknown Device") else "Review alert",
                     "primary": True})
    for r in requests_:
        if r.request_status == "Pending" and r.verification_status == "Verified":
            todo.append({"level": "Medium", "title": f"{r.contact.contact_name} is waiting for your decision",
                         "meta": f"{r.request_type} · {r.asset.asset_label}", "link": f"/requests?id={r.request_id}",
                         "button": "Decide", "primary": True})
    for a in assets:
        if a.importance_level == "High" and a.mfa_enabled != "Yes":
            word = "off" if a.mfa_enabled == "No" else "not confirmed"
            todo.append({"level": "Medium", "title": f"2-step verification is {word} on {a.asset_label}",
                         "meta": "Turn it on with the provider, then update it here.",
                         "link": f"/assets#{a.asset_id}", "button": "Update asset", "primary": False})
    for a in assets:
        if a.management_status in ("Inactive", "Unmanaged"):
            todo.append({"level": "Medium" if a.management_status == "Unmanaged" else "Low",
                         "title": f"{a.asset_label} not reviewed in {days_since(a.last_reviewed_on)} days",
                         "meta": "Still in use? Review it so it doesn't become an unmanaged account.",
                         "link": f"/assets#{a.asset_id}", "button": "Review asset", "primary": False})
    unverified = [c for c in contacts if c.verification_status != "Verified"]
    if unverified:
        names = " and ".join(c.contact_name for c in unverified[:2]) + (" and others" if len(unverified) > 2 else "")
        todo.append({"level": "Low", "title": f"{len(unverified)} trusted contact{'s are' if len(unverified) > 1 else ' is'} not verified",
                     "meta": f"{names} can't submit requests until verified.", "link": "/contacts",
                     "button": "Send verification", "primary": False})
    todo.sort(key=lambda t: -RISK_ORDER[t["level"]])

    n = len(assets) or 1
    health = [
        ("2-step verification on", sum(a.mfa_enabled == "Yes" for a in assets), len(assets)),
        ("Reviewed in last 180 days", sum(days_since(a.last_reviewed_on) <= 180 for a in assets), len(assets)),
        ("Verified trusted contacts", len(verified), len(contacts)),
    ]
    return page(request, "dashboard.html", user, db, active="dashboard",
                assets=assets, contacts=contacts, events=events[:5], todo=todo[:6], health=health,
                cat_summary=" · ".join(f"{v} {k.lower()}" for k, v in cat_counts.most_common()),
                attention=len(attention_assets),
                attention_summary=" · ".join(f"{v} {k.lower()}" for k, v in status_counts.items()) or "All up to date",
                high_count=len(high_events), latest_high=high_events[0] if high_events else None,
                verified_count=len(verified), n=n)


# ---------------------------------------------------------------- assets
@app.get("/assets")
def assets_page(request: Request, status: str = "All", user: User = Depends(current_member), db: Session = Depends(get_db)):
    q = db.query(DigitalAsset).filter_by(user_id=user.user_id)
    if status in STATUSES:
        q = q.filter(DigitalAsset.management_status == status)
    assets = q.order_by(DigitalAsset.asset_id).all()
    total = db.query(DigitalAsset).filter_by(user_id=user.user_id).count()
    return page(request, "assets.html", user, db, active="assets", assets=assets, total=total, status=status,
                statuses=STATUSES, categories=CATEGORIES, levels=LEVELS, mfa_options=MFA_OPTIONS)


@app.post("/assets")
def create_asset(asset_category: str = Form(...), platform_name: str = Form(...), asset_label: str = Form(...),
                 importance_level: str = Form(...), mfa_enabled: str = Form(...),
                 contains_sensitive_data: str = Form("Unknown"),
                 user: User = Depends(current_member), db: Session = Depends(get_db)):
    try:
        asset = DigitalAsset(
            asset_id=next_id(db, DigitalAsset, DigitalAsset.asset_id, "A"), user_id=user.user_id,
            asset_category=pick(asset_category, CATEGORIES, "category"),
            platform_name=clean_text(platform_name, "Platform type", 60),
            asset_label=clean_text(asset_label, "Label", 60),
            importance_level=pick(importance_level, LEVELS, "importance"),
            mfa_enabled=pick(mfa_enabled, MFA_OPTIONS, "2-step value"),
            contains_sensitive_data=pick(contains_sensitive_data, MFA_OPTIONS, "sensitive data value"),
            management_status="Active", last_reviewed_on=date.today())
    except ValueError as e:
        return go("/assets", err=str(e))
    db.add(asset)
    db.commit()
    return go("/assets", msg=f"“{asset.asset_label}” registered.")


@app.post("/assets/{asset_id}/review")
def review_asset(asset_id: str, user: User = Depends(current_member), db: Session = Depends(get_db)):
    a = owned(db, DigitalAsset, asset_id, user)
    a.management_status, a.last_reviewed_on = "Active", date.today()
    db.commit()
    return go("/assets", msg=f"“{a.asset_label}” marked as reviewed today.")


@app.post("/assets/{asset_id}/update")
def update_asset(asset_id: str, mfa_enabled: str = Form(...), management_status: str = Form(...),
                 user: User = Depends(current_member), db: Session = Depends(get_db)):
    a = owned(db, DigitalAsset, asset_id, user)
    try:
        a.mfa_enabled = pick(mfa_enabled, MFA_OPTIONS, "2-step value")
        a.management_status = pick(management_status, STATUSES, "status")
    except ValueError as e:
        return go("/assets", err=str(e))
    db.commit()
    return go("/assets", msg=f"“{a.asset_label}” updated.")


@app.post("/assets/{asset_id}/delete")
def delete_asset(asset_id: str, user: User = Depends(current_member), db: Session = Depends(get_db)):
    a = owned(db, DigitalAsset, asset_id, user)
    db.query(SecurityEvent).filter_by(asset_id=a.asset_id).delete()
    db.query(AccessRequest).filter_by(asset_id=a.asset_id).delete()
    db.delete(a)
    db.commit()
    return go("/assets", msg=f"“{a.asset_label}” and its history were removed.")


# ---------------------------------------------------------------- trusted contacts
@app.get("/contacts")
def contacts_page(request: Request, user: User = Depends(current_member), db: Session = Depends(get_db)):
    contacts = db.query(TrustedContact).filter_by(user_id=user.user_id).order_by(TrustedContact.contact_id).all()
    req_counts = Counter(r.contact_id for r in db.query(AccessRequest).filter_by(user_id=user.user_id))
    return page(request, "contacts.html", user, db, active="contacts", contacts=contacts, req_counts=req_counts,
                relationships=RELATIONSHIPS, auth_levels=AUTH_LEVELS)


@app.post("/contacts")
def add_contact(contact_name: str = Form(...), relationship_category: str = Form(...), contact_email: str = Form(""),
                user: User = Depends(current_member), db: Session = Depends(get_db)):
    contact_email = contact_email.strip().lower()
    try:
        name = clean_text(contact_name, "Name", 60)
        rel = pick(relationship_category, RELATIONSHIPS, "relationship")
        if contact_email and not re.fullmatch(r"[a-z0-9._-]+@example\.(com|org)", contact_email):
            raise ValueError("This demo only accepts reserved addresses ending in @example.com or @example.org.")
    except ValueError as e:
        return go("/contacts", err=str(e))
    cid = next_id(db, TrustedContact, TrustedContact.contact_id, "C")
    db.add(TrustedContact(contact_id=cid, user_id=user.user_id, contact_name=name, relationship_category=rel,
                          verification_status="Not Verified", authorization_level="No Authorization",
                          contact_email=contact_email or f"contact{cid[1:]}@example.com", added_on=date.today()))
    db.commit()
    return go("/contacts", msg=f"{name} added. Send them a verification link next.")


@app.post("/contacts/{contact_id}/send-verification")
def send_verification(contact_id: str, user: User = Depends(current_member), db: Session = Depends(get_db)):
    c = owned(db, TrustedContact, contact_id, user)
    if c.verification_status == "Verified":
        return go("/contacts", err=f"{c.contact_name} is already verified.")
    c.verification_status = "Pending"
    db.commit()
    return go("/contacts", msg=f"Verification link sent to {c.contact_email} (simulated).")


@app.post("/contacts/{contact_id}/confirm")
def confirm_verification(contact_id: str, user: User = Depends(current_member), db: Session = Depends(get_db)):
    """Demo shortcut: pretend the contact completed verification."""
    c = owned(db, TrustedContact, contact_id, user)
    if c.verification_status != "Pending":
        return go("/contacts", err="Send a verification link first.")
    c.verification_status, c.authorization_level = "Verified", "View Metadata"
    db.commit()
    return go("/contacts", msg=f"{c.contact_name} is verified and can now view metadata.")


@app.post("/contacts/{contact_id}/authority")
def set_authority(contact_id: str, authorization_level: str = Form(...),
                  user: User = Depends(current_member), db: Session = Depends(get_db)):
    c = owned(db, TrustedContact, contact_id, user)
    try:
        level = pick(authorization_level, AUTH_LEVELS, "authority level")
    except ValueError as e:
        return go("/contacts", err=str(e))
    if c.verification_status != "Verified" and level != "No Authorization":
        return go("/contacts", err="Only verified contacts can be given authority.")
    c.authorization_level = level
    db.commit()
    return go("/contacts", msg=f"{c.contact_name}: authority set to {level}.")


@app.post("/contacts/{contact_id}/delete")
def delete_contact(contact_id: str, user: User = Depends(current_member), db: Session = Depends(get_db)):
    c = owned(db, TrustedContact, contact_id, user)
    if db.query(AccessRequest).filter_by(contact_id=c.contact_id).count():
        return go("/contacts", err=f"{c.contact_name} has request history, so they can't be deleted. "
                                   f"Set their authority to No Authorization instead.")
    db.delete(c)
    db.commit()
    return go("/contacts", msg=f"{c.contact_name} removed.")


# ---------------------------------------------------------------- access requests
REASONS = {
    "View Asset Metadata": "Wants to confirm which services are registered",
    "Flag Suspicious Activity": "Noticed unusual posts on the user's profile",
    "Request Account Review": "Account appears inactive for a long time",
}


@app.get("/requests")
def requests_page(request: Request, id: str | None = None, user: User = Depends(current_member), db: Session = Depends(get_db)):
    reqs = (db.query(AccessRequest).filter_by(user_id=user.user_id)
            .order_by(AccessRequest.request_date.desc(), AccessRequest.request_id.desc()).all())
    selected = next((r for r in reqs if r.request_id == id), reqs[0] if reqs else None)
    contacts = db.query(TrustedContact).filter_by(user_id=user.user_id).all()
    assets = db.query(DigitalAsset).filter_by(user_id=user.user_id).all()
    return page(request, "requests.html", user, db, active="requests", reqs=reqs, selected=selected,
                checks=request_checks(selected) if selected else [], contacts=contacts, assets=assets,
                request_types=REQUEST_TYPES)


@app.post("/requests/simulate")
def simulate_request(requester: str = Form(...), asset_id: str = Form(...), request_type: str = Form(...),
                     request_reason: str = Form(""), user: User = Depends(current_member), db: Session = Depends(get_db)):
    """Pretend someone submitted a request, then run it through the rule engine."""
    asset = owned(db, DigitalAsset, asset_id, user)
    contact = None if requester == "unregistered" else owned(db, TrustedContact, requester, user)
    try:
        rtype = pick(request_type, REQUEST_TYPES, "request type")
        reason = clean_text(request_reason or REASONS[rtype], "Reason", 120)
    except ValueError as e:
        return go("/requests", err=str(e))
    ver, auth_status, status = evaluate_request(contact, rtype)
    rid = next_id(db, AccessRequest, AccessRequest.request_id, "R")
    req = AccessRequest(request_id=rid, user_id=user.user_id, asset_id=asset.asset_id,
                        contact_id=contact.contact_id if contact else None,
                        requester_type="Trusted Contact" if contact else "Unregistered Requester",
                        request_type=rtype, request_reason=reason, request_date=date.today(),
                        verification_status=ver, authorization_status=auth_status, request_status=status)
    db.add(req)
    if contact is None or ver == "Rejected":  # suspicious -> raise a security alert too
        others = [f"{c}, {s}" for c, s in db.query(User.city, User.state).filter(User.is_admin.is_(False)).distinct()
                  if c != user.city]
        now = datetime.now().replace(microsecond=0)
        risk, susp, action = score_event("Unusual Access Request", 0, True, True, now.hour, asset, user,
                                         unregistered_requester=contact is None)
        db.add(SecurityEvent(event_id=next_id(db, SecurityEvent, SecurityEvent.event_id, "E"), user_id=user.user_id,
                             asset_id=asset.asset_id, event_type="Unusual Access Request", event_time=now,
                             device_category="Unknown", is_new_device="Yes", location_region=random.choice(others),
                             failed_attempt_count=0, is_suspicious=susp, risk_level=risk, recommended_action=action,
                             related_request_id=rid, data_origin="SIMULATED (live demo)"))
    db.commit()
    return go(f"/requests?id={rid}", msg=f"Request {rid} received and checked: {status}.")


@app.post("/requests/{request_id}/decide")
def decide_request(request_id: str, decision: str = Form(...), user: User = Depends(current_member), db: Session = Depends(get_db)):
    r = owned(db, AccessRequest, request_id, user)
    if decision in ("approve", "deny"):
        if not (r.verification_status == "Verified" and r.authorization_status == "Pending"):
            return go(f"/requests?id={r.request_id}", err="This request can't be decided right now.")
        if decision == "approve":
            r.authorization_status = r.request_status = "Approved"
        else:
            r.authorization_status = r.request_status = "Denied"
    elif decision == "close" and r.request_status in ("Approved", "Denied"):
        r.request_status = "Closed"
    elif decision == "revoke" and r.request_status == "Approved":
        r.authorization_status = r.request_status = "Denied"
    else:
        return go(f"/requests?id={r.request_id}", err="That action isn't allowed for this request.")
    db.commit()
    return go(f"/requests?id={r.request_id}", msg=f"Request {r.request_id} is now {r.request_status.lower()}.")


# ---------------------------------------------------------------- security alerts
@app.get("/alerts")
def alerts_page(request: Request, risk: str = "All", focus: str | None = None,
                user: User = Depends(current_member), db: Session = Depends(get_db)):
    events = (db.query(SecurityEvent).filter_by(user_id=user.user_id)
              .order_by(SecurityEvent.event_time.desc()).all())
    shown = [e for e in events if risk not in LEVELS or e.risk_level == risk]
    open_events = [e for e in events if e.is_suspicious == "Yes" and e.resolution is None]
    top = next((e for e in events if e.event_id == focus), None) or \
        next((e for e in sorted(open_events, key=lambda e: -RISK_ORDER[e.risk_level])), None)
    assets = db.query(DigitalAsset).filter_by(user_id=user.user_id).all()
    cities = sorted({f"{c}, {s}" for c, s in db.query(User.city, User.state).filter(User.is_admin.is_(False)).distinct()})
    return page(request, "alerts.html", user, db, active="alerts", events=shown, risk=risk, top=top,
                reasons=event_reasons(top, top.asset, user) if top else [], assets=assets,
                event_types=EVENT_TYPES, devices=DEVICES, cities=cities, home=f"{user.city}, {user.state}")


@app.post("/alerts/{event_id}/resolve")
def resolve_alert(event_id: str, answer: str = Form(...), user: User = Depends(current_member), db: Session = Depends(get_db)):
    e = owned(db, SecurityEvent, event_id, user)
    if answer == "me":
        e.resolution = "Confirmed by owner"
        msg = "Thanks — marked as your own activity."
    elif answer == "not_me":
        e.resolution = "Owner secured account"
        e.asset.management_status, e.asset.last_reviewed_on = "Under Review", date.today()
        msg = (f"“{e.asset.asset_label}” is now under review. Change its password and sign out other "
               f"sessions with the provider.")
    else:
        return go("/alerts", err="Unknown answer.")
    db.commit()
    return go("/alerts", msg=msg)


@app.post("/alerts/simulate")
def simulate_event(asset_id: str = Form(...), event_type: str = Form(...), location_region: str = Form(...),
                   device_category: str = Form(...), is_new_device: str = Form("No"), hour: int = Form(...),
                   failed_attempt_count: int = Form(0), user: User = Depends(current_member), db: Session = Depends(get_db)):
    """Create a simulated event and score it with the rule engine - useful for live demos."""
    asset = owned(db, DigitalAsset, asset_id, user)
    try:
        etype = pick(event_type, EVENT_TYPES, "event type")
        device = pick(device_category, DEVICES, "device")
        if not (0 <= hour <= 23 and 0 <= failed_attempt_count <= 50):
            raise ValueError("Hour must be 0-23 and failed attempts 0-50.")
        if not re.fullmatch(r"[A-Za-z .]+, [A-Za-z .]+", location_region):
            raise ValueError("Pick a location from the list.")
    except ValueError as e:
        return go("/alerts", err=str(e))
    if etype == "Repeated Failed Login":
        failed_attempt_count = max(failed_attempt_count, 3)
    new_dev = is_new_device == "Yes"
    away = location_region != f"{user.city}, {user.state}"
    when = datetime.now().replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)
    risk, susp, action = score_event(etype, failed_attempt_count, away, new_dev, hour, asset, user)
    eid = next_id(db, SecurityEvent, SecurityEvent.event_id, "E")
    db.add(SecurityEvent(event_id=eid, user_id=user.user_id, asset_id=asset.asset_id, event_type=etype, event_time=when,
                         device_category=device, is_new_device="Yes" if new_dev else "No", location_region=location_region,
                         failed_attempt_count=failed_attempt_count, is_suspicious=susp, risk_level=risk,
                         recommended_action=action, data_origin="SIMULATED (live demo)"))
    db.commit()
    return go(f"/alerts?focus={eid}", msg=f"Simulated event {eid} scored as {risk} risk → {action}.")


# ---------------------------------------------------------------- admin
@app.get("/admin")
def admin_page(request: Request, q: str = "", user: User = Depends(current_admin), db: Session = Depends(get_db)):
    users_q = db.query(User).filter(User.is_admin.is_(False))
    if q.strip():
        like = f"%{q.strip()}%"
        users_q = users_q.filter((User.full_name.ilike(like)) | (User.city.ilike(like)) |
                                 (User.state.ilike(like)) | (User.user_id.ilike(like)))
    users = users_q.order_by(User.user_id).all()
    asset_n = dict(db.query(DigitalAsset.user_id, func.count()).group_by(DigitalAsset.user_id).all())
    contact_n = dict(db.query(TrustedContact.user_id, func.count()).group_by(TrustedContact.user_id).all())
    open_n = dict(db.query(SecurityEvent.user_id, func.count()).filter(
        SecurityEvent.is_suspicious == "Yes", SecurityEvent.resolution.is_(None)).group_by(SecurityEvent.user_id).all())
    risk_counts = dict(db.query(SecurityEvent.risk_level, func.count()).group_by(SecurityEvent.risk_level).all())
    totals = {
        "users": db.query(User).filter(User.is_admin.is_(False)).count(),
        "assets": db.query(DigitalAsset).count(),
        "unmanaged": db.query(DigitalAsset).filter(DigitalAsset.management_status == "Unmanaged").count(),
        "no_mfa": db.query(DigitalAsset).filter(DigitalAsset.mfa_enabled != "Yes").count(),
        "contacts": db.query(TrustedContact).count(),
        "pending_requests": db.query(AccessRequest).filter(AccessRequest.request_status == "Pending").count(),
        "events": db.query(SecurityEvent).count(),
    }
    recent_high = (db.query(SecurityEvent).filter(SecurityEvent.risk_level == "High")
                   .order_by(SecurityEvent.event_time.desc()).limit(8).all())
    names = {u.user_id: u.full_name for u in db.query(User)}
    return page(request, "admin.html", user, db, active="admin", users=users, q=q, asset_n=asset_n,
                contact_n=contact_n, open_n=open_n, risk_counts=risk_counts, totals=totals,
                recent_high=recent_high, names=names)
