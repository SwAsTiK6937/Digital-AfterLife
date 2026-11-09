"""
Synthetic dataset generator - Digital Identity Protection System
=================================================================
Every person, name, email, event and request produced here is FICTIONAL.
No real data is scraped, collected or reproduced. Only Python's standard
library is used, so this runs on any Python 3.10+ (including 3.12.8).

Run:   python generate_dataset.py
Output: ./data/*.csv   (same output every time because SEED is fixed)
"""

import csv
import math
import os
import random
from datetime import datetime, timedelta

SEED = 42
N_USERS = 100
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

rng = random.Random(SEED)


# ----------------------------------------------------------------------------
# 1. Name pools (fictional combinations of common given names and surnames)
# ----------------------------------------------------------------------------
NAMES = {
    "hindi": (
        ["Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Ishaan", "Ankit", "Vikas",
         "Saurabh", "Nikhil", "Manish", "Deepak", "Gaurav", "Harsh", "Kunal", "Abhishek",
         "Ananya", "Priya", "Neha", "Pooja", "Shreya", "Ritika", "Anjali", "Swati",
         "Nidhi", "Megha", "Divya", "Tanvi", "Aditi", "Sakshi", "Komal", "Pallavi"],
        ["Sharma", "Verma", "Gupta", "Mishra", "Pandey", "Tiwari", "Srivastava", "Yadav",
         "Chauhan", "Agarwal", "Saxena", "Joshi", "Malhotra", "Khanna", "Bhatia", "Dubey",
         "Rastogi", "Tripathi", "Chaturvedi", "Sinha", "Rawat", "Negi", "Bisht", "Mehra"],
    ),
    "punjabi": (
        ["Harpreet", "Gurpreet", "Jaspreet", "Mandeep", "Navjot", "Simran", "Amandeep",
         "Rajveer", "Manpreet", "Kiranjot", "Arshdeep", "Gurleen", "Jasleen", "Parminder"],
        ["Gill", "Sandhu", "Dhillon", "Sidhu", "Grewal", "Bajwa", "Brar", "Virk",
         "Randhawa", "Ahluwalia", "Bedi", "Sethi", "Arora", "Chawla"],
    ),
    "marathi": (
        ["Siddharth", "Omkar", "Tejas", "Prathamesh", "Aniket", "Shubham", "Mayur",
         "Sayali", "Ketaki", "Mrunal", "Gauri", "Rutuja", "Snehal", "Aishwarya", "Prajakta"],
        ["Kulkarni", "Deshpande", "Patil", "Jadhav", "Pawar", "Shinde", "Gokhale",
         "Joshi", "Bhosale", "Kale", "Deshmukh", "Sawant", "Apte", "Gaikwad", "More"],
    ),
    "gujarati": (
        ["Hardik", "Jignesh", "Parth", "Dhruv", "Chirag", "Kunal", "Nirav", "Bhavin",
         "Hetal", "Krupa", "Dhwani", "Riddhi", "Nisha", "Foram", "Khushi", "Janvi"],
        ["Patel", "Shah", "Mehta", "Desai", "Parikh", "Trivedi", "Vyas", "Modi",
         "Pandya", "Chokshi", "Gandhi", "Thakkar", "Dave", "Bhatt", "Soni"],
    ),
    "tamil": (
        ["Karthik", "Arun", "Vignesh", "Prakash", "Saravanan", "Dinesh", "Hari",
         "Surya", "Balaji", "Gokul", "Lakshmi", "Divya", "Keerthana", "Priyadharshini",
         "Nandhini", "Revathi", "Sowmya", "Janani", "Meenakshi", "Aishwarya"],
        ["Subramanian", "Ramesh", "Krishnan", "Raghavan", "Venkatesan", "Murugan",
         "Sundaram", "Natarajan", "Rajendran", "Srinivasan", "Shanmugam", "Kannan",
         "Balasubramanian", "Ganesan", "Selvam", "Anand"],
    ),
    "telugu": (
        ["Srinivas", "Venkat", "Ravi", "Kiran", "Sai", "Pavan", "Chaitanya", "Naveen",
         "Harika", "Lavanya", "Sravani", "Bhavya", "Keerthi", "Swathi", "Mounika", "Sirisha"],
        ["Reddy", "Rao", "Naidu", "Chowdary", "Varma", "Raju", "Prasad", "Kumar",
         "Goud", "Murthy", "Sastry", "Nalla", "Kondapalli", "Yerramsetti"],
    ),
    "kannada": (
        ["Manjunath", "Shreyas", "Darshan", "Pradeep", "Nagaraj", "Vinay", "Chethan",
         "Shwetha", "Rashmi", "Chaitra", "Deepika", "Pavithra", "Spoorthi", "Bhoomika"],
        ["Gowda", "Hegde", "Shetty", "Rao", "Kamath", "Bhat", "Naik", "Kulkarni",
         "Acharya", "Shenoy", "Prabhu", "Murthy", "Hiremath"],
    ),
    "malayalam": (
        ["Arjun", "Anoop", "Vishnu", "Akhil", "Rahul", "Nithin", "Sreejith", "Jithin",
         "Anjali", "Aswathy", "Athira", "Gopika", "Neethu", "Reshma", "Sreelakshmi", "Nimisha"],
        ["Nair", "Menon", "Pillai", "Kurup", "Panicker", "Warrier", "Nambiar",
         "Thomas", "Varghese", "Kurian", "Mathew", "Jacob", "Unnikrishnan", "Mohan"],
    ),
    "bengali": (
        ["Arnab", "Sourav", "Debashish", "Abhijit", "Sayan", "Rajdeep", "Anirban",
         "Subhajit", "Moumita", "Payel", "Sohini", "Rituparna", "Tanushree", "Ishita", "Sreya"],
        ["Banerjee", "Chatterjee", "Mukherjee", "Bose", "Ghosh", "Das", "Sen", "Dutta",
         "Roy", "Chakraborty", "Bhattacharya", "Saha", "Mitra", "Sarkar"],
    ),
    "odia": (
        ["Subhasis", "Debasish", "Pritam", "Sambit", "Ashutosh", "Biswajit",
         "Sasmita", "Lipika", "Smruti", "Sonali", "Itishree", "Bandana"],
        ["Mohanty", "Patnaik", "Panda", "Mishra", "Sahoo", "Pradhan", "Rout",
         "Behera", "Jena", "Dash", "Nayak", "Swain"],
    ),
    "assamese": (
        ["Bhaskar", "Dhruba", "Pranjal", "Manash", "Rupam", "Nayan",
         "Jahnavi", "Pallabi", "Bornali", "Mridusmita", "Dikshita", "Gitanjali"],
        ["Baruah", "Gogoi", "Bora", "Saikia", "Kalita", "Hazarika", "Phukan",
         "Deka", "Sarma", "Choudhury", "Medhi", "Talukdar"],
    ),
    "konkani": (
        ["Rohit", "Sanket", "Nilesh", "Cyril", "Ashwin", "Pratik",
         "Shweta", "Neelam", "Sheryl", "Riya", "Sneha", "Glenda"],
        ["Naik", "Kamat", "Prabhu", "Fernandes", "D'Souza", "Pereira", "Gaonkar",
         "Desai", "Rodrigues", "Sardesai", "Borkar", "Lobo"],
    ),
    "khasi": (
        ["Wanphrang", "Banshan", "Ibashisha", "Daphisha", "Kyrshan", "Iohborlang",
         "Wanbiang", "Badaplin", "Ridalin", "Aiti"],
        ["Lyngdoh", "Syiem", "Kharkongor", "Marbaniang", "Nongrum", "Lyngkhoi",
         "Kharbuli", "Rymbai", "Nongbri", "Kharshiing"],
    ),
    # Mixed pan-India pool, blended into every region for realistic diversity.
    "pan_india": (
        ["Imran", "Farhan", "Sameer", "Zaid", "Adil", "Irfan", "Ayesha", "Sana", "Zoya",
         "Fatima", "Nazia", "Rukhsar", "Joseph", "Kevin", "Sharon", "Grace", "Rhea",
         "Tenzin", "Pema", "Rustom", "Zarine", "Aman", "Ravi", "Kavya", "Meera", "Rahul"],
        ["Siddiqui", "Qureshi", "Ansari", "Shaikh", "Mirza", "Hussain", "Rizvi",
         "Fernandes", "D'Costa", "Pinto", "Mascarenhas", "Dsouza", "Wangchuk", "Dolma",
         "Irani", "Contractor", "Kumar", "Singh", "Khan", "Ali"],
    ),
}

