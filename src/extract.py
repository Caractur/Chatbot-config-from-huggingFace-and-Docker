import fitz, trafilatura
from bs4 import BeautifulSoup

def extract_text_from_pdf(binary: bytes) -> str:
    text = []
    with fitz.open(stream=binary, filetype="pdf") as doc:
        for page in doc:
            text.append(page.get_text())
    return "\n".join(text).strip()

def extract_text_from_html(html_bytes: bytes) -> tuple[str, str]:
    html_str = html_bytes.decode("utf-8", errors="replace")
    title = ""
    try:
        soup = BeautifulSoup(html_str, "lxml")
        if soup.title and soup.title.text:
            title = soup.title.text.strip()
    except Exception:
        pass
    text = trafilatura.extract(html_str, include_links=False, include_tables=False) or ""
    return title, text.strip()
