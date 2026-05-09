from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class Medicine(Base):
    __tablename__ = "medicines"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String, nullable=False, unique=True, index=True)
    manufacturer = Column(String, default="")
    category     = Column(String, default="General")
    unit_price   = Column(Float, nullable=False, default=0.0)
    created_at   = Column(DateTime, default=datetime.utcnow)

    inventory_items = relationship(
        "Inventory",
        back_populates="medicine",
        cascade="all, delete-orphan"
    )
    bill_items      = relationship("BillItem",  back_populates="medicine")
    sales           = relationship("SalesLog",  back_populates="medicine")


class Inventory(Base):
    __tablename__ = "inventory"

    id            = Column(Integer, primary_key=True, index=True)
    medicine_id   = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    quantity      = Column(Integer, nullable=False, default=0)
    expiry_date   = Column(String, nullable=False)
    batch_number  = Column(String, default="")
    reorder_level = Column(Integer, default=10)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    medicine = relationship("Medicine", back_populates="inventory_items")


class Bill(Base):
    __tablename__ = "bills"

    id            = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, default="Walk-in Customer")
    total_amount  = Column(Float, nullable=False, default=0.0)
    notes         = Column(Text, default="")
    created_at    = Column(DateTime, default=datetime.utcnow)

    items = relationship("BillItem", back_populates="bill", cascade="all, delete-orphan")


class BillItem(Base):
    __tablename__ = "bill_items"

    id          = Column(Integer, primary_key=True, index=True)
    bill_id     = Column(Integer, ForeignKey("bills.id"), nullable=False)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    quantity    = Column(Integer, nullable=False)
    unit_price  = Column(Float, nullable=False)

    bill     = relationship("Bill",     back_populates="items")
    medicine = relationship("Medicine", back_populates="bill_items")


class SalesLog(Base):
    __tablename__ = "sales_log"

    id          = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    quantity_sold = Column(Integer, nullable=False)
    sold_at     = Column(DateTime, default=datetime.utcnow)

    medicine = relationship("Medicine", back_populates="sales")