# Exact name combinations that belong to well-known public figures.
# Any generated name in this list is rejected and regenerated.
BLOCKLIST = {
    "Virat Kohli", "Sachin Tendulkar", "Narendra Modi", "Rahul Gandhi", "Imran Khan",
    "Amitabh Bachchan", "Shah Rukh Khan", "Salman Khan", "Aamir Khan", "Priyanka Chopra",
    "Deepika Padukone", "Ratan Tata", "Mukesh Ambani", "Sundar Pichai", "Rahul Dravid",
    "Sourav Ganguly", "Arijit Singh", "Sania Mirza", "Kiran Bedi", "Hardik Pandya",
    "Ravi Shastri", "Sonia Gandhi", "Arvind Kejriwal", "Mamata Banerjee", "Rohit Sharma",
    "Ayesha Takia", "Sameer Wankhede", "Ravi Kumar", "Rahul Kumar", "Amit Shah",
    "Mahatma Gandhi", "Indira Gandhi", "Neeraj Chopra", "Kapil Dev", "Yuvraj Singh",
    "Harbhajan Singh", "Manmohan Singh", "Rajinikanth", "Kamal Haasan", "Mohan Lal",
    "Shreya Ghoshal", "Smriti Mandhana", "Mithali Raj", "Saina Nehwal", "Pv Sindhu",
    "Rajeev Chandrasekhar", "Nandan Nilekani", "Azim Premji", "Kiran Mazumdar",
    "Gautam Adani", "Anand Mahindra", "Sudha Murthy", "Narayana Murthy", "Arjun Kapoor",
    "Sonam Kapoor", "Kareena Kapoor", "Ranbir Kapoor", "Varun Dhawan", "Ayushmann Khurrana",
    "Kunal Kapoor", "Riya Sen", "Moumita Das", "Sourav Das", "Abhijit Banerjee",
    "Rajdeep Sardesai", "Prakash Raj", "Arjun Reddy", "Manpreet Gill", "Gurpreet Ghuggi",
}

