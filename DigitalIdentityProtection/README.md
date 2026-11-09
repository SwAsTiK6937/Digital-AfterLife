# Identity Shield — Digital Identity Protection System (prototype)

A working FastAPI + SQLite web app for the project *Persistent Digital Identity Protection*.
All 100 users, their assets, contacts, requests and security events come from the
**synthetic** dataset in `data/`. Nothing connects to a real service.

## Run it (Windows, VS Code terminal)

```bash
cd DigitalIdentityProtection
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000. The first start builds `identity.db` from the CSVs (~15 seconds).
To reset all data any time: `python seed.py`.

## Demo logins

| Who | Email | Password |
|---|---|---|
| Any dataset user (e.g. Parth Patel) | `firstname.lastname@example.com` | `Demo@1234` |
| Priya Sharma (has a blocked request) | `priya.sharma@example.com` | `Demo@1234` |
| Administrator | `admin@example.com` | `Admin@1234` |

The login page has one-click buttons that fill these in.

## What works

| Page | Features |
|---|---|
| Sign in | argon2-hashed passwords, signed session cookie (8 h), 5 wrong attempts → 5-minute lock |
| Dashboard | Live stats, "Needs your attention" list built from your data, asset-health bars, recent activity |
| Digital assets | Filter by status, register an asset, update 2-step/status, mark reviewed, remove. Text that looks like a password, OTP, Aadhaar/PAN or phone number is rejected |
| Trusted contacts | Add (only `@example.com/.org` emails), send verification, simulate the contact verifying, set authority, remove |
| Access requests | Request list + detail showing the 3 checks; approve / deny / close / revoke; **simulate an incoming request** (try "Someone not on my trusted list": it's auto-denied and raises an alert) |
| Security alerts | Top open alert with *why it was flagged*, "Was this you?" answers, risk filter, **simulate an event** and see the rule engine score it |
| Admin | Read-only overview of all 100 users, search, system-wide risk counts |

## Files

```
main.py       routes (every query is filtered by the logged-in user's ID)
auth.py       password hashing, signed cookie, login lockout
models.py     SQLAlchemy tables
risk.py       explainable risk-scoring and request-checking rules
seed.py       loads data/*.csv into identity.db and creates demo logins
test_app.py   38 automated end-to-end checks:  python test_app.py
templates/    Jinja2 pages        static/style.css   styles
```

## Security notes for your report

- **Access control:** a user can't view or change another user's records. Every route loads rows
  through `owned()`, which returns 404 for records belonging to someone else (tested).
- **Sessions:** the cookie is HMAC-signed with a random key in `.secret_key`. Editing it logs you out (tested).
- **Known demo limitations:** all dataset users share one demo password; there's no CSRF token
  (SameSite=Lax cookies reduce the risk); the lockout counter lives in memory and resets on restart;
  the app runs over HTTP locally. A production system would need to fix all four.
- **Risk scoring is rule-based** and uses the same signals as the dataset generator. It shows the
  workflow; it is not a validated fraud detector.
