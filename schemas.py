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

# 1. Definisci prima la classe di creazione (quella base)
class BeverageBookingCreate(BaseModel):
    booked_by: str
    beverage_name: str
    photo_url: str | None = None

# 2. Poi definisci la classe che la estende (quella di risposta)
class BeverageBooking(BeverageBookingCreate):
    id: int

    class Config:
        from_attributes = True
