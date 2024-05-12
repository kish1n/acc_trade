from typing import Dict

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from src.database import Base


class Image(Base):
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True)
    path = Column(String, nullable=False)
    description = Column(String, nullable=True)
    product_id = Column(Integer, ForeignKey('product.id'))

    product = relationship('Product', back_populates='images')

class Product(Base):
    __tablename__ = 'product'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Integer)
    description = Column(String)
    tags = Column(String)
    main_img = Column(String)
    game_rating = Column(JSONB)  # JSON тип для хранения сложных структур данных

    images = relationship("Image", back_populates="product")
