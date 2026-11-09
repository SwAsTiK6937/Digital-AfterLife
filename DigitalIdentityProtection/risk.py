"""
Rule engines for the prototype.

1. score_event()     - scores a security event and explains WHY (same signals the
                       dataset generator used, without the random noise).
2. evaluate_request() - runs an access request through identity + authority checks.
3. request_checks()  - builds the step-by-step check list shown on the Requests page.

Everything here is a transparent demo rule set, not a real fraud detector.
"""

RISK_ORDER = {"Low": 0, "Medium": 1, "High": 2}

BASE_SCORE = {
    "Normal Activity": 0.0, "Inactive Account Review": 1.4, "Unknown Device": 1.4,
    "Unusual Login": 1.8, "Repeated Failed Login": 1.0, "Unusual Access Request": 2.0,
}


def event_reasons(event, asset, user):
    """Human-readable reasons an event looks risky (used for display)."""
    reasons = []
    home = f"{user.city}, {user.state}"
    if event.is_new_device == "Yes":
        reasons.append(("New device", "Never seen on this account"))
    if event.location_region and event.location_region != home:
        reasons.append(("Away from home", f"{event.location_region.split(',')[0]}, not {user.city}"))
    if event.event_time and event.event_time.hour < 5:
        reasons.append(("Unusual hour", "Between midnight and 5 AM"))
    if (event.failed_attempt_count or 0) >= 3:
        reasons.append(("Repeated failures", f"{event.failed_attempt_count} wrong passwords in a row"))
    if asset.mfa_enabled == "No":
        reasons.append(("No 2-step verification", "Password alone protects it"))
    elif asset.mfa_enabled == "Unknown":
        reasons.append(("2-step status unknown", "You haven't confirmed it's on"))
    if asset.management_status == "Unmanaged":
        reasons.append(("Unmanaged account", "Not reviewed for over a year"))
    if event.related_request_id and event.event_type == "Unusual Access Request":
        reasons.append(("Access request", f"Linked to request {event.related_request_id}"))
    return reasons


def score_event(event_type, failed, away_from_home, new_device, hour, asset, user, unregistered_requester=False):
    """Return (risk_level, is_suspicious, recommended_action)."""
    s = BASE_SCORE[event_type]
    s += 0.18 * failed
    s += 1.0 if away_from_home else 0
    s += 0.7 if new_device else 0
    s += 0.6 if hour < 5 else 0
    s += {"No": 0.6, "Unknown": 0.3, "Yes": -0.3}[asset.mfa_enabled]
    s += {"High": 0.5, "Medium": 0.2, "Low": 0.0}[asset.importance_level]
    s += {"Low": 0.4, "Medium": 0.1, "High": -0.2}[user.account_security_awareness]
    s += 0.5 if asset.management_status == "Unmanaged" else 0
    s += 1.2 if unregistered_requester else 0

    if event_type == "Normal Activity":
        risk = "Low"
    else:
        risk = "Low" if s < 2.4 else ("Medium" if s < 4.3 else "High")
    suspicious = "No" if risk == "Low" else "Yes"

    if risk == "Low":
        action = "Monitor"
    elif event_type == "Unusual Access Request":
        action = "Block Demo Request" if risk == "High" else "Review Request"
    elif event_type == "Inactive Account Review":
        action = "Verify User"
    else:
        action = "Block Demo Request" if (risk == "High" and failed >= 8) else "Verify User"
    return risk, suspicious, action


# Which authority level each request type needs
NEEDED_LEVEL = {
    "View Asset Metadata": "View Metadata",
    "Flag Suspicious Activity": "Submit Request",
    "Request Account Review": "Submit Request",
}


def authority_covers(level, request_type):
    return level == "Submit Request" or (level == "View Metadata" and NEEDED_LEVEL[request_type] == "View Metadata")


def evaluate_request(contact, request_type):
    """
    Decide the starting statuses for a new request.
    Returns (verification_status, authorization_status, request_status).
    The owner makes the final Approve/Deny decision afterwards.
    """
    if contact is None:  # not on the user's trusted list
        return "Rejected", "Denied", "Denied"
    if contact.verification_status == "Not Verified":
        return "Rejected", "Denied", "Denied"
    if contact.verification_status == "Pending":
        return "Pending", "Pending", "Pending"
    if not authority_covers(contact.authorization_level, request_type):
        return "Verified", "Denied", "Denied"
    return "Verified", "Pending", "Pending"  # waits for the owner's decision


def request_checks(req):
    """Step list for the UI: each step is (state, title, detail); state = ok | fail | wait | skip."""
    c = req.contact
    steps = []
    # Step 1 - identity
    if c is None:
        steps.append(("fail", "Identity check failed", "The requester is not on your trusted contact list."))
    elif req.verification_status == "Verified":
        steps.append(("ok", "Identity verified", f"{c.contact_name} is a verified trusted contact."))
    elif req.verification_status == "Pending":
        steps.append(("wait", "Identity check pending", f"{c.contact_name} hasn't finished verification yet."))
    else:
        steps.append(("fail", "Identity check failed", f"{c.contact_name} is not verified."))

    # Step 2 - authority
    if req.verification_status != "Verified":
        steps.append(("skip", "Authority check", "Skipped until identity is verified."))
    elif authority_covers(c.authorization_level, req.request_type):
        steps.append(("ok", "Authority matches the request",
                      f"“{c.authorization_level}” covers “{req.request_type}”."))
    elif req.authorization_status == "Denied" and c.authorization_level != "No Authorization" and \
            not authority_covers(c.authorization_level, req.request_type):
        steps.append(("fail", "Authority too low",
                      f"“{c.authorization_level}” does not cover “{req.request_type}”."))
    else:
        steps.append(("fail", "No authority", "This contact has no authorization level."))

    # Step 3 - owner's decision
    final = {
        "Approved": ("ok", "Approved", "The asset was flagged as requested. No login details were shared."),
        "Closed": ("ok", "Closed", "This request is finished."),
        "Denied": ("fail", "Denied", "Nothing was shared with the requester."),
        "Pending": ("wait", "Waiting for your decision", "Approve or deny this request below."),
    }[req.request_status]
    if req.request_status == "Closed" and req.authorization_status == "Denied":
        final = ("fail", "Denied and closed", "Nothing was shared with the requester.")
    if req.request_status == "Pending" and req.verification_status == "Pending":
        final = ("skip", "Your decision", "Available once identity is verified.")
    steps.append(final)
    return steps