# ----------------------------------------------------------------------------
# 2. Broad locations: state -> (cities, weight, name pools, language mix)
# ----------------------------------------------------------------------------
LOCATIONS = {
    "Delhi":          (["New Delhi"], 8, ["hindi", "punjabi"], [("Hindi", .55), ("English", .40), ("Punjabi", .05)]),
    "Uttar Pradesh":  (["Lucknow", "Kanpur", "Noida", "Varanasi"], 9, ["hindi"], [("Hindi", .75), ("English", .25)]),
    "Rajasthan":      (["Jaipur", "Jodhpur", "Udaipur"], 4, ["hindi"], [("Hindi", .75), ("English", .25)]),
    "Madhya Pradesh": (["Bhopal", "Indore"], 4, ["hindi"], [("Hindi", .75), ("English", .25)]),
    "Bihar":          (["Patna"], 3, ["hindi"], [("Hindi", .80), ("English", .20)]),
    "Uttarakhand":    (["Dehradun"], 2, ["hindi"], [("Hindi", .70), ("English", .30)]),
    "Punjab":         (["Ludhiana", "Amritsar"], 3, ["punjabi", "hindi"], [("Punjabi", .55), ("Hindi", .20), ("English", .25)]),
    "Chandigarh":     (["Chandigarh"], 2, ["punjabi", "hindi"], [("Punjabi", .35), ("Hindi", .30), ("English", .35)]),
    "Haryana":        (["Gurugram", "Faridabad"], 4, ["hindi", "punjabi"], [("Hindi", .55), ("English", .45)]),
    "Maharashtra":    (["Mumbai", "Pune", "Nagpur", "Nashik"], 11, ["marathi", "gujarati", "hindi"], [("Marathi", .50), ("English", .35), ("Hindi", .15)]),
    "Gujarat":        (["Ahmedabad", "Surat", "Vadodara"], 5, ["gujarati"], [("Gujarati", .65), ("English", .20), ("Hindi", .15)]),
    "Goa":            (["Panaji"], 1, ["konkani"], [("Konkani", .45), ("English", .45), ("Marathi", .10)]),
    "Karnataka":      (["Bengaluru", "Mysuru", "Mangaluru"], 9, ["kannada", "konkani"], [("Kannada", .50), ("English", .45), ("Hindi", .05)]),
    "Tamil Nadu":     (["Chennai", "Coimbatore", "Madurai"], 9, ["tamil"], [("Tamil", .60), ("English", .40)]),
    "Kerala":         (["Kochi", "Thiruvananthapuram", "Kozhikode"], 4, ["malayalam"], [("Malayalam", .60), ("English", .40)]),
    "Telangana":      (["Hyderabad", "Warangal"], 6, ["telugu"], [("Telugu", .55), ("English", .35), ("Hindi", .10)]),
    "Andhra Pradesh": (["Visakhapatnam", "Vijayawada"], 4, ["telugu"], [("Telugu", .70), ("English", .30)]),
    "West Bengal":    (["Kolkata", "Siliguri"], 6, ["bengali"], [("Bengali", .65), ("English", .30), ("Hindi", .05)]),
    "Odisha":         (["Bhubaneswar", "Cuttack"], 2, ["odia"], [("Odia", .65), ("English", .35)]),
    "Jharkhand":      (["Ranchi"], 1, ["hindi", "bengali"], [("Hindi", .70), ("English", .30)]),
    "Assam":          (["Guwahati"], 2, ["assamese"], [("Assamese", .60), ("English", .30), ("Hindi", .10)]),
    "Meghalaya":      (["Shillong"], 1, ["khasi"], [("Khasi", .45), ("English", .55)]),
}

