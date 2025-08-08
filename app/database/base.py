from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func
import uuid


Base = declarative_base()


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UUIDMixin:
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)


class TenantMixin:
    tenant_id = Column(String, nullable=False, index=True) 