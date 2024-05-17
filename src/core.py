from fastapi import HTTPException, Depends
from sqlalchemy import and_, asc, desc, func, Integer, cast, update
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert


from src.database import async_session_factory, async_engine, Base
from src.products.database import Product, Image
from src.auth.models import User
from src.auth.base_config import current_user
from src.products.utils import ImageCreate

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
                # Создаем новый продукт
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
                    id_user=self['id_user'],
                    output_data={
                        "username": self['username'],
                        "email": self['email'],
                        "password": self['password']
                    }
                )
                session.add(product)
                await session.flush()

                # Получаем ID нового продукта
                new_product_id = product.id

                # Обновляем колонку user_products у пользователя
                user_stmt = select(User).where(User.id == self['id_user'])
                user_result = await session.execute(user_stmt)
                user = user_result.scalars().one_or_none()

                if user:
                    if user.user_products is None:
                        user.user_products = []
                    user.user_products.append(new_product_id)

                    # Обновляем пользователя в базе данных
                    user_update_stmt = update(User).where(User.id == user.id).values(
                        user_products=user.user_products)
                    await session.execute(user_update_stmt)

            await session.commit()

            # Явно загружаем связанные данные, такие как images
            product_stmt = select(Product).options(joinedload(Product.images)).where(
                Product.id == new_product_id)
            product_result = await session.execute(product_stmt)
            product = product_result.unique().scalars().one_or_none()

            return product

    @staticmethod
    async def add_image(image_data: ImageCreate):
        async with async_session_factory() as session:
            async with session.begin():
                try:
                    # Создаем новый объект Image
                    new_image = Image(
                        path=image_data.path,
                        description=image_data.description,
                        product_id=image_data.product_id
                    )
                    session.add(new_image)
                    await session.flush()

                    await session.commit()


                    return new_image

                except Exception as e:
                    print(f"Error adding image: {str(e)}")
                    await session.rollback()
                    raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_product(p_id: int):
        async with async_session_factory() as session:
            async with session.begin():
                try:
                    stmt = select(Product).where(Product.id == p_id).options(joinedload(Product.id_user))
                    result = await session.execute(stmt)
                    product = result.scalars().one_or_none()

                    if product is None:
                        print(f"Product with ID {p_id} not found.")
                        return {"message": "Product not found", "id": p_id}

                    user_stmt = select(User).where(User.id == product.id_user)
                    user_result = await session.execute(user_stmt)
                    user = user_result.scalars().one_or_none()

                    if user is None:
                        print(f"User with ID {product.id_user} not found.")
                        return {"message": "User not found", "id_user": product.id_user}

                    if user.output_data:
                        output_data = user.output_data
                        updated_output_data = [item for item in output_data if item.get("id") != p_id]

                        # Обновить пользователя в базе данных
                        user_update_stmt = update(User).where(User.id == user.id).values(
                            output_data=updated_output_data)
                        await session.execute(user_update_stmt)

                    await session.delete(product)
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
                    stmt = select(Product).where(Product.id == p_id).options(joinedload(Product.images))
                    result = await session.execute(stmt)
                    item = result.unique().scalars().one_or_none()  # Используем unique() для исключения дублирующих результатов
                    if item is None:
                        print(f"Product with ID {p_id} not found.")
                        return {"message": "Product not found", "id": p_id}
                    if item.id_user != cur_user:
                        raise HTTPException(status_code=400, detail=f"Вы не владелец этого продукта {cur_user}")

                    # Обновление полей продукта
                    for key, value in kwargs.items():
                        setattr(item, key, value)

                    # Обновление output_data в продукте
                    item.output_data = {
                        "username": kwargs.get("username", item.output_data.get("username")),
                        "email": kwargs.get("email", item.output_data.get("email")),
                        "password": kwargs.get("password", item.output_data.get("password"))
                    }

                    await session.commit()
#                    await session.refresh(item)  # Обновляем продукт после коммита

                    return item

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