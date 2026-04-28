from playwright.sync_api import sync_playwright
import pandas as pd

def estrai_ricette_dynamic(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        
        # Attendiamo che il contenitore specifico sia presente nel DOM
        page.wait_for_selector('.list-block')
        
        # Estraiamo il contenuto della pagina
        html = page.content()
        browser.close()
        
        # Analizziamo l'HTML con BeautifulSoup
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        lista_ricette = []
        items = soup.select('div.list-block ul.list-items li a')
        for link in items:
            lista_ricette.append({'Titolo': link.get_text(strip=True), 'URL': link['href']})
        
        return lista_ricette

# Esegui lo script
url_target = "https://www.agrodolce.it/ricette/indice/c"
dati = estrai_ricette_dynamic(url_target)

if dati:
    df = pd.DataFrame(dati)
    df.to_excel('ricette_con_c.xlsx', index=False)
    print(f"Estratte {len(dati)} ricette. File salvato.")
else:
    print("Ancora nessun dato trovato.")