OCCUPATIONS = ["Student", "IT Professional", "Teacher", "Business Owner", "Healthcare Worker",
               "Government Employee", "Sales & Marketing", "Finance Professional",
               "Freelancer", "Homemaker", "Skilled Trades", "Retired"]

# ----------------------------------------------------------------------------
# 3. Generic platform labels (deliberately NOT real brands - no integration implied)
# ----------------------------------------------------------------------------
PLATFORMS = {
    "Email":             [("Generic Webmail Provider", "Personal email"), ("Work Email Service", "Work email"),
                          ("Secondary Webmail Provider", "Backup email")],
    "Social Media":      [("Photo-Sharing Social App", "Photo social profile"), ("Professional Networking Site", "Professional profile"),
                          ("Microblogging Platform", "Public microblog"), ("Messaging App", "Chat account"),
                          ("Video-Sharing Platform", "Video channel")],
    "Cloud Storage":     [("Cloud Drive Service", "Document storage"), ("Photo Backup Service", "Photo backup"),
                          ("Phone Backup Service", "Phone backup")],
    "Shopping":          [("E-commerce Marketplace", "Online shopping"), ("Food Delivery App", "Food orders"),
                          ("Grocery Delivery App", "Grocery orders"), ("Travel Booking Portal", "Train & flight bookings")],
    "Subscription":      [("Video Streaming Service", "Movies & shows"), ("Music Streaming Service", "Music"),
                          ("Online Learning Platform", "Online courses"), ("News Subscription", "Digital newspaper"),
                          ("Gaming Network", "Gaming account")],
    "Website/Domain":    [("Domain Registrar", "Personal domain"), ("Blog Hosting Service", "Personal blog"),
                          ("Portfolio Hosting Service", "Portfolio site")],
    "Financial Service": [("UPI Payment App", "UPI payments"), ("Net Banking Portal", "Savings account portal"),
                          ("Mutual Fund Platform", "Mutual fund investments"), ("Stock Broking App", "Share trading"),
                          ("Insurance Portal", "Insurance policies"), ("Digital Wallet App", "Mobile wallet")],
    "Other":             [("Fitness Tracking App", "Fitness data"), ("Password Manager", "Password vault (metadata only)"),
                          ("Utility Bill Portal", "Electricity bill portal")],
}

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def wchoice(pairs):
    """Weighted choice from [(value, weight), ...]."""
    items, weights = zip(*pairs)
    return rng.choices(items, weights=weights, k=1)[0]


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


used_names = set()


def make_name(pool_keys, surname_override=None):
    """Return a unique fictional name; 15% chance of mixing in the pan-India pool."""
    for _ in range(500):
        key = rng.choice(pool_keys)
        if rng.random() < 0.15:
            key = "pan_india"
        first = rng.choice(NAMES[key][0])
        last = surname_override or rng.choice(NAMES[key][1])
        full = f"{first} {last}"
        if full not in used_names and full not in BLOCKLIST:
            used_names.add(full)
            return full
        surname_override = None  # if forced surname collides, fall back to free choice
    raise RuntimeError("Name pool exhausted")


def rand_date(start, end):
    span = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, span))


LEVEL = ["Low", "Medium", "High"]

# ----------------------------------------------------------------------------
# 4. USERS
# ----------------------------------------------------------------------------
users = []
state_weights = [(s, v[1]) for s, v in LOCATIONS.items()]
for i in range(1, N_USERS + 1):
    state = wchoice(state_weights)
    cities, _, pools, langs = LOCATIONS[state]
    city = rng.choice(cities)

    # Age: adults only, skewed toward 20-45 like India's online population
    age = int(clamp(round(rng.gauss(33, 11)), 18, 74))

    if age <= 24:
        occ = wchoice([("Student", 60), ("IT Professional", 15), ("Freelancer", 10), ("Sales & Marketing", 10), ("Skilled Trades", 5)])
    elif age >= 60:
        occ = wchoice([("Retired", 65), ("Business Owner", 15), ("Teacher", 10), ("Homemaker", 10)])
    else:
        occ = wchoice([(o, 1) for o in OCCUPATIONS if o not in ("Student", "Retired")])

    # Digital literacy: hidden score from age + occupation
    lit = 0.0
    lit += 1.0 if age < 30 else (0.4 if age < 45 else (-0.3 if age < 60 else -1.0))
    lit += {"IT Professional": 1.2, "Student": 0.6, "Freelancer": 0.5, "Finance Professional": 0.5,
            "Sales & Marketing": 0.3, "Teacher": 0.1, "Healthcare Worker": 0.1, "Government Employee": 0.0,
            "Business Owner": 0.0, "Homemaker": -0.5, "Skilled Trades": -0.5, "Retired": -0.6}[occ]
    lit += rng.gauss(0, 0.6)
    literacy = "High" if lit > 1.0 else ("Medium" if lit > -0.2 else "Low")

    # Security awareness follows literacy but not perfectly (high literacy != careful)
    aw = {"Low": -0.8, "Medium": 0.0, "High": 0.7}[literacy] + (0.4 if occ in ("IT Professional", "Finance Professional") else 0) + rng.gauss(0, 0.7)
    awareness = "High" if aw > 0.8 else ("Medium" if aw > -0.4 else "Low")

    created = rand_date(datetime(2024, 1, 1), datetime(2025, 12, 31, 23, 59))
    users.append({
        "user_id": f"U{i:04d}",
        "full_name": make_name(pools),
        "age": age,
        "city": city,
        "state": state,
        "preferred_language": wchoice(langs),
        "occupation_category": occ,
        "digital_literacy_level": literacy,
        "account_security_awareness": awareness,
        "created_at": created.strftime("%Y-%m-%d"),
        "_created": created,
        "_pools": pools,
    })

