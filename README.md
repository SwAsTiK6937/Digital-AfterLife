# Digital AfterLife — Persistent Digital Identity Protection

A prototype system that helps people keep track of their online accounts, name trusted
contacts who can act for them, and catch suspicious activity before it turns into account
takeover. It's built for the problem of *what happens to your digital identity* when you
stop managing it, through neglect, illness or death.

The repository has two parts:

| Folder | What it is |
|---|---|
| [`DigitalIdentityProtection/`](DigitalIdentityProtection/) | **Identity Shield**: a working FastAPI + SQLite web app |
| [`DigitalIdentityDataset/`](DigitalIdentityDataset/) | A reproducible **synthetic Indian dataset** (100 users) that feeds the app, plus an ML-ready table |

> **All data is fictional.** No real person's data was collected. Platform names are generic
> labels (e.g. "UPI Payment App"), and the app doesn't connect to any real service.

---

## Features

- **Digital asset register.** Record email, social, cloud, financial and other accounts, along
  with importance, 2-step verification status and when each was last reviewed. Any text that
  looks like a password, OTP, Aadhaar/PAN or phone number is rejected, so secrets never get stored.
- **Trusted contacts.** Add people you trust, verify them, and give each one an authority level.
- **Access requests.** Every request to view or act on an asset goes through identity and
  authority checks. Requests from someone who isn't a trusted contact are denied automatically
  and raise an alert.
- **Explainable security alerts.** A rule engine scores each event (new device, away from home,
  unusual hour, repeated failures, no 2-step verification, unmanaged account…) and shows
  *why* it was flagged, with a "Was this you?" response.
- **Personal dashboard.** Live stats, a "Needs your attention" list, asset-health bars and
  recent activity.
- **Admin view.** A read-only overview of all users with system-wide risk counts.
- **Simulators.** Trigger incoming requests and security events to watch the rules work live.

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy · SQLite · Jinja2 · argon2 password hashing (pwdlib) ·
HMAC-signed session cookies

---

## Quick start

```bash
git clone https://github.com/SwAsTiK6937/Digital-AfterLife.git
cd Digital-AfterLife/DigitalIdentityProtection
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open <http://127.0.0.1:8000>. On first start the app builds `identity.db` from the CSVs in
`data/`, which takes about 15 seconds. Run `python seed.py` any time to reset all data.

### Demo logins

| Role | Email | Password |
|---|---|---|
| Any dataset user | `firstname.lastname@example.com` (e.g. `parth.patel@example.com`) | `Demo@1234` |
| User with a blocked request | `priya.sharma@example.com` | `Demo@1234` |
| Administrator | `admin@example.com` | `Admin@1234` |

The login page has one-click buttons that fill these in.

### Run the tests

```bash
cd DigitalIdentityProtection
python test_app.py               # 38 end-to-end checks
```

```bash
cd DigitalIdentityDataset
python generate_dataset.py       # rebuild every CSV (fixed seed 42, standard library only)
python validate_dataset.py       # 41 integrity, logic and privacy checks
```

---

## Project structure

```
Digital-AfterLife/
├── DigitalIdentityProtection/        # Web application
│   ├── main.py                       # Routes; every query is scoped to the logged-in user
│   ├── auth.py                       # Password hashing, signed cookie, login lockout
│   ├── models.py                     # SQLAlchemy tables
│   ├── risk.py                       # Explainable risk scoring and request checks
│   ├── database.py                   # Engine and session setup
│   ├── seed.py                       # Loads data/*.csv into identity.db, creates demo logins
│   ├── test_app.py                   # End-to-end tests
│   ├── data/                         # CSVs the app loads
│   ├── templates/                    # Jinja2 pages
│   └── static/style.css
└── DigitalIdentityDataset/           # Synthetic dataset
    ├── generate_dataset.py
    ├── validate_dataset.py
    ├── README_DATA_DICTIONARY.md     # Full column-by-column data dictionary
    └── data/
        ├── users.csv                 # 100 users
        ├── digital_assets.csv        # 329 assets
        ├── trusted_contacts.csv      # 107 contacts
        ├── access_requests.csv       # 80 requests
        ├── security_events.csv       # 420 events
        └── ml_security_events.csv    # Same events as ML features + target labels
```

### How the data connects

```
users (user_id)
 ├── digital_assets (asset_id, user_id)
 ├── trusted_contacts (contact_id, user_id)
 ├── access_requests (request_id, user_id, asset_id, contact_id?)
 │        └── security_events.related_request_id
 └── security_events (event_id, user_id, asset_id)
                └── ml_security_events (event_id, features + targets)
```

See [`README_DATA_DICTIONARY.md`](DigitalIdentityDataset/README_DATA_DICTIONARY.md) for every column.

---

## Security design

- **Per-user access control.** Every route loads records through `owned()`, which returns 404
  for anything belonging to another user. Tests cover this.
- **Passwords** are hashed with argon2. Five wrong attempts lock the account for 5 minutes.
- **Sessions** use an HMAC-signed cookie (8-hour lifetime) with a random key kept in
  `.secret_key`, which is never committed. A tampered cookie logs the user out.
- **No secrets stored.** The asset register blocks anything that looks like a credential or
  government ID.

### Known prototype limitations

This is a demo, not a production system:

- All dataset users share one demo password.
- There's no CSRF token; SameSite=Lax cookies reduce the risk.
- The lockout counter lives in memory and resets when the server restarts.
- The app runs over plain HTTP locally.
- Risk scoring is a transparent rule set, not a validated fraud-detection model.

---

## Author

**Swastik** ([@SwAsTiK6937](https://github.com/SwAsTiK6937))
