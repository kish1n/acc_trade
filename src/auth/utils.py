from enum import Enum

from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.database import get_async_session

async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)

class CarType(Enum):
    SEDAN = "Sedan"
    SUV = "SUV"
    VAN = "Van"
    TRUCK = "Truck"

class Car:
    def __init__(self, car_brand: str, car_model: str, car_color: str,
                 car_plate: str, car_type: CarType, num_seats: int):
        self.car_brand = car_brand
        self.car_model = car_model
        self.car_color = car_color
        self.car_plate = car_plate
        self.car_type = car_type
        self.num_seats = num_seats

class Driver:
    def __init__(self, license_num: int, car: Car, car_owner: str, car_owner_contact: str,
                 trips: int = 0, rating: float = 0.0):
        self.license = license_num
        self.car = car
        self.car_owner = car_owner
        self.car_owner_contact = car_owner_contact
        self.num_of_trips = trips
        self.rating = 0.0

class Passenger:
    def __init__(self, trips: int = 0, rating: float = 0.0):
        self.num_of_trips = trips
        self.rating = 0.0

class UserInfo:
    def __init__(self, role: bool, driver: Driver, passenger: Passenger):
        self.is_driver = role
        self.driver = driver
        self.passenger = passenger