# ----------------------------------------------------------------------------
# 5. DIGITAL ASSETS (every user has at least one email - email is the root identity)
# ----------------------------------------------------------------------------
assets = []
aid = 0
CAT_WEIGHTS = [("Social Media", 26), ("Shopping", 20), ("Financial Service", 18), ("Subscription", 16),
               ("Cloud Storage", 10), ("Email", 5), ("Website/Domain", 3), ("Other", 4)]
for u in users:
    n_assets = {"Low": rng.randint(2, 3), "Medium": rng.randint(2, 4), "High": rng.randint(3, 5)}[u["digital_literacy_level"]]
    cats = ["Email"] + [wchoice(CAT_WEIGHTS) for _ in range(n_assets - 1)]
    used_platforms = set()
    for cat in cats:
        options = [p for p in PLATFORMS[cat] if p[0] not in used_platforms]
        if not options:
            continue
        platform, label = rng.choice(options)
        used_platforms.add(platform)
        aid += 1

        importance = {"Email": "High", "Financial Service": "High", "Cloud Storage": wchoice([("High", 5), ("Medium", 5)]),
                      "Social Media": wchoice([("Medium", 6), ("Low", 3), ("High", 1)]),
                      "Shopping": wchoice([("Medium", 6), ("Low", 4)]), "Subscription": wchoice([("Low", 7), ("Medium", 3)]),
                      "Website/Domain": wchoice([("Medium", 6), ("High", 2), ("Low", 2)]),
                      "Other": wchoice([("Low", 4), ("Medium", 4), ("High", 2)])}[cat]
        if platform == "Password Manager":
            importance = "High"

        # Management status, with review-age ranges kept logically consistent
        status = wchoice([("Active", 62), ("Inactive", 18), ("Unmanaged", 12), ("Under Review", 8)])
        if u["account_security_awareness"] == "Low" and status == "Active" and rng.random() < 0.25:
            status = "Unmanaged"
        days = {"Active": rng.randint(1, 179), "Inactive": rng.randint(180, 720),
                "Unmanaged": rng.randint(366, 1500), "Under Review": rng.randint(0, 29)}[status]

        # MFA probability depends on category and the user's awareness
        p_mfa = {"Financial Service": 0.85, "Email": 0.55, "Cloud Storage": 0.45, "Social Media": 0.35,
                 "Website/Domain": 0.4, "Shopping": 0.2, "Subscription": 0.1, "Other": 0.3}[cat]
        p_mfa += {"Low": -0.15, "Medium": 0.0, "High": 0.15}[u["account_security_awareness"]]
        r = rng.random()
        mfa = "Yes" if r < clamp(p_mfa, 0.02, 0.97) else ("Unknown" if r < clamp(p_mfa, 0.02, 0.97) + 0.12 else "No")
        if status == "Unmanaged" and mfa == "Yes" and rng.random() < 0.4:
            mfa = "Unknown"  # owner no longer knows how the account is configured

        sens = ("Yes" if cat in ("Email", "Financial Service", "Cloud Storage") or platform == "Password Manager"
                else wchoice([("No", 6), ("Yes", 2), ("Unknown", 2)]))

        assets.append({
            "asset_id": f"A{aid:04d}",
            "user_id": u["user_id"],
            "asset_category": cat,
            "platform_name": platform,
            "asset_label": label,
            "importance_level": importance,
            "management_status": status,
            "mfa_enabled": mfa,
            "last_reviewed_days_ago": days,
            "contains_sensitive_data": sens,
        })

assets_by_user = {}
for a in assets:
    assets_by_user.setdefault(a["user_id"], []).append(a)
