from sqlalchemy import Column, Integer, String, Text, SmallInteger, ForeignKey, Float
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
    image_url = Column(String, nullable=True)
    author_id = Column(Integer, ForeignKey('users.id', ondelete='NO ACTION'), nullable=False)
    author = relationship("User", back_populates="recipes")
    ingredients = relationship('RecipeIngredient', back_populates='recipe', cascade="all, delete-orphan")

class Ingredient(Base):
    __tablename__ = 'ingredients'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    recipe_links = relationship('RecipeIngredient', back_populates='ingredient')

class RecipeIngredient(Base):
    __tablename__ = 'recipe_ingredients'

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    ingredient_id = Column(Integer, ForeignKey('ingredients.id', ondelete='CASCADE'), nullable=False)
    amount = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    recipe = relationship('Recipe', back_populates='ingredients')
    ingredient = relationship('Ingredient', back_populates='recipe_links')

    @property
    def name(self):
        return self.ingredient.name