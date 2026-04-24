from sqlalchemy import Column, Integer, String, Text, SmallInteger, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(40), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    name = Column(Text)
    surname = Column(Text)
    hashed_password = Column(String(255), nullable=False)
    recipes = relationship('Recipe', back_populates='author')

class Recipe(Base):
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(70), nullable=False, unique=True, index=True)
    description = Column(Text)
    servings = Column(SmallInteger, nullable=False, default=4)
    category = Column(String(30), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey('users.id', ondelete='NO ACTION'), nullable=False)
    author = relationship("User", back_populates="recipes")