asset_by_id = {a["asset_id"]: a for a in assets}
user_by_id = {u["user_id"]: u for u in users}

# ----------------------------------------------------------------------------
# 6. TRUSTED CONTACTS
# ----------------------------------------------------------------------------
contacts = []
cid = 0
for u in users:
    n = wchoice([(0, 30), (1, 40), (2, 22), (3, 8)])
    for _ in range(n):
        cid += 1
        rel = wchoice([("Family", 55), ("Friend", 25), ("Colleague", 12), ("Other", 8)])
        # Family members often (not always) share a surname
        surname = u["full_name"].split(" ", 1)[1] if rel == "Family" and rng.random() < 0.6 else None
        name = make_name(u["_pools"], surname)

        ver = wchoice([("Verified", 60), ("Pending", 25), ("Not Verified", 15)])
        if ver == "Verified":
            auth = wchoice([("View Metadata", 55), ("Submit Request", 45)])
        else:
            auth = "No Authorization"  # unverified people never get authority

        added = rand_date(u["_created"], datetime(2026, 6, 30))
        contacts.append({
            "contact_id": f"C{cid:04d}",
            "user_id": u["user_id"],
            "contact_name": name,
            "relationship_category": rel,
            "verification_status": ver,
            "authorization_level": auth,
            "contact_email": f"contact{cid:04d}@example.com",
            "added_on": added.strftime("%Y-%m-%d"),
            "_added": added,
        })

contacts_by_user = {}
for c in contacts:
    contacts_by_user.setdefault(c["user_id"], []).append(c)

# ----------------------------------------------------------------------------
# 7. ACCESS REQUESTS
# ----------------------------------------------------------------------------
REQ_TYPES = {
    "View Asset Metadata": ["Needs the list of registered accounts to help with an account review",
                            "Wants to confirm which services are registered",
                            "Helping the user organise their digital accounts"],
    "Flag Suspicious Activity": ["Received an odd message that appeared to come from this account",
                                 "Noticed unusual posts on the user's profile",
                                 "Got a payment request that looked suspicious"],
    "Request Account Review": ["User has been unreachable and the account looks unattended",
                               "Account appears inactive for a long time",
                               "Wants the account reviewed as per the user's preferences"],
}
EXTERNAL_REASONS = ["Claims to be a relative and wants account access",
                    "Says they are from customer support and need to verify the account",
                    "Requests login details to 'recover' the account",
                    "Claims the user asked them to manage the account but cannot verify identity",
                    "Urgent request to change the recovery email"]

requests = []
rid = 0
users_with_contacts = [u for u in users if contacts_by_user.get(u["user_id"])]
TARGET_REQUESTS = 80
REQ_START, REQ_END = datetime(2026, 1, 5), datetime(2026, 10, 25)

while rid < TARGET_REQUESTS:
    external = rng.random() < 0.22
    if external:
        u = rng.choice(users)
        contact = None
    else:
        u = rng.choice(users_with_contacts)
        contact = rng.choice(contacts_by_user[u["user_id"]])
    asset = rng.choice(assets_by_user[u["user_id"]])
    rid += 1

    lower = max(REQ_START, contact["_added"] + timedelta(days=1)) if contact else REQ_START
    req_date = rand_date(lower, REQ_END)

    if external:
        req_type = rng.choice(["View Asset Metadata", "Request Account Review"])
        reason = rng.choice(EXTERNAL_REASONS)
        ver = wchoice([("Rejected", 70), ("Pending", 30)])
    else:
        req_type = wchoice([("View Asset Metadata", 45), ("Flag Suspicious Activity", 30), ("Request Account Review", 25)])
        reason = rng.choice(REQ_TYPES[req_type])
        ver = {"Verified": wchoice([("Verified", 85), ("Pending", 15)]),
               "Pending": wchoice([("Pending", 60), ("Rejected", 40)]),
               "Not Verified": wchoice([("Rejected", 75), ("Pending", 25)])}[contact["verification_status"]]

    # Authorization depends on verification AND on the contact's authority level
    needed = "View Metadata" if req_type == "View Asset Metadata" else "Submit Request"
    if ver == "Pending":
        auth, status = "Pending", "Pending"
    elif ver == "Rejected":
        auth = "Denied"
        status = wchoice([("Denied", 70), ("Closed", 30)])
    else:  # Verified trusted contact
        level = contact["authorization_level"]
        sufficient = level == "Submit Request" or (level == "View Metadata" and needed == "View Metadata")
        if not sufficient:
            auth = "Denied"
            status = wchoice([("Denied", 75), ("Closed", 25)])
        else:
            auth = wchoice([("Approved", 80), ("Pending", 20)])
            status = "Pending" if auth == "Pending" else wchoice([("Approved", 65), ("Closed", 35)])

    requests.append({
        "request_id": f"R{rid:04d}",
        "user_id": u["user_id"],
        "asset_id": asset["asset_id"],
        "contact_id": contact["contact_id"] if contact else "",
        "requester_type": "Trusted Contact" if contact else "Unregistered Requester",
        "request_type": req_type,
        "request_reason": reason,
        "request_date": req_date.strftime("%Y-%m-%d"),
        "verification_status": ver,
        "authorization_status": auth,
        "request_status": status,
        "_date": req_date,
        "_external": external,
    })

