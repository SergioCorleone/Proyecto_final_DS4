from flask import Flask, render_template, request, redirect, url_for, flash
import pdf_functions
import re

app = Flask(__name__)
app.secret_key = 'super_secret_key' # Needed for flash messages

# In-memory "Database" simulation
db = {
    "urls_to_scrape": [], # List of dicts: {"id": int, "url": str, "status": str, "files": []}
    "documents": []       # Stores the pdf_document objects returned by your script
}

# Helper class to format data for your buscar_palabras_ratio function
class TextChunk:
    def __init__(self, frase, url_origen):
        self.frase = frase
        self.url_origen = url_origen
        self.ratio = 0.0

@app.route('/')
def home():
    total_docs = len(db["documents"])
    total_words = sum(len(str(doc.content).split()) for doc in db["documents"] if doc.content)
    
    # Extract year from the URL (e.g., matching "2025" or "2026")
    docs_by_year = {}
    for doc in db["documents"]:
        match = re.search(r'(20\d{2})', doc.url)
        year = match.group(1) if match else "Unknown"
        docs_by_year[year] = docs_by_year.get(year, 0) + 1

    return render_template('home.html', total_docs=total_docs, total_words=total_words, docs_by_year=docs_by_year)

@app.route('/configuration', methods=['GET', 'POST'])
def configuration():
    if request.method == 'POST':
        new_url = request.form.get('url_input')
        if new_url:
            new_entry = {
                "id": len(db["urls_to_scrape"]) + 1,
                "url": new_url,
                "status": "No escrapeada",
                "files": []
            }
            db["urls_to_scrape"].append(new_entry)
            flash("URL agregada exitosamente.", "success")
        return redirect(url_for('configuration'))
    
    return render_template('configuration.html', urls=db["urls_to_scrape"])

@app.route('/scrapper')
def scrapper():
    return render_template('scrapper.html', urls=db["urls_to_scrape"])

@app.route('/run_scraper/<int:url_id>')
def run_scraper(url_id):
    # Find the URL in our DB
    target = next((item for item in db["urls_to_scrape"] if item["id"] == url_id), None)
    if target:
        try:
            # Call your get_pdfs function
            pdf_dictionary = pdf_functions.get_pdfs(target["url"])
            
            # Update DB with results
            target["status"] = "Escrapeada"
            target["files"] = list(pdf_dictionary.keys())
            db["documents"].extend(pdf_dictionary.values())
            
            flash(f"Scrape completado para {target['url']}", "success")
        except Exception as e:
            flash(f"Error al scrapear: {str(e)}", "danger")
            
    return redirect(url_for('scrapper'))

import Levenshtein # Asegúrate de tenerlo importado arriba en tu app.py

import Levenshtein

@app.route('/search')
def search():
    query = request.args.get('query', '').lower().strip()
    
    try:
        threshold = float(request.args.get('threshold', 0.5))
    except ValueError:
        threshold = 0.5

    resultados = []

    if query and db["documents"]:
        words_per_chunk = 30
        
        # 1. Contamos cuántas palabras tiene la búsqueda
        query_words = query.split()
        query_len = len(query_words)
        # Limpiamos la búsqueda de comas o puntos para mayor precisión
        query_limpia = "".join(c for c in query if c.isalnum() or c.isspace())
        
        for doc in db["documents"]:
            if doc.content:
                words = doc.content.split()
                
                # 2. Recorremos por bloques de 30 palabras para mostrar en pantalla
                for i in range(0, len(words), words_per_chunk):
                    bloque_palabras = words[i:i+words_per_chunk]
                    bloque_texto = " ".join(bloque_palabras)
                    
                    best_ratio = 0.0
                    
                    # 3. VENTANA DESLIZANTE:
                    # Si el usuario busca 2 palabras, revisamos el bloque de 2 en 2 palabras.
                    if query_len <= len(bloque_palabras):
                        for j in range(len(bloque_palabras) - query_len + 1):
                            # Extraemos una ventanita de palabras del mismo tamaño que la búsqueda
                            ventana_palabras = bloque_palabras[j:j+query_len]
                            ventana_texto = " ".join(ventana_palabras).lower()
                            
                            # Limpiamos la ventanita de comas o puntos
                            ventana_limpia = "".join(c for c in ventana_texto if c.isalnum() or c.isspace())
                            
                            # Comparamos del mismo tamaño: ej. 2 palabras vs 2 palabras
                            ratio = Levenshtein.ratio(query_limpia, ventana_limpia)
                            
                            if ratio > best_ratio:
                                best_ratio = ratio
                    else:
                        # Si la búsqueda es más grande que el bloque, comparamos todo directo
                        best_ratio = Levenshtein.ratio(query_limpia, bloque_texto.lower())
                    
                    # 4. Si el mejor pedacito supera el slider, guardamos el bloque entero
                    if best_ratio >= threshold:
                        chunk_obj = TextChunk(bloque_texto, doc.url)
                        chunk_obj.ratio = best_ratio
                        resultados.append(chunk_obj)

        # Ordenar los resultados para mostrar el mayor porcentaje primero
        resultados.sort(key=lambda x: x.ratio, reverse=True)

    return render_template('search.html', query=query, threshold=threshold, resultados=resultados)

if __name__ == '__main__':
    app.run(debug=True)