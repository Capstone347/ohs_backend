from sqlalchemy import Column, Date, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class LegalAcknowledgement(Base):
    __tablename__ = "legal_acknowledgments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=False, index=True)
    jurisdiction = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    effective_date = Column(Date, nullable=False)

    order = relationship("Order", back_populates="legal_acknowledgments")