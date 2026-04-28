import requests
from bs4 import BeautifulSoup
import pandas as pd

def estrai_ricette(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    lista_dati = []
    
    # Cerchiamo tutti i blocchi che contengono le ricette
    blocchi = soup.find_all('div', class_='list-block')
    
    for blocco in blocchi:
        # Estraiamo la categoria dal tag h6 dentro la colonna 3
        col3 = blocco.find('div', class_='col-3')
        categoria = col3.h6.get_text(strip=True) if col3 and col3.h6 else "N/A"
        
        # Estraiamo i link dalla lista nella colonna 9
        col9 = blocco.find('div', class_='col-9')
        if col9:
            links = col9.select('ul.list-items li a')
            for link in links:
                lista_dati.append({
                    'Categoria': categoria,
                    'Variante': link.get_text(strip=True),
                    'URL': link['href']
                })
                
    return lista_dati

# Inserisci l'URL corretto
url_target = "https://www.agrodolce.it/ricette/indice/c" 
dati = estrai_ricette(url_target)

if dati:
    df = pd.DataFrame(dati)
    df.to_excel('ricette_con_c.xlsx', index=False)
    print(f"Estratte {len(dati)} ricette. File 'ricette_con_c.xlsx' creato.")
else:
    print("Nessun dato trovato. Assicurati che l'HTML scaricato contenga effettivamente i div 'list-block'.")
