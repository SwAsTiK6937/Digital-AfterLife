"""
Database tables. They mirror the synthetic CSV files one-to-one, plus:
  - users.email / users.password_hash / users.is_admin  (for login)
  - digital_assets.last_reviewed_on  (a real date instead of a fixed "days ago")
  - security_events.resolution  (what the owner answered on an alert)

No real third-party passwords, ID numbers or bank details are stored anywhere.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)  # argon2 hash of the APP password only
    is_admin = Column(Boolean, default=False)
    age = Column(Integer)
    city = Column(String)
    state = Column(String)
    preferred_language = Column(String)
    occupation_category = Column(String)
    digital_literacy_level = Column(String)
    account_security_awareness = Column(String)
    created_at = Column(Date)

    assets = relationship("DigitalAsset", back_populates="owner")
    contacts = relationship("TrustedContact", back_populates="owner")


class DigitalAsset(Base):
    __tablename__ = "digital_assets"

    asset_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), index=True, nullable=False)
    asset_category = Column(String, nullable=False)
    platform_name = Column(String, nullable=False)
    asset_label = Column(String, nullable=False)
    importance_level = Column(String, nullable=False)
    management_status = Column(String, nullable=False)
    mfa_enabled = Column(String, nullable=False)
    last_reviewed_on = Column(Date, nullable=False)
    contains_sensitive_data = Column(String, nullable=False)

    owner = relationship("User", back_populates="assets")


class TrustedContact(Base):
    __tablename__ = "trusted_contacts"

    contact_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), index=True, nullable=False)
    contact_name = Column(String, nullable=False)
    relationship_category = Column(String, nullable=False)
    verification_status = Column(String, nullable=False)
    authorization_level = Column(String, nullable=False)
    contact_email = Column(String)
    added_on = Column(Date)

    owner = relationship("User", back_populates="contacts")


class AccessRequest(Base):
    __tablename__ = "access_requests"

    request_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), index=True, nullable=False)
    asset_id = Column(String, ForeignKey("digital_assets.asset_id"), nullable=False)
    contact_id = Column(String, ForeignKey("trusted_contacts.contact_id"), nullable=True)
    requester_type = Column(String, nullable=False)
    request_type = Column(String, nullable=False)
    request_reason = Column(String, nullable=False)
    request_date = Column(Date, nullable=False)
    verification_status = Column(String, nullable=False)
    authorization_status = Column(String, nullable=False)
    request_status = Column(String, nullable=False)

    asset = relationship("DigitalAsset")
    contact = relationship("TrustedContact")


class SecurityEvent(Base):
    __tablename__ = "security_events"

    event_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), index=True, nullable=False)
    asset_id = Column(String, ForeignKey("digital_assets.asset_id"), nullable=False)
    event_type = Column(String, nullable=False)
    event_time = Column(DateTime, nullable=False)
    device_category = Column(String)
    is_new_device = Column(String)
    location_region = Column(String)
    failed_attempt_count = Column(Integer, default=0)
    is_suspicious = Column(String)
    risk_level = Column(String)
    recommended_action = Column(String)
    related_request_id = Column(String, nullable=True)
    data_origin = Column(String, default="SIMULATED")
    resolution = Column(String, nullable=True)  # None = still open

    asset = relationship("DigitalAsset")
