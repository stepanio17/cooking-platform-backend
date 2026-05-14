from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from auth import verify_password, create_access_token, SECRET_KEY, ALGORITHM, get_password_hash
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import List
from jose import jwt, JWTError
import os
import shutil
import models
import schemas
import uuid
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

@app.post("/recipes/{recipe_id}/favorite")
def toggle_favorite(recipe_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Рецепт не найден")

    favorite = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user_id,
        models.Favorite.recipe_id == recipe_id).first()

    if favorite:
        db.delete(favorite)
        db.commit()
        return {"message": "Удалено из избранного", "status": "removed"}
    else:
        new_favorite = models.Favorite(user_id=current_user_id, recipe_id=recipe_id)
        db.add(new_favorite)
        db.commit()
        return {"message": "Добавлено в избранное", "status": "added"}

@app.get("/favorites", response_model=List[schemas.RecipeOut])
def get_favorites(db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    favorites = db.query(models.Favorite).filter(models.Favorite.user_id == current_user_id).all()
    recipes_ids = [fav.recipe_id for fav in favorites]
    recipes = db.query(models.Recipe).filter(models.Recipe.id.in_(recipes_ids)).all()
    return recipes

@app.get("/recipes", response_model=List[schemas.RecipeOut])
def get_recipes(search: str = None, category: str = None, sort_by: str = "newest", ingredient_search: str = None, exclude_ingredient: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Recipe).options(joinedload(models.Recipe.steps))

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(func.lower(models.Recipe.title).like(search_lower))

    if category and category != "Все":
        query = query.filter(models.Recipe.category == category)

    if ingredient_search:
        ing_search_lower = f"%{ingredient_search.lower()}%"
        query = query.join(models.Recipe.ingredients).join(models.RecipeIngredient.ingredient).filter(
            func.lower(models.Ingredient.name).like(ing_search_lower)
        ).distinct()

    if exclude_ingredient:
        exclude_lower = f"%{exclude_ingredient.lower()}%"

        forbidden_recipes_ids = db.query(models.RecipeIngredient.recipe_id).join(
            models.Ingredient).filter(func.lower(models.Ingredient.name).like(exclude_lower))
        query = query.filter(models.Recipe.id.notin_(forbidden_recipes_ids))

    if sort_by == "newest":
        query = query.order_by(desc(models.Recipe.id))

    return query.all()

@app.post("/upload-image")
def upload_image(file: UploadFile = File(...)):
    file_extension = file.filename.rsplit(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = f"static/images/{unique_filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"image_url": f"http://127.0.0.1:8000/static/images/{unique_filename}"}

@app.post("/recipes", response_model=schemas.RecipeOut)
def create_recipe(recipe: schemas.RecipeCreate, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    db_recipe = models.Recipe(**recipe.model_dump(exclude={"ingredients", "steps"}), author_id=current_user_id)
    try:
        db.add(db_recipe)
        db.flush()
        for ing_data in recipe.ingredients:
            db_ingredient = db.query(models.Ingredient).filter(
                models.Ingredient.name == ing_data.name.lower().strip()
            ).first()

            if not db_ingredient:
                db_ingredient = models.Ingredient(name=ing_data.name.lower().strip())
                db.add(db_ingredient)
                db.flush()

            recipe_ing = models.RecipeIngredient(
                recipe_id=db_recipe.id,
                ingredient_id=db_ingredient.id,
                amount=ing_data.amount,
                unit=ing_data.unit
            )
            db.add(recipe_ing)

        for step_data in recipe.steps:
            new_step = models.RecipeStep(
                recipe_id=db_recipe.id,
                step_number=step_data.step_number,
                instruction=step_data.instruction,
                image_url=step_data.image_url
            )
            db.add(new_step)

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
def update_recipe(recipe_id: int, updated_recipe: schemas.RecipeCreate, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    db_recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()

    if not db_recipe or db_recipe.author_id != current_user_id:
        raise HTTPException(status_code = 403, detail="У вас нет прав для изменения этого рецепта")

    update_data = updated_recipe.model_dump(exclude={"ingredients", "steps"})
    for key, value in update_data.items():
        setattr(db_recipe, key, value)

    try:
        db.query(models.RecipeIngredient).filter(models.RecipeIngredient.recipe_id == recipe_id).delete()

        for img_data in updated_recipe.ingredients:
            db_ingredient = db.query(models.Ingredient).filter(
                models.Ingredient.name == img_data.name.lower().strip()
            ).first()

            if not db_ingredient:
                db_ingredient = models.Ingredient(name=img_data.name.lower().strip())
                db.add(db_ingredient)
                db.flush()

            new_recipe_ing = models.RecipeIngredient(
                recipe_id=db_recipe.id,
                ingredient_id=db_ingredient.id,
                amount=img_data.amount,
                unit=img_data.unit
            )
            db.add(new_recipe_ing)

        db.query(models.RecipeStep).filter(models.RecipeStep.recipe_id == recipe_id).delete()
        for step_data in updated_recipe.steps:
            new_step = models.RecipeStep(
                recipe_id=db_recipe.id,
                step_number=step_data.step_number,
                instruction=step_data.instruction,
                image_url=step_data.image_url
            )
            db.add(new_step)

        db.commit()
        db.refresh(db_recipe)
        return db_recipe

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка, название уже занято или данные некорректны")

@app.post("/recipes/{recipe_id}/view")
def increment_view(recipe_id: int, db: Session = Depends(get_db)):
    db_recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not db_recipe:
        raise HTTPException(status_code=404, detail="Рецепт не найден")
    db_recipe.views += 1
    db.commit()
    return {"views": db_recipe.views}

@app.post("/recipes/{recipe_id}/rate")
def rate_recipe(recipe_id: int, is_positive: bool, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    existing_rating = db.query(models.Rating).filter(
        models.Rating.user_id == current_user_id,
        models.Rating.recipe_id == recipe_id
    ).first()

    if existing_rating:
        if existing_rating.is_positive == is_positive:
            db.delete(existing_rating)
        else:
            existing_rating.is_positive = is_positive
    else:
        new_rating = models.Rating(user_id=current_user_id, recipe_id=recipe_id, is_positive=is_positive)
        db.add(new_rating)

    db.commit()
    return {"success": True}

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

app.mount("/static", StaticFiles(directory="static"), name="static")