# ----------------------------------------------------------------------------
# 8. SECURITY EVENTS (simulated)
# ----------------------------------------------------------------------------
EV_START, EV_END = datetime(2026, 1, 1), datetime(2026, 10, 31, 23, 59)
all_regions = [(c, s) for s, v in LOCATIONS.items() for c in v[0]]


def build_event(u, asset, ev_type, when=None, related_request=None):
    home = (u["city"], u["state"])
    when = when or rand_date(EV_START, EV_END)

    # Time of day: unusual events lean toward late night
    if ev_type in ("Unusual Login", "Repeated Failed Login", "Unknown Device") and rng.random() < 0.45:
        when = when.replace(hour=rng.randint(0, 4), minute=rng.randint(0, 59))
    elif ev_type == "Normal Activity":
        when = when.replace(hour=int(clamp(round(rng.gauss(15, 4)), 6, 23)), minute=rng.randint(0, 59))

    away_prob = {"Normal Activity": 0.07, "Unusual Login": 0.75, "Repeated Failed Login": 0.45,
                 "Unknown Device": 0.40, "Unusual Access Request": 0.50, "Inactive Account Review": 0.0}[ev_type]
    region = rng.choice([r for r in all_regions if r != home]) if rng.random() < away_prob else home

    new_dev = {"Normal Activity": rng.random() < 0.05, "Unusual Login": rng.random() < 0.55,
               "Repeated Failed Login": rng.random() < 0.6, "Unknown Device": True,
               "Unusual Access Request": rng.random() < 0.5, "Inactive Account Review": False}[ev_type]

    if ev_type == "Inactive Account Review":
        device = "Unknown"
    else:
        device = wchoice([("Mobile", 62), ("Desktop", 28), ("Tablet", 5), ("Unknown", 5)] if not new_dev
                         else [("Mobile", 45), ("Desktop", 30), ("Tablet", 5), ("Unknown", 20)])

    failed = {"Repeated Failed Login": rng.randint(3, 15)}.get(
        ev_type, wchoice([(0, 80), (1, 15), (2, 5)]) if ev_type != "Inactive Account Review" else 0)

    # ---------- hidden risk score (not exported) ----------
    base = {"Normal Activity": 0.0, "Inactive Account Review": 1.4, "Unknown Device": 1.4,
            "Unusual Login": 1.8, "Repeated Failed Login": 1.0, "Unusual Access Request": 2.0}[ev_type]
    s = base
    s += 0.18 * failed
    s += 1.0 if region != home else 0
    s += 0.7 if new_dev else 0
    s += 0.6 if when.hour < 5 else 0
    s += {"No": 0.6, "Unknown": 0.3, "Yes": -0.3}[asset["mfa_enabled"]]
    s += {"High": 0.5, "Medium": 0.2, "Low": 0.0}[asset["importance_level"]]
    s += {"Low": 0.4, "Medium": 0.1, "High": -0.2}[u["account_security_awareness"]]
    s += 0.5 if asset["management_status"] == "Unmanaged" else 0
    if related_request and related_request["_external"]:
        s += 1.2
    s += rng.gauss(0, 0.55)  # noise: real signals are never perfectly clean

    if ev_type == "Normal Activity":
        risk = "Low"
    else:
        risk = "Low" if s < 2.4 else ("Medium" if s < 4.3 else "High")
    suspicious = "No" if risk == "Low" else "Yes"

    if risk == "Low":
        action = "Monitor"
    elif ev_type == "Unusual Access Request":
        action = "Block Demo Request" if risk == "High" else "Review Request"
    elif ev_type == "Inactive Account Review":
        action = "Verify User"
    else:
        action = "Block Demo Request" if (risk == "High" and failed >= 8) else "Verify User"

    return {
        "user_id": u["user_id"],
        "asset_id": asset["asset_id"],
        "event_type": ev_type,
        "event_time": when.strftime("%Y-%m-%d %H:%M:%S"),
        "device_category": device,
        "is_new_device": "Yes" if new_dev else "No",
        "location_region": f"{region[0]}, {region[1]}",
        "failed_attempt_count": failed,
        "is_suspicious": suspicious,
        "risk_level": risk,
        "recommended_action": action,
        "related_request_id": related_request["request_id"] if related_request else "",
        "data_origin": "SIMULATED",
        "_when": when,
    }


