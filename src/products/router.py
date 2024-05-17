from typing import List, Optional, Dict
from functools import partial
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.database import get_async_session

from src.core import Core
from src.products.database import Product, Image
from src.auth.base_config import current_user
from src.products.utils import ImageCreate

router = APIRouter(
    tags=["products"],
    prefix="/products"
)


def product_to_dict(product):
    if isinstance(product, Product):
        return {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "description": product.description,
            "tags": product.tags,
            "main_img": product.main_img,
            "game_rating": {
                "rating": product.game_rating.get("rating", 0),
                "description": product.game_rating.get("description", "")
            } if product.game_rating else {},
            "images": [img.path for img in product.images],
            "id_user": product.id_user,
            "output_data": product.output_data  # Добавим поле output_data
        }
    return {}


@router.get("/")
async def get_prd(fst_id: int, lst_id: int, session: AsyncSession = Depends(get_async_session)) -> List[dict]:
    stmt = select(Product).where(Product.id.between(fst_id, lst_id)).options(selectinload(Product.images))
    result = await session.execute(stmt)
    items = result.scalars().all()
    return [product_to_dict(item) for item in items]

@router.get("/item/{id}")
async def get_products_by_tags_and_id(id: int) -> List[dict]:
    items = await Core.get_products_by_id(id)
    if not items:
        raise HTTPException(status_code=404, detail="Product not found with the given id")

    return [product_to_dict(item) for item in items]

@router.get("/{tags}/sorted/{method}")
async def get_products_by_tags(tags: str, offset: int = 0, limit: int = 30, method: str = "default") -> List[dict]:

    try:
        items = await Core.sorted_products(method, tags, offset, limit)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return [product_to_dict(item) for item in items]

@router.post("/add/item")
async def add_product(name: str, price: int, description: str, tags: str, main_img: str, rating_elo: int,
                      rating_name: str, username: str, email: str, password: str, user: User = Depends(current_user)) -> dict:
    try:
        item = await Core.add_product({
            "name": name,
            "price": price,
            "description": description,
            "tags": tags,
            "main_img": main_img,
            "rating_elo": rating_elo,
            "rating_name": rating_name,
            "id_user": user.id,
            "username": username,
            "email": email,
            "password": password
        })

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return product_to_dict(item)

@router.post("/add/images/")
async def create_image(image: ImageCreate, cur_user: User = Depends(current_user)):
    try:
        item = await Core.add_image(image)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "Image added", "image": item}

@router.post("/delete/item")
async def delete_product(id: int) -> dict:
    try:
        item = await Core.delete_product(id)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return product_to_dict(item)

@router.put("/rework/item/{id_product}", response_model=dict)
async def rework_product(
    id_product: int,
    name: str,
    price: int,
    description: str,
    tags: str,
    main_img: str,
    rating_elo: int,
    rating_name: str,
    username: str,
    email: str,
    password: str,
    cur_user: User = Depends(current_user),
):
    try:
        item = await Core.rework_product(id_product, {
            "name": name,
            "price": price,
            "description": description,
            "tags": tags,
            "main_img": main_img,
            "game_rating": {"rating": rating_elo, "description": rating_name},
            "username": username,
            "email": email,
            "password": password
        }, cur_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return product_to_dict(item)

@router.get("/buy/item/{id}")
async def buy_product(id: int, user: User = Depends(current_user)) -> dict:
    try:
        item = await Core.buy_product(id, user.id)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return product_to_dict(item)
