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

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    resultados = []

    if query and db["documents"]:
        words_per_chunk = 30
        
        for doc in db["documents"]:
            if doc.content:
                words = doc.content.split()
                
                # Create blocks of 30 words
                for i in range(0, len(words), words_per_chunk):
                    bloque = " ".join(words[i:i+words_per_chunk])
                    
                    # Find the highest Levenshtein ratio for any single word in this block
                    best_ratio = 0.0
                    for word in words[i:i+words_per_chunk]:
                        # Clean punctuation off the word for an accurate match
                        clean_word = "".join(c for c in word if c.isalnum()).lower()
                        if clean_word:
                            import Levenshtein
                            ratio = Levenshtein.ratio(clean_word, query)
                            if ratio > best_ratio:
                                best_ratio = ratio
                    
                    # If the best matching word in the paragraph meets the threshold, save the whole block
                    if best_ratio >= 0.5: # Adjusted to 0.5 as requested in your original Python file
                        chunk_obj = TextChunk(bloque, doc.url)
                        chunk_obj.ratio = best_ratio
                        resultados.append(chunk_obj)

        # Sort results by highest ratio first
        resultados.sort(key=lambda x: x.ratio, reverse=True)

    return render_template('search.html', query=query, resultados=resultados)

if __name__ == '__main__':
    app.run(debug=True)