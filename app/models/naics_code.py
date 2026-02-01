from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class NAICSCode(Base):
    __tablename__ = "naics_code"

    code = Column(Integer, primary_key=True)
    industry = Column(String(45), nullable=True)

    user_content = relationship(
        "NAICSUserContent", 
        primaryjoin="foreign(NAICSUserContent.naics_code) == NAICSCode.code", 
        back_populates="naics_code_rel"
    )