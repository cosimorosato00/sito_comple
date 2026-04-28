from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
import secrets
import models, schemas
from database import engine, get_db, SessionLocal
from pydantic import BaseModel
class PhotoUpdate(BaseModel):
    photo_url: str

# Crea le tabelle automaticamente
models.Base.metadata.create_all(bind=engine)

# Seed automatico al primo avvio (solo se il DB è vuoto)
def auto_seed():
    db = SessionLocal()
    try:
        if db.query(models.Category).count() > 0:
            return  # Già popolato
        print("Esecuzione seed automatico...")
        import pandas as pd
        import os
        excel_path = "scraping/ricette_con_c.xlsx"
        if not os.path.exists(excel_path):
            print(f"Excel non trovato: {excel_path}")
            return
        df = pd.read_excel(excel_path)
        cols = df.columns.str.lower()
        df.columns = cols
        if "categoria" not in cols:
            return
        unique_categories = df['categoria'].dropna().unique()
        cat_map = {}
        for cat_name in unique_categories:
            cat_name_str = str(cat_name).strip()
            normalized = " ".join(cat_name_str.lower().split())
            db_cat = models.Category(name=cat_name_str, normalized_name=normalized)
            db.add(db_cat)
            db.flush()
            cat_map[normalized] = db_cat.id
        added = 0
        for index, row in df.iterrows():
            cat_name = str(row['categoria']).strip() if pd.notna(row['categoria']) else ""
            var_name = str(row['variante']).strip() if pd.notna(row['variante']) else ""
            if not cat_name or not var_name:
                continue
            normalized_cat = " ".join(cat_name.lower().split())
            cat_id = cat_map.get(normalized_cat)
            if cat_id:
                db_var = models.Variant(category_id=cat_id, name=var_name, is_available=True)
                db.add(db_var)
                added += 1
        db.commit()
        print(f"Seed completato: {len(cat_map)} categorie, {added} varianti")
    except Exception as e:
        print(f"Errore seed: {e}")
        db.rollback()
    finally:
        db.close()

# Esegui seed in background
auto_seed()

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

@app.post("/api/variants/{variant_id}/update-photo")
def update_variant_photo(variant_id: int, request: PhotoUpdate, db: Session = Depends(get_db)):
    variant = db.query(models.Variant).filter(models.Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variante non trovata")
    variant.photo_url = request.photo_url
    db.commit()
    return {"status": "success", "message": "Foto aggiornata"}

@app.post("/api/admin/variants/{variant_id}/cancel")
def cancel_booking(variant_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    # Aggiorniamo anche photo_url a None
    db.query(models.Variant).filter(models.Variant.id == variant_id).update({
        "is_available": True, 
        "booked_by": None,
        "photo_url": None  # <--- AGGIUNTA LOGICA
    }, synchronize_session=False)
    
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

@app.post("/api/admin/seed")
def run_seed(db: Session = Depends(get_db)):
    """Endpoint per eseguire il seed manualmente (solo per setup iniziale)"""
    import pandas as pd
    import os
    
    # Verifica se il DB è già popolato
    existing = db.query(models.Category).count()
    if existing > 0:
        return {"status": "already_seeded", "categories": existing}
    
    excel_path = "scraping/ricette_con_c.xlsx"
    if not os.path.exists(excel_path):
        return {"status": "error", "detail": "File Excel non trovato"}
    
    try:
        df = pd.read_excel(excel_path)
        cols = df.columns.str.lower()
        df.columns = cols
        
        if "categoria" not in cols or "variante" not in cols:
            return {"status": "error", "detail": "Colonne mancanti nel file Excel"}
        
        # Crea categorie
        unique_categories = df['categoria'].dropna().unique()
        cat_map = {}
        
        for cat_name in unique_categories:
            cat_name_str = str(cat_name).strip()
            normalized = " ".join(cat_name_str.lower().split())
            db_cat = models.Category(name=cat_name_str, normalized_name=normalized)
            db.add(db_cat)
            db.flush()
            cat_map[normalized] = db_cat.id
        
        # Crea varianti
        added = 0
        for index, row in df.iterrows():
            cat_name = str(row['categoria']).strip() if pd.notna(row['categoria']) else ""
            var_name = str(row['variante']).strip() if pd.notna(row['variante']) else ""
            
            if not cat_name or not var_name:
                continue
            
            normalized_cat = " ".join(cat_name.lower().split())
            cat_id = cat_map.get(normalized_cat)
            
            if cat_id:
                db_var = models.Variant(category_id=cat_id, name=var_name, is_available=True)
                db.add(db_var)
                added += 1
        
        db.commit()
        return {"status": "success", "categories": len(cat_map), "variants": added}
        
    except Exception as e:
        db.rollback()
        return {"status": "error", "detail": str(e)}
