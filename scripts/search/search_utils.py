"""
Utilidades compartidas para scripts de Azure AI Search
"""
import os
import re
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
import tiktoken

load_dotenv()


def get_search_index_client() -> SearchIndexClient:
    """
    Obtiene un cliente autenticado para gestionar índices de Azure AI Search

    Returns:
        SearchIndexClient configurado con credenciales
    """
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")

    if not endpoint or not key:
        raise ValueError("AZURE_SEARCH_ENDPOINT y AZURE_SEARCH_KEY requeridos en .env")

    return SearchIndexClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key)
    )


def get_search_client(index_name: str) -> SearchClient:
    """
    Obtiene un cliente autenticado para búsquedas en Azure AI Search

    Args:
        index_name: Nombre del índice

    Returns:
        SearchClient configurado con credenciales
    """
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")

    if not endpoint or not key:
        raise ValueError("AZURE_SEARCH_ENDPOINT y AZURE_SEARCH_KEY requeridos en .env")

    return SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(key)
    )


def get_openai_client() -> AzureOpenAI:
    """
    Obtiene un cliente autenticado para Azure OpenAI

    Returns:
        AzureOpenAI client configurado
    """
    api_key = os.getenv("AZURE_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

    if not api_key or not endpoint:
        raise ValueError("AZURE_API_KEY y AZURE_OPENAI_ENDPOINT requeridos en .env")

    return AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=endpoint
    )


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Cuenta el número de tokens en un texto

    Args:
        text: Texto a contar
        model: Modelo para el encoding (default: gpt-4o)

    Returns:
        Número de tokens
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback para modelos nuevos
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))


def clean_text(text: str) -> str:
    """
    Limpia texto OCR eliminando espacios extras y normalizando

    Args:
        text: Texto a limpiar

    Returns:
        Texto limpio
    """
    # Eliminar espacios múltiples
    text = re.sub(r'\s+', ' ', text)

    # Eliminar espacios al inicio/final de líneas
    text = '\n'.join(line.strip() for line in text.split('\n'))

    # Eliminar líneas vacías múltiples
    text = re.sub(r'\n\n+', '\n\n', text)

    return text.strip()


def parse_spanish_date(date_str: str) -> Optional[datetime]:
    """
    Parsea fechas en español a datetime

    Args:
        date_str: Fecha en formato español (ej: "26 de febrero de 2024")

    Returns:
        datetime object o None si no se puede parsear
    """
    # Mapeo de meses en español
    meses = {
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
    }

    # Normalizar string
    date_str = date_str.lower().strip()

    # Patrón: "DD de MMMM de YYYY"
    pattern = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
    match = re.search(pattern, date_str)

    if match:
        day = match.group(1).zfill(2)
        month = meses.get(match.group(2))
        year = match.group(3)

        if month:
            try:
                return datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
            except ValueError:
                pass

    # Intentar formato ISO (YYYY-MM-DD)
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        pass

    return None


def format_currency(amount: Optional[float], currency: str = "MXN") -> str:
    """
    Formatea montos para display

    Args:
        amount: Monto numérico
        currency: Moneda (MXN, USD, etc.)

    Returns:
        String formateado (ej: "$1,234.56 MXN")
    """
    if amount is None:
        return "N/A"

    return f"${amount:,.2f} {currency}"


def extract_ocr_text(ocr_file_path: str) -> str:
    """
    Extrae solo el texto completo de un archivo OCR
    (elimina header y metadata)

    Args:
        ocr_file_path: Ruta al archivo OCR .txt

    Returns:
        Texto completo del documento
    """
    with open(ocr_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Buscar la sección "TEXTO COMPLETO"
    start_marker = "TEXTO COMPLETO:"
    end_marker = "METADATA:"

    start_idx = content.find(start_marker)
    if start_idx == -1:
        # Si no hay marker, retornar todo
        return content

    # Saltar el marker y las líneas de separación
    start_idx = content.find('\n', start_idx) + 1
    start_idx = content.find('\n', start_idx) + 1

    end_idx = content.find(end_marker)
    if end_idx == -1:
        # Si no hay fin, tomar hasta el final
        text = content[start_idx:]
    else:
        text = content[start_idx:end_idx]

    return clean_text(text)


def get_ocr_filename(ocr_file_path: str) -> str:
    """
    Extrae el nombre del archivo original del OCR file

    Args:
        ocr_file_path: Ruta al archivo OCR

    Returns:
        Nombre del archivo original
    """
    with open(ocr_file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()

    # La primera línea es: "Archivo: nombre.pdf"
    if first_line.startswith("Archivo:"):
        return first_line.split(":", 1)[1].strip()

    # Fallback: usar el nombre del archivo OCR
    import os.path
    basename = os.path.basename(ocr_file_path)
    return basename.replace("_ocr.txt", ".pdf")
