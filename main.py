from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, select, desc, asc
from pydantic import BaseModel
from typing import List

DATABASE_URL = "sqlite+aiosqlite:///./recipes.db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

app = FastAPI(
    title="Recipe Book API", description="API for a recipe book app", version="1.0.0"
)


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0)
    cook_time: Mapped[int] = mapped_column(Integer, nullable=False)
    ingredients: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class RecipeCreate(BaseModel):
    title: str
    cook_time: int
    ingredients: str
    description: str


class RecipeOut(BaseModel):
    id: int
    title: str
    views: int
    cook_time: int

    class Config:
        orm_mode = True


class RecipeDetailOut(RecipeOut):
    ingredients: str
    description: str


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


@app.get("/recipes", response_model=List[RecipeOut])
async def get_recipes(session: AsyncSession = Depends(get_session)):
    stmt = select(Recipe).order_by(desc(Recipe.views), asc(Recipe.cook_time))
    result = await session.execute(stmt)
    return result.scalars().all()


@app.get("/recipes/{recipe_id}", response_model=RecipeDetailOut)
async def get_recipe(recipe_id: int, session: AsyncSession = Depends(get_session)):
    recipe = await session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    recipe.views += 1
    await session.commit()
    return recipe


@app.post("/recipes", response_model=RecipeDetailOut, status_code=201)
async def create_recipe(
    recipe: RecipeCreate, session: AsyncSession = Depends(get_session)
):
    db_recipe = Recipe(**recipe.dict())
    session.add(db_recipe)
    await session.commit()
    await session.refresh(db_recipe)
    return db_recipe


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)