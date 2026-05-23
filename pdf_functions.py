""" PDF functions for searching and processing PDF files from a webpage. """
import Levenshtein
from markitdown import MarkItDown
import requests
from bs4 import BeautifulSoup
import os
import fitz  
import pytesseract
from PIL import Image
import io

pytesseract.pytesseract.tesseract_cmd = r'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Tesseract-OCR\tesseract.exe'
class pdf_document:
    """ Class to represent a PDF document with its URL, pdf path and markdown path filename."""
    def __init__(self, url, pdf_path, markdown_path):
        self.url = url
        self.pdf_path = pdf_path
        self.markdown_path = markdown_path
        self.content = None
        self.convert_pdf_to_markdown()
    def convert_pdf_to_markdown(self):
        """ Converts a PDF file to Markdown format, with OCR fallback for scanned files."""
        try:
            converter = MarkItDown()
            result = converter.convert(self.pdf_path)
            markdown_content = result.markdown or result.text_content

    
            if not markdown_content or len(markdown_content.strip()) < 50:
                print(f"[{os.path.basename(self.pdf_path)}] Parece ser un PDF escaneado. Aplicando OCR...")
                ocr_text = extract_text_with_ocr(self.pdf_path)
                if ocr_text:
                    markdown_content = ocr_text

            if markdown_content:
                with open(self.markdown_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                self.content = markdown_content
                
        except Exception as e:
            print(f"Error converting PDF to Markdown: {e}")

def extract_text_with_ocr(pdf_path):
    """ Convierte el PDF a imágenes y aplica OCR para extraer el texto. """
    text_content = ""
    try:
        pdf_document = fitz.open(pdf_path)
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
           
            pix = page.get_pixmap(dpi=300) 
            img = Image.open(io.BytesIO(pix.tobytes()))
            
           
            text = pytesseract.image_to_string(img, lang='spa')
            
            text_content += f"\n\n### Página {page_num + 1}\n\n" + text
            
        pdf_document.close()
        return text_content
    except Exception as e:
        print(f"Error durante el OCR en {pdf_path}: {e}")
        return None
    
def get_webpage(url):
    """ Fetches the content of a webpage given its URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Check if the request was successful
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return None

def extract_pdf_links(html):
    """ Parses the HTML content and extracts all PDF links."""
    soup = BeautifulSoup(html, 'html.parser')
    pdf_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.endswith('.pdf'):
            pdf_links.append(href)
    return pdf_links

def download_pdf(url, filename):
    """ Downloads a PDF file from a given URL and saves it with a specified filename."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the PDF: {e}")

def get_pdfs(url = "https://fi-ing.unison.mx/acuerdos-de-sesiones-del-h-colegio-de-la-facultad-interdisciplinaria-de-ingenieria-2026/"):
    """ Main function to orchestrate the PDF downloading process."""
    
    download_path = "downloaded_pdfs"
    markdown_path = "markdown_files"
    if not os.path.exists(download_path):
        # Create the directory if it doesn't exist
        os.makedirs(download_path, exist_ok=True)
    if not os.path.exists(markdown_path):
        os.makedirs(markdown_path, exist_ok=True)
    html = get_webpage(url)
    if not html:
        print(f"Failed to fetch the webpage: {url}")
        exit(1)
    pdf_links = extract_pdf_links(html)
    pdf_dict = {} # Dictionary to store PDF URLs and their corresponding markdown paths
    for link in pdf_links:
        print(link)
        filename = link.split('/')[-1]
        downloaded_file = os.path.join(download_path, filename) 
        download_pdf(link, f"{downloaded_file}")
        markdown_file = os.path.join(markdown_path, f"{os.path.splitext(filename)[0]}.md")
        pdf_doc = pdf_document(link, downloaded_file, markdown_file)
        pdf_dict[filename] = pdf_doc
        print(f"Downloaded: {downloaded_file}")
    return pdf_dict

def buscar_palabras_ratio(frases:list, frase_a_buscar:str, umbral:float=0.50)->list:
    """ Busca una frase en una lista de frases """
    frases_encontradas = []
    frase_a_buscar = frase_a_buscar.lower()
    for frase in frases:
        frase_lower = frase.frase.lower()
        ratio = Levenshtein.ratio(frase_lower, frase_a_buscar)
        if ratio >=umbral:
            frase.ratio = ratio
            frases_encontradas.append(frase)
    return frases_encontradas

def main():
    """ Main function to orchestrate the PDF downloading process."""
    pdf_dictionary = get_pdfs()
    print(pdf_dictionary.keys())
    main_dictionary = {}
    for key, pdf_doc in pdf_dictionary.items():
        content = pdf_doc.content 
        # split the content into 3 words chunks
        chunk_length = 20
        chunks = [content[i:i+chunk_length] for i in range(0, len(content), chunk_length)]
        for chunk in chunks:
            if chunk not in main_dictionary:
                main_dictionary[chunk] = [key]
            else:
                main_dictionary[chunk].append(key)
    print(main_dictionary.keys())

if  __name__ == "__main__":
    main()