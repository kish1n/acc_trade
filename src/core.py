from fastapi import HTTPException, Depends
from sqlalchemy import and_, asc, desc, func, Integer, cast
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert


from src.database import async_session_factory, async_engine, Base
from src.products.database import Product
from src.auth.models import User
from src.auth.base_config import current_user

class Core:
    @staticmethod
    async def create_tables():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            await conn.commit()

    @staticmethod
    async def get_num_elem(fst_num: int, lst_num: int):
        async with async_session_factory() as session:
            async with session.begin() as s:
                stmt = select(Product).where(Product.id.between(fst_num, lst_num))
                result = await session.execute(stmt)
                items = result.scalars().all()
                return items

    @staticmethod
    async def get_products_by_id(p_id: int) -> list:
        async with async_session_factory() as session:
            stmt = select(Product).where(Product.id == p_id).options(selectinload(Product.images))
            result = await session.execute(stmt)
            item = result.scalars().all()
            return item

    @staticmethod
    async def get_products_by_tags(tags: str, offset: int = 0, limit: int = 30):
        tags_list = tags.split('&')
        conditions = [Product.tags.op("~")(f"\\y{tag}\\y") for tag in tags_list]
        async with async_session_factory() as session:
            stmt = select(Product).where(and_(*conditions)).offset(offset).limit(limit).options(selectinload(Product.images))
            result = await session.execute(stmt)
            items = result.scalars().all()
            return items

    @staticmethod
    async def sorted_products(method: str, tags: str, offset: int = 0, limit: int = 30):
        async with async_session_factory() as session:
            tags_list = tags.split('&')
            conditions = [Product.tags.op("~")(f"\\y{tag}\\y") for tag in tags_list]

            method_functions = {
                "default": None,
                "rating_up": asc(cast(Product.game_rating['rating'], Integer)),
                "rating_down": desc(cast(Product.game_rating['rating'], Integer)),
                "price_up": asc(Product.price),
                "price_down": desc(Product.price),
            }

            order_clause = method_functions[method]

            stmt = (
                select(Product)
                .where(and_(*conditions))  # Применяем все условия фильтрации
                .order_by(order_clause)  # Устанавливаем порядок сортировки
                .offset(offset)  # Смещение для пагинации
                .limit(limit)  # Ограничение на количество элементов
                .options(selectinload(Product.images))  # Предзагрузка связанных изображений
            )
            result = await session.execute(stmt)
            items = result.scalars().all()
            return items

    @staticmethod
    async def add_product(self: dict):
        async with async_session_factory() as session:
            async with session.begin():
                product = Product(
                    name=self['name'],
                    price=int(self['price']),
                    description=self['description'],
                    tags=self['tags'],
                    main_img=self['main_img'],
                    game_rating={
                        "rating": int(self['rating_elo']),
                        "description": self['rating_name']
                    },
                    id_user=self['id_user']
                )
                session.add(product)
                await session.flush()

            await session.commit()
            session.expunge_all()

            product = await session.execute(
                select(Product).options(selectinload(Product.images)).where(Product.id == product.id)
            )
            product = product.scalars().one()
            return product

    @staticmethod
    async def delete_product(p_id: int):
        async with async_session_factory() as session:
            async with session.begin():
                try:
                    stmt = select(Product).where(Product.id == p_id)
                    result = await session.execute(stmt)
                    item = result.scalars().one_or_none()
                    if item is None:
                        print(f"Product with ID {p_id} not found.")
                        return {"message": "Product not found", "id": p_id}

                    await session.delete(item)
                    print(f"Product with ID {p_id} scheduled for deletion.")
                    await session.commit()
                    return {"message": "Product deleted", "id": p_id}

                except Exception as e:
                    print(f"Error during deletion: {str(e)}")
                    await session.rollback()
                    raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def rework_product(p_id: int, kwargs: dict, cur_user: int):
        async with async_session_factory() as session:
            async with session.begin():
                try:
                    stmt = select(Product).where(Product.id == p_id)
                    result = await session.execute(stmt)
                    item = result.scalars().one_or_none()
                    if item is None:
                        print(f"Product with ID {p_id} not found.")
                        return {"message": "Product not found", "id": p_id}
                    if item.id_user != cur_user:
                        raise HTTPException(status_code=400, detail=f"Вы не владелец этого продукта {current_user}")

                    for key, value in kwargs.items():
                        setattr(item, key, value)

                    await session.commit()
                    return {"message": "Product reworked", "id": p_id}

                except Exception as e:
                    print(f"Error during rework: {str(e)}")
                    await session.rollback()
                    raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def buy_item(p_id: int, cur_user: int):
        async with async_session_factory() as session:
            async with session.begin():
                try:
                    stmt = select(Product).where(Product.id == p_id)
                    result = await session.execute(stmt)
                    item = result.scalars().one_or_none()
                    if item is None:
                        print(f"Product with ID {p_id} not found.")
                        return {"message": "Product not found", "id": p_id}
                    if item.id_user == cur_user:
                        raise HTTPException(status_code=400, detail=f"Вы не можете купить свой продукт {current_user}")
                    await Core.delete_product(p_id)
                    await session.commit()
                    return {"message": "Product bought", "id": p_id}

                except Exception as e:
                    print(f"Error during buying: {str(e)}")
                    await session.rollback()
                    raise HTTPException(status_code=500, detail=str(e))