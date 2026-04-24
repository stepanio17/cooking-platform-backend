from pydantic import BaseModel, Field
from typing import Optional

class RecipeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=70, description="Название не может быть пустым")
    description: str = Field(..., min_length=10)
    servings: int = Field(..., gt=0, description="Количество порций должно быть больше нуля")

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

class RecipeCreate(RecipeBase):
    pass

class RecipeOut(RecipeCreate):
    id: int
    class Config:
        from_attributes = True


