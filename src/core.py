from sqlalchemy import and_, asc, desc, func, Integer, cast
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert


from src.database import async_session_factory, async_engine, Base
from src.products.database import Product
from src.auth.models import User

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
    async def sorted_products_by_price(tags: str = "default", offset: int = 0, limit: int = 30, up: bool = False):
        tags_list = tags.split('&')
        conditions = [Product.tags.op("~")(f"\\y{tag}\\y") for tag in tags_list]
        order_clause = None
        if up:
            order_clause = asc(Product.price)
        else:
            order_clause = desc(Product.price)
        async with async_session_factory() as session:
            stmt = (
                select(Product)
                .where(and_(*conditions))  # Применяем все условия фильтрации
                .order_by(order_clause)  # Добавляем сортировку по полю price
                .offset(offset)  # Устанавливаем смещение для пагинации
                .limit(limit)  # Устанавливаем лимит на количество возвращаемых элементов
                .options(selectinload(Product.images))  # Предварительная загрузка связанных изображений
            )
            result = await session.execute(stmt)
            items = result.scalars().all()
            return items

    @staticmethod
    async def sorted_products_by_rating(tags: str = "default", offset: int = 0, limit: int = 30, up: bool = False):
        async with async_session_factory() as session:
            tags_list = tags.split('&')
            conditions = [Product.tags.op("~")(f"\\y{tag}\\y") for tag in tags_list]
            order_clause = None
            if up:
                order_clause = asc(cast(Product.game_rating['rating'], Integer))
            else:
                order_clause = desc(cast(Product.game_rating['rating'], Integer))

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