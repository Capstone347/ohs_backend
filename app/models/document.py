from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String, CHAR, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class DocumentFormat(Enum):
    DOCX = "docx"
    PDF = "pdf"


class Document(Base):
    __tablename__ = "documents"

    document_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
    content = Column(JSON, nullable=True)
    access_token = Column(CHAR(64), nullable=False, unique=True)
    token_expires_at = Column(DateTime, nullable=False)
    generated_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    downloaded_count = Column(Integer, nullable=False, default=0)
    last_downloaded_at = Column(DateTime, nullable=True)
    file_path = Column(String(500), nullable=True)
    file_format = Column(String(10), nullable=True, default="docx")

    order = relationship("Order", back_populates="documents")