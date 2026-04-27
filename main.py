from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from auth import verify_password, create_access_token, SECRET_KEY, ALGORITHM, get_password_hash
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List
from jose import jwt, JWTError
import os
import shutil
import models
import schemas
from database import engine, get_db

os.makedirs("static/images", exist_ok=True)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Невалидный токен")
        return int(user_id)
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Ошибка авторизации")

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users", response_model=List[schemas.UserOut])
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

@app.post("/users", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    hashed_pwd = get_password_hash(user.password)
    new_user = models.User(username=user.username, email=user.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.get("/recipes", response_model=List[schemas.RecipeOut])
def get_recipes(search: str = None, category: str = None, sort_by: str = "newest", db: Session = Depends(get_db)):
    query = db.query(models.Recipe)

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(func.lower(models.Recipe.title).like(search_lower))

    if category and category != "Все":
        query = query.filter(models.Recipe.category == category)

    if sort_by == "newest":
        query = query.order_by(desc(models.Recipe.id))

    return query.all()

@app.post("/recipes", response_model=schemas.RecipeOut)
def create_recipe(recipe: schemas.RecipeCreate, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    db_recipe = models.Recipe(**recipe.model_dump(), author_id=current_user_id)
    try:
        db.add(db_recipe)
        db.commit()
        db.refresh(db_recipe)
        return db_recipe
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Рецепт с таким названием уже существует")

@app.delete("/recipes/{recipe_id}")
def delete_recipe(recipe_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    db_recipe = db.query(models.Recipe).get(recipe_id)
    if not db_recipe:
        raise HTTPException(status_code=404, detail="Рецепт не найден")
    if db_recipe.author_id != current_user_id:
        raise HTTPException(status_code=403, detail="Не твой рецепт")
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

@app.post("/recipes/{recipe_id}/image")
def upload_recipe_image(
        recipe_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user_id: int = Depends(get_current_user),
):
    db_recipe = db.query(models.Recipe).get(recipe_id)

    if not db_recipe or db_recipe.author_id != current_user_id:
        raise HTTPException(status_code=403, detail="Нельзя изменить этот рецепт")

    file_location = f"static/images/{recipe_id}_{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    db_recipe.image_url = f"http://127.0.0.1:8000/{file_location}"
    db.commit()

    return {"info": "Файл сохранён", "url": db_recipe.image_url}