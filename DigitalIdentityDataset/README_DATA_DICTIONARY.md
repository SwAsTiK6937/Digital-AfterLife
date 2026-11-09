# Synthetic Indian Dataset — Digital Identity Protection System

> **Every record in this dataset is fictional and simulated.** No real person's data was
> scraped, collected or reproduced. Names are random combinations of common Indian given names
> and surnames; any resemblance to a real person is coincidental. Security events are
> simulated and are not real cyber incidents.

## 1. What's in the folder

| File | Rows | Purpose |
|---|---|---|
| `data/users.csv` | 100 | Fictional Indian users |
| `data/digital_assets.csv` | 329 | Accounts each user registered (metadata only) |
| `data/trusted_contacts.csv` | 107 | People a user trusts, with verification and authority level |
| `data/access_requests.csv` | 80 | Requests to view or act on a user's asset |
| `data/security_events.csv` | 420 | Simulated security monitoring events |
| `data/ml_security_events.csv` | 420 | Same events, flattened into ML features + labels |
| `generate_dataset.py` | — | Rebuilds every file (fixed seed = 42, standard library only) |
| `validate_dataset.py` | — | 41 automatic checks for integrity, logic and privacy |

Run with `python generate_dataset.py`, then `python validate_dataset.py`. The same seed always gives exactly the same data.

## 2. Application database vs ML dataset (simple explanation)

- **The application database files** (the first five CSVs) are what your FastAPI + SQLite app loads to show
  dashboards, assets, contacts and requests. They're split into separate tables linked by IDs,
  the same way your `models.py` is structured.
- **The ML dataset** (`ml_security_events.csv`) is one big flat table where each row is one event
  described with numbers and categories, plus the "answer" columns (`target_*`) a model learns to predict.
  It holds no IDs and no names, because a model shouldn't learn from those.

## 3. How the tables connect

```
users (user_id)
 ├── digital_assets (asset_id, user_id)
 ├── trusted_contacts (contact_id, user_id)
 ├── access_requests (request_id, user_id, asset_id, contact_id?)
 │        └── security_events.related_request_id
 └── security_events (event_id, user_id, asset_id)
                └── ml_security_events (event_id, features + targets)
```

A request's `asset_id` and `contact_id` always belong to **the same user**. This is the
access-control rule your app must also enforce.

## 4. Data dictionary

### users.csv
| Column | Type | Values / meaning |
|---|---|---|
| user_id | text | `U0001`… |
| full_name | text | Fictional Indian name, drawn from a name pool for the user's region (15% mixed pan-India) |
| age | int | 18–74, centred around 33 |
| city, state | text | Broad city + state/UT label only (22 states/UTs) |
| preferred_language | text | Regional language / English / Hindi, weighted by state |
| occupation_category | text | Broad category; students are ≤30, retired users ≥55 |
| digital_literacy_level | Low/Medium/High | Derived from age + occupation + noise |
| account_security_awareness | Low/Medium/High | Correlated with literacy, but not identical |
| created_at | date | 2024-01-01 to 2025-12-31 |

### digital_assets.csv
| Column | Type | Values / meaning |
|---|---|---|
| asset_id, user_id | text | `A0001`; owner link |
| asset_category | text | Email, Social Media, Cloud Storage, Shopping, Subscription, Website/Domain, Financial Service, Other |
| platform_name | text | **Generic label** (e.g. "UPI Payment App"), never a real brand, so no integration is implied |
| asset_label | text | Friendly label ("Photo backup") |
| importance_level | Low/Medium/High | Email & Financial are always High |
| management_status | text | Active (0–179 days since review), Inactive (180–720), Unmanaged (366+), Under Review (0–29) |
| mfa_enabled | Yes/No/Unknown | Most likely on financial accounts, least likely on subscriptions |
| last_reviewed_days_ago | int | Consistent with status |
| contains_sensitive_data | Yes/No/Unknown | Yes for Email/Financial/Cloud |

Every user has at least one Email asset, because email is the recovery root for most other accounts.

### trusted_contacts.csv
| Column | Type | Values / meaning |
|---|---|---|
| contact_id, user_id | text | `C0001`; owner link |
| contact_name | text | Fictional; Family contacts share the user's surname 60% of the time |
| relationship_category | text | Family, Friend, Colleague, Other |
| verification_status | text | Verified, Pending, Not Verified |
| authorization_level | text | View Metadata / Submit Request (only if Verified); otherwise No Authorization |
| contact_email | text | `contactNNNN@example.com` (reserved domain) |
| added_on | date | Always after the user's `created_at` |

### access_requests.csv
| Column | Type | Values / meaning |
|---|---|---|
| request_id, user_id, asset_id | text | `R0001`; links |
| contact_id | text | Blank when the requester is not a registered trusted contact |
| requester_type | text | Trusted Contact / Unregistered Requester |
| request_type | text | View Asset Metadata, Flag Suspicious Activity, Request Account Review |
| request_reason | text | Short fictional reason; unregistered ones mimic social-engineering patterns |
| request_date | date | 2026, after the contact was added |
| verification_status | text | Pending, Verified, Rejected |
| authorization_status | text | Pending, Approved, Denied |
| request_status | text | Pending, Approved, Denied, Closed |

**Status rules (always followed):**
- Pending verification → Pending authorization → Pending request
- Rejected verification → Denied → Denied or Closed
- Verified → Approved only if the contact's authority covers the request type
  (View Metadata covers only "View Asset Metadata"; Submit Request covers everything)
- Unregistered requesters are **never** approved

### security_events.csv
| Column | Type | Values / meaning |
|---|---|---|
| event_id, user_id, asset_id | text | `E0001`… (sorted by time); asset always belongs to the user |
| event_type | text | Normal Activity, Unusual Login, Repeated Failed Login, Unknown Device, Unusual Access Request, Inactive Account Review |
| event_time | datetime | 2026-01-01 to 2026-10-31 |
| device_category | text | Mobile, Desktop, Tablet, Unknown |
| is_new_device | Yes/No | Always Yes for Unknown Device events |
| location_region | text | "City, State" only, with no coordinates |
| failed_attempt_count | int | ≥3 for Repeated Failed Login |
| is_suspicious | Yes/No | No ⇔ risk Low |
| risk_level | Low/Medium/High | From a hidden weighted score + random noise |
| recommended_action | text | Low→Monitor; access-request events→Review Request / Block Demo Request; others→Verify User (Block if High + ≥8 failures) |
| related_request_id | text | Links Unusual Access Request events to the request that triggered them |
| data_origin | text | Always `SIMULATED` |

**How risk is decided:** event type, logins away from the home city, new device, night-time
(00:00–04:59), no/unknown MFA, high-importance asset, low user awareness, unmanaged asset and
unregistered requester all add to a score. Random noise is then added, so the labels follow
the logic without being perfectly mechanical. Normal Activity is always Low risk.

### ml_security_events.csv
Features: `event_type, hour_of_day, is_night_time, day_of_week, device_category, is_new_device,
location_matches_home, failed_attempt_count, asset_category, asset_importance,
asset_management_status, asset_mfa_enabled, asset_last_reviewed_days_ago, user_age,
user_digital_literacy, user_security_awareness, from_unregistered_requester`

Targets: `target_is_suspicious` (binary) or `target_risk_level` (3-class). Pick **one** target and
never use the other target or `recommended_action` as a feature (that would be target leakage).
Drop `event_id` before training.

## 5. Distribution snapshot (seed 42)

- Risk levels: Low 210 · Medium 123 · High 87. Suspicious: 50% (balanced on purpose for the demo)
- Assets: Active 184 · Inactive 75 · Unmanaged 52 · Under Review 18
- MFA: Yes 132 · No 141 · Unknown 56
- Requests: Pending 28 · Denied 25 · Closed 14 · Approved 13 (12 from unregistered requesters)

**Baseline check (25% stratified test split):** Random Forest scores about 93% accuracy on
`target_is_suspicious` and about 82% on `target_risk_level`. The data is learnable but not
trivially separable.

## 6. Limitations (state these in your report)

1. **Synthetic ≠ real-world evidence.** The patterns come from rules the generator encodes. A model
   trained on this data learns those rules, and **cannot** be claimed to detect real fraud.
2. **Class balance is artificial.** Real suspicious events are a tiny fraction of all activity. Here it's
   50% so a small demo model has enough examples of both classes.
3. **Names may coincide with real people.** Common Indian names are shared by many real individuals; a
   blocklist removes well-known public-figure combinations, but the names refer to no one.
4. **Regional name pools are a realism choice only.** No religion, caste, ethnicity or other sensitive
   attribute is recorded or implied.
5. **No real credentials, IDs, phone numbers, addresses or personal emails** appear anywhere
   (verified automatically by `validate_dataset.py`).
