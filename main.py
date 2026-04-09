from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

import models
import schemas
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/users", response_model=List[schemas.UserOut])
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

@app.post("/users", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/recipes", response_model=List[schemas.RecipeOut])
def get_recipes(search: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Recipe)

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(func.lower(models.Recipe.title).like(search_lower))
    return query.all()

@app.post("/recipes", response_model=schemas.RecipeOut)
def create_recipe(recipe: schemas.RecipeCreate, db: Session = Depends(get_db)):
    db_recipe = models.Recipe(**recipe.model_dump())
    try:
        db.add(db_recipe)
        db.commit()
        db.refresh(db_recipe)
        return db_recipe
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Рецепт с таким названием уже существует")

@app.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    db_recipe = db.query(models.Recipe).get(recipe_id)
    if not db_recipe:
        raise HTTPException(status_code=404, detail="Рецепт не найден")
    db.delete(db_recipe)
    db.commit()
    return {"message": "Рецепт был удалён"}

@app.put("/recipes/{recipe_id}", response_model=schemas.RecipeOut)
def update_recipe(recipe_id: int,  updated_recipe: schemas.RecipeCreate, db: Session = Depends(get_db)):
    try:
        db_recipe = db.query(models.Recipe).get(recipe_id)
        if not db_recipe:
            raise HTTPException(status_code=404, detail="Рецепт не найден")
        updated_data = updated_recipe.model_dump()
        for key, value in updated_data.items():
            setattr(db_recipe, key, value)
        db.commit()
        db.refresh(db_recipe)
        return db_recipe
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Название уже занято, придумай другое")