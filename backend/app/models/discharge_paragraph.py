from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.identifiers import new_id


class DischargeParagraph(Base):
    __tablename__ = "discharge_paragraphs"

    id = Column(String(36), primary_key=True, default=new_id)
    discharge_draft_id = Column(String(36), ForeignKey("discharge_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    source_citation = Column(String(255), nullable=True)
    order_index = Column(Integer, nullable=False, default=0)

    discharge_draft = relationship("DischargeDraft", back_populates="paragraphs")
