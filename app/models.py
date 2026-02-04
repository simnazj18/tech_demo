from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)

    accounts = relationship("AzureAccount", back_populates="owner")

class AzureAccount(Base):
    __tablename__ = "azure_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100)) # Alias, e.g. "Dev Environment"
    client_id = Column(String(100))
    client_secret = Column(String(255)) # Encrypt in prod!
    tenant_id = Column(String(100))
    keyvault_url = Column(String(255))
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="accounts")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    secret_name = Column(String(255))
    action = Column(String(50)) # e.g., "Rotated"
    status = Column(String(50)) # e.g., "Success", "Failed"
    details = Column(String(500), nullable=True)
    
    account_id = Column(Integer, ForeignKey("azure_accounts.id"))
    account = relationship("AzureAccount")
