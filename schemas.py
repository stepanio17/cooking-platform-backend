from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    name: Optional[str] = None
    surname: Optional[str] = None

class UserOut(UserCreate):
    id: int
    class Config:
        from_attributes = True

class RecipeCreate(BaseModel):
    title: str
    description: Optional[str] = None
    servings: int = 4
    author_id: int

class RecipeOut(RecipeCreate):
    id: int
    class Config:
        from_attributes = True


