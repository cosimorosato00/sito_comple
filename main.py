from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
import secrets
import models, schemas
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema Prenotazione Piatti API")
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "admin123")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Credenziali non valide",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Setup CORS for the frontend testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sanitize_search_query(q: str) -> str:
    if not q:
        return ""
    # Lowers and removes multiple consecutive spaces
    return " ".join(q.strip().lower().split())

@app.get("/api/categories", response_model=list[schemas.Category])
def search_categories(q: str, db: Session = Depends(get_db)):
    if len(q) < 3:
        raise HTTPException(status_code=400, detail="La query deve essere di almeno 3 caratteri")
    
    sanitized_q = sanitize_search_query(q)
    # Using prefix matching with LIKE
    categories = db.query(models.Category)\
                   .filter(models.Category.normalized_name.like(f"{sanitized_q}%"))\
                   .limit(10).all()
    return categories

@app.get("/api/categories/{category_id}/variants", response_model=list[schemas.Variant])
def get_available_variants(category_id: int, db: Session = Depends(get_db)):
    variants = db.query(models.Variant)\
                 .filter(models.Variant.category_id == category_id)\
                 .all()
    return variants

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    food_count = db.query(models.Variant).filter(models.Variant.is_available == False).count()
    drink_count = db.query(models.BeverageBooking).count()
    return {"food": food_count, "drinks": drink_count}

@app.post("/api/variants/{variant_id}/book")
def book_variant(variant_id: int, request: schemas.BookVariantRequest, db: Session = Depends(get_db)):
    try:
        rows_affected = db.query(models.Variant)\
                          .filter(models.Variant.id == variant_id)\
                          .filter(models.Variant.is_available == True)\
                          .update({"is_available": False, "booked_by": request.booked_by}, synchronize_session=False)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database Error interno")

    if rows_affected == 0:
        raise HTTPException(status_code=409, detail="La variante non è più disponibile o non esiste.")
        
    return {"status": "success", "message": "Prenotazione completata."}

@app.post("/api/beverages")
def book_beverage(request: schemas.BeverageBookingCreate, db: Session = Depends(get_db)):
    new_drink = models.BeverageBooking(booked_by=request.booked_by, beverage_name=request.beverage_name)
    db.add(new_drink)
    db.commit()
    return {"status": "success"}

@app.get("/api/admin/bookings", response_model=list[schemas.VariantAdmin])
def get_bookings(db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    variants = db.query(models.Variant)\
                 .options(joinedload(models.Variant.category))\
                 .filter(models.Variant.is_available == False)\
                 .all()
    return variants

@app.post("/api/admin/variants/{variant_id}/cancel")
def cancel_booking(variant_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    db.query(models.Variant).filter(models.Variant.id == variant_id).update({"is_available": True, "booked_by": None}, synchronize_session=False)
    db.commit()
    return {"status": "success"}

@app.get("/api/admin/beverages", response_model=list[schemas.BeverageBooking])
def get_admin_beverages(db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    return db.query(models.BeverageBooking).all()

@app.post("/api/admin/beverages/{beverage_id}/cancel")
def cancel_admin_beverage(beverage_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    db.query(models.BeverageBooking).filter(models.BeverageBooking.id == beverage_id).delete(synchronize_session=False)
    db.commit()
    return {"status": "success"}

@app.get("/")
def serve_landing():
    return FileResponse("landing.html")

@app.get("/food")
def serve_food():
    return FileResponse("index.html")

@app.get("/drinks")
def serve_drinks():
    return FileResponse("drinks.html")

@app.get("/admin")
def serve_admin(username: str = Depends(get_current_username)):
    return FileResponse("admin.html")
