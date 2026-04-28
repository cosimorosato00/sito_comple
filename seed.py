import pandas as pd
from database import SessionLocal, SessionLocal, engine
import models
import os

def seed_db():
    # Verifica se il DB è già popolato (per evitare doppi seed)
    db = SessionLocal()
    existing_categories = db.query(models.Category).count()
    if existing_categories > 0:
        print(f"Database già popolato ({existing_categories} categorie esistenti). Saltato.")
        db.close()
        return
    
    models.Base.metadata.create_all(bind=engine)
    
    excel_path = "scraping/ricette_con_c.xlsx"
    
    # Su Railway il file Excel potrebbe non esistere
    if not os.path.exists(excel_path):
        print(f"File Excel non trovato: {excel_path}")
        print("Seed saltato - assicurati di caricare il file Excel su Railway se necessario.")
        return
    
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"Errore di lettura dell'excel {excel_path}: {e}")
        return

    # Normalizza i nomi delle colonne
    cols = df.columns.str.lower()
    df.columns = cols
    
    if "categoria" not in cols or "variante" not in cols:
        print("Il file Excel deve contenere le colonne 'categoria' e 'variante'")
        print(f"Colonne trovate: {list(cols)}")
        return

    print("Inizio popolamento del DB...")
    
    # Processa prima le categorie
    unique_categories = df['categoria'].dropna().unique()
    
    cat_map = {}
    for cat_name in unique_categories:
        cat_name_str = str(cat_name).strip()
        normalized = " ".join(cat_name_str.lower().split())
        
        # Check esistenza
        db_cat = db.query(models.Category).filter(models.Category.normalized_name == normalized).first()
        if not db_cat:
            db_cat = models.Category(name=cat_name_str, normalized_name=normalized)
            db.add(db_cat)
            db.commit()
            db.refresh(db_cat)
        cat_map[normalized] = db_cat.id

    # Processa le varianti con un approccio Batch in RAM (veloce)
    added_variants = 0
    
    # Precarichiamo quelle già esistenti per non fare N query al DB (evita i blocchi DB SQLite)
    existing_vars = set()
    for v in db.query(models.Variant).all():
        existing_vars.add((v.category_id, v.name))
        
    varianti_da_inserire = []
    
    for index, row in df.iterrows():
        cat_name = str(row['categoria']).strip() if pd.notna(row['categoria']) else ""
        var_name = str(row['variante']).strip() if pd.notna(row['variante']) else ""
        
        if not cat_name or not var_name:
            continue
            
        normalized_cat = " ".join(cat_name.lower().split())
        cat_id = cat_map.get(normalized_cat)
        
        if cat_id:
            chiave = (cat_id, var_name)
            if chiave not in existing_vars:
                varianti_da_inserire.append(models.Variant(category_id=cat_id, name=var_name, is_available=True))
                existing_vars.add(chiave)
                added_variants += 1
                
    if varianti_da_inserire:
        db.add_all(varianti_da_inserire)
        
    db.commit()
    db.close()
    print(f"Database popolato con successo. Aggiunte/verificate {len(cat_map)} categorie e inserite {added_variants} varianti.")

if __name__ == "__main__":
    seed_db()
