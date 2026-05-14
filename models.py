from sqlalchemy import Column, Integer, String, Text, SmallInteger, ForeignKey, Float, UniqueConstraint, Boolean
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
    views = Column(Integer, default=0)

    ratings = relationship("Rating", back_populates="recipe", cascade="all, delete-orphan")
    steps = relationship("RecipeStep", back_populates="recipe", cascade="all, delete-orphan")

    @property
    def likes_count(self):
        return sum(1 for r in self.ratings if r.is_positive)

    @property
    def dislikes_count(self):
        return sum(1 for r in self.ratings if not r.is_positive)

class Rating(Base):
    __tablename__ = 'ratings'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recipe_id = Column(Integer, ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)
    is_positive = Column(Boolean, nullable=False)

    recipe = relationship("Recipe", back_populates="ratings")

    __table_args__ = (UniqueConstraint('user_id', 'recipe_id', name='rating_rating_uc'),)

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

class Favorite(Base):
    __tablename__ = 'favorites'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recipe_id = Column(Integer, ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (UniqueConstraint('user_id', 'recipe_id', name='user_recipe_uc'),)

class RecipeStep(Base):
    __tablename__ = 'recipe_steps'

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"))
    step_number = Column(Integer)
    instruction = Column(String)
    image_url = Column(String, nullable=True)

    recipe = relationship('Recipe', back_populates='steps')