from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), unique=True, nullable=False, index=True)

    variants = relationship("Variant", back_populates="category", cascade="all, delete-orphan")

class Variant(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    booked_by = Column(String(255), nullable=True)

    category = relationship("Category", back_populates="variants")
    
    __table_args__ = (
        UniqueConstraint('category_id', 'name', name='uq_variants_name'),
        Index('idx_variants_category_availability', 'category_id', 'is_available'),
    )

class BeverageBooking(Base):
    __tablename__ = "beverage_bookings"

    id = Column(Integer, primary_key=True, index=True)
    booked_by = Column(String(255), nullable=False)
    beverage_name = Column(String(255), nullable=False)
