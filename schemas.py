from pydantic import BaseModel

class VariantBase(BaseModel):
    name: str

class Variant(VariantBase):
    id: int
    category_id: int
    is_available: bool

    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str

class Category(CategoryBase):
    id: int
    normalized_name: str

    class Config:
        from_attributes = True

class VariantAdmin(Variant):
    category: Category
    booked_by: str | None

class BookVariantRequest(BaseModel):
    booked_by: str

class BeverageBookingCreate(BaseModel):
    booked_by: str
    beverage_name: str

class BeverageBooking(BeverageBookingCreate):
    id: int

    class Config:
        from_attributes = True