raw_events = []
# (a) Every unregistered-requester request and some contact requests generate an event
for r in requests:
    if r["_external"] or (r["verification_status"] != "Verified" and rng.random() < 0.5):
        u = user_by_id[r["user_id"]]
        raw_events.append(build_event(u, asset_by_id[r["asset_id"]], "Unusual Access Request",
                                      when=r["_date"] + timedelta(minutes=rng.randint(1, 180)), related_request=r))

# (b) Background events until we reach ~420
EV_TYPE_W = [("Normal Activity", 48), ("Unusual Login", 13), ("Repeated Failed Login", 13),
             ("Unknown Device", 14), ("Inactive Account Review", 12)]
while len(raw_events) < 420:
    u = rng.choice(users)
    ev_type = wchoice(EV_TYPE_W)
    pool = assets_by_user[u["user_id"]]
    if ev_type == "Inactive Account Review":
        pool = [a for a in pool if a["management_status"] in ("Inactive", "Unmanaged")]
        if not pool:
            continue
    else:
        # login-type events happen on accounts in use; skip unmanaged ones most of the time
        active_pool = [a for a in pool if a["management_status"] != "Unmanaged"]
        if active_pool and rng.random() < 0.85:
            pool = active_pool
    raw_events.append(build_event(u, rng.choice(pool), ev_type))

raw_events.sort(key=lambda e: e["_when"])
for i, e in enumerate(raw_events, 1):
    e["event_id"] = f"E{i:04d}"

# ----------------------------------------------------------------------------
# 9. ML-READY TABLE (one row per event, features + labels; no IDs as features)
# ----------------------------------------------------------------------------
ml_rows = []
for e in raw_events:
    u, a = user_by_id[e["user_id"]], asset_by_id[e["asset_id"]]
    home = f"{u['city']}, {u['state']}"
    ml_rows.append({
        "event_id": e["event_id"],  # reference only - drop before training
        "event_type": e["event_type"],
        "hour_of_day": e["_when"].hour,
        "is_night_time": "Yes" if e["_when"].hour < 5 else "No",
        "day_of_week": e["_when"].strftime("%A"),
        "device_category": e["device_category"],
        "is_new_device": e["is_new_device"],
        "location_matches_home": "Yes" if e["location_region"] == home else "No",
        "failed_attempt_count": e["failed_attempt_count"],
        "asset_category": a["asset_category"],
        "asset_importance": a["importance_level"],
        "asset_management_status": a["management_status"],
        "asset_mfa_enabled": a["mfa_enabled"],
        "asset_last_reviewed_days_ago": a["last_reviewed_days_ago"],
        "user_age": u["age"],
        "user_digital_literacy": u["digital_literacy_level"],
        "user_security_awareness": u["account_security_awareness"],
        "from_unregistered_requester": "Yes" if (e["related_request_id"] and
                                                 next(r for r in requests if r["request_id"] == e["related_request_id"])["_external"]) else "No",
        # ---- TARGETS (never use one target as a feature for another) ----
        "target_is_suspicious": e["is_suspicious"],
        "target_risk_level": e["risk_level"],
    })


# ----------------------------------------------------------------------------
# 10. WRITE CSVs
# ----------------------------------------------------------------------------
def write_csv(name, rows, cols):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  {name:<28} {len(rows):>4} rows")


print(f"Generating synthetic dataset (seed={SEED}) ...")
write_csv("users.csv", users, ["user_id", "full_name", "age", "city", "state", "preferred_language",
                               "occupation_category", "digital_literacy_level", "account_security_awareness", "created_at"])
write_csv("digital_assets.csv", assets, ["asset_id", "user_id", "asset_category", "platform_name", "asset_label",
                                         "importance_level", "management_status", "mfa_enabled",
                                         "last_reviewed_days_ago", "contains_sensitive_data"])
write_csv("trusted_contacts.csv", contacts, ["contact_id", "user_id", "contact_name", "relationship_category",
                                             "verification_status", "authorization_level", "contact_email", "added_on"])
write_csv("access_requests.csv", requests, ["request_id", "user_id", "asset_id", "contact_id", "requester_type",
                                            "request_type", "request_reason", "request_date", "verification_status",
                                            "authorization_status", "request_status"])
write_csv("security_events.csv", raw_events, ["event_id", "user_id", "asset_id", "event_type", "event_time",
                                              "device_category", "is_new_device", "location_region",
                                              "failed_attempt_count", "is_suspicious", "risk_level",
                                              "recommended_action", "related_request_id", "data_origin"])
write_csv("ml_security_events.csv", ml_rows, list(ml_rows[0].keys()))
print("Done. All records are fictional and simulated.")
