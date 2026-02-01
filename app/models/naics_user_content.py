from sqlalchemy import Column, Integer, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class NAICSUserContent(Base):
    __tablename__ = "naics_user_content"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=False, index=True)
    naics_code = Column(Integer, ForeignKey("naics_code.code", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=False, index=True)
    industry_description = Column(Text, nullable=False)
    suggested_sections = Column(JSON, nullable=True)
    procedures = Column(JSON, nullable=True)

    order = relationship("Order", back_populates="naics_user_content")
    naics_code_rel = relationship(
        "NAICSCode", 
        primaryjoin="foreign(NAICSUserContent.naics_code) == NAICSCode.code", 
        back_populates="user_content"
    )