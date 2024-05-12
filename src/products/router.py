from typing import List, Optional, Dict
from functools import partial
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_async_session

from src.core import Core
from src.products.database import Product

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
            },
            "images": [img.path for img in product.images]
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
                      rating_name) -> dict:
    try:
        item = await Core.add_product({
            "name": name,
            "price": price,
            "description": description,
            "tags": tags,
            "main_img": main_img,
            "rating_elo": rating_elo,
            "rating_name": rating_name
        })

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return product_to_dict(item)

@router.post("/delete/item")
async def delete_product(id: int) -> dict:
    try:
        item = await Core.delete_product(id)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return product_to_dict(item)





