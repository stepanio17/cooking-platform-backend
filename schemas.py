from pydantic import BaseModel, Field
from typing import Optional, List

from models import Ingredient


class RecipeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=70, description="Название не может быть пустым")
    description: str = Field(..., min_length=10)
    servings: int = Field(..., gt=0, le=16, description="Количество порций должно быть больше нуля")
    category: Optional[str] = Field(None, max_length=30)
    image_url: Optional[str] = None

class UserBase(BaseModel):
    username: str
    email: str
    name: Optional[str] = None
    surname: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    class Config:
        from_attributes = True

class RecipeIngredientCreate(BaseModel):
    name: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1)


class RecipeIngredientOut(BaseModel):
    id: int
    ingredient_id: int
    name: str
    amount: float
    unit: str

    class Config:
        from_attributes = True

class RecipeCreate(RecipeBase):
    ingredients: List[RecipeIngredientCreate] = []

class RecipeOut(RecipeBase):
    id: int
    author_id: int
    ingredients: List[RecipeIngredientOut] = []
    class Config:
        from_attributes = True