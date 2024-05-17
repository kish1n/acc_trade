from pydantic import BaseModel
class ImageCreate(BaseModel):
    path: str
    description: str
    product_id: int

