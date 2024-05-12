from fastapi import FastAPI
from fastapi_users import FastAPIUsers

from src.auth.manager import get_user_manager
from src.auth.schemas import UserRead, UserCreate
from src.auth.base_config import auth_backend
from src.auth.models import User

from src.core import Core
from src.products.router import router as products_router

app = FastAPI(
    title="Account shop",
)

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(products_router)

@app.get("/")
async def startup_event():
    #await Core.create_tables()
    return {"message": "Hello World"}
