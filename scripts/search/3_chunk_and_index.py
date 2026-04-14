"""
Chunking, embedding, e indexación de contratos en Azure AI Search
Procesa metadata + texto OCR → chunks → embeddings → Azure AI Search
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import re

# Agregar path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.search_config import (
    CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE, INDEX_NAME
)
from scripts.search.search_utils import (
    get_search_client, get_openai_client,
    extract_ocr_text, count_tokens, clean_text
)
from scripts.search.semantic_chunker import chunk_text_semantic


def sanitize_document_id(text: str) -> str:
    """
    Sanitiza un string para usarlo como ID en Azure AI Search
    Solo permite: letras, números, _, -, =

    Args:
        text: Texto a sanitizar

    Returns:
        String sanitizado válido para Azure AI Search
    """
    import re
    # Reemplazar espacios por guiones
    text = text.replace(' ', '-')
    # Remover caracteres especiales, mantener solo: a-z, A-Z, 0-9, _, -, =
    text = re.sub(r'[^a-zA-Z0-9_\-=]', '', text)
    # Evitar IDs que empiecen con guión
    text = text.lstrip('-')
    return text


def extract_page_number_from_text(text: str) -> Optional[int]:
    """
    Extrae el número de página del texto que contiene marcadores [Page N]

    Args:
        text: Texto que puede contener [Page N]

    Returns:
        Número de página o None si no se encuentra
    """
    match = re.search(r'\[Page (\d+)\]', text)
    if match:
        return int(match.group(1))
    return None


def chunk_text_with_pages(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Dict[str, any]]:
    """
    Divide texto en chunks con overlap, respetando límites de oraciones y rastreando páginas

    Args:
        text: Texto a dividir (puede contener marcadores [Page N])
        chunk_size: Tamaño máximo en tokens
        overlap: Tokens de overlap entre chunks

    Returns:
        Lista de diccionarios con 'text' y 'page_number'
    """
    # Dividir en oraciones (respeta . ! ?)
    sentences = re.split(r'([.!?]\s+)', text)

    # Reconstruir oraciones completas con tracking de página
    full_sentences = []
    current_page = 1

    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else '')

        # Buscar marcador de página en esta oración
        page_match = re.search(r'\[Page (\d+)\]', sentence)
        if page_match:
            current_page = int(page_match.group(1))
            # Remover el marcador de página del texto
            sentence = re.sub(r'\[Page \d+\]\s*', '', sentence)

        if sentence.strip():  # Solo agregar si no está vacía después de limpiar
            full_sentences.append((sentence, current_page))

    # Agrupar oraciones en chunks
    chunks = []
    current_chunk = []
    current_tokens = 0
    chunk_pages = set()

    for sentence, page_num in full_sentences:
        sentence_tokens = count_tokens(sentence)

        # Si agregar esta oración excede el límite
        if current_tokens + sentence_tokens > chunk_size and current_chunk:
            # Guardar chunk actual con el número de página más frecuente
            chunk_text = ''.join([s for s, _ in current_chunk])
            primary_page = min(chunk_pages) if chunk_pages else 1
            chunks.append({
                'text': chunk_text,
                'page_number': primary_page
            })

            # Calcular cuánto texto mantener para overlap
            overlap_text = []
            overlap_tokens = 0
            overlap_pages = set()

            for sent, pg in reversed(current_chunk):
                sent_tokens = count_tokens(sent)
                if overlap_tokens + sent_tokens <= overlap:
                    overlap_text.insert(0, (sent, pg))
                    overlap_tokens += sent_tokens
                    overlap_pages.add(pg)
                else:
                    break

            # Iniciar nuevo chunk con overlap
            current_chunk = overlap_text
            current_tokens = overlap_tokens
            chunk_pages = overlap_pages

        # Agregar oración al chunk actual
        current_chunk.append((sentence, page_num))
        current_tokens += sentence_tokens
        chunk_pages.add(page_num)

    # Agregar último chunk si existe
    if current_chunk:
        chunk_text = ''.join([s for s, _ in current_chunk])
        primary_page = min(chunk_pages) if chunk_pages else 1
        chunks.append({
            'text': chunk_text,
            'page_number': primary_page
        })

    return chunks


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Divide texto en chunks con overlap, respetando límites de oraciones
    DEPRECATED: Usar chunk_text_with_pages() para incluir tracking de páginas

    Args:
        text: Texto a dividir
        chunk_size: Tamaño máximo en tokens
        overlap: Tokens de overlap entre chunks

    Returns:
        Lista de chunks de texto
    """
    chunks_with_pages = chunk_text_with_pages(text, chunk_size, overlap)
    return [chunk['text'] for chunk in chunks_with_pages]


def create_chunk_with_metadata(
    chunk_text: str,
    chunk_id: int,
    total_chunks: int,
    metadata: Dict,
    filename: str
) -> str:
    """
    Crea un chunk con metadata prefix para mejor semantic matching

    Args:
        chunk_text: Texto del chunk
        chunk_id: Número del chunk
        total_chunks: Total de chunks del documento
        metadata: Metadata del contrato
        filename: Nombre del archivo

    Returns:
        Chunk con metadata prefix
    """
    # Crear prefix con metadata relevante
    prefix_parts = [
        f"DOCUMENTO: {metadata.get('titulo', filename)}",
        f"TIPO: {metadata.get('tipo_contrato', 'N/A')}",
    ]

    if metadata.get('proveedor'):
        prefix_parts.append(f"PROVEEDOR: {metadata['proveedor']}")

    if metadata.get('cliente'):
        prefix_parts.append(f"CLIENTE: {metadata['cliente']}")

    if metadata.get('fecha_contrato'):
        prefix_parts.append(f"FECHA: {metadata['fecha_contrato']}")

    prefix = '\n'.join(prefix_parts)

    return f"{prefix}\n\n{chunk_text}"


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Genera embeddings para una lista de textos

    Args:
        texts: Lista de textos

    Returns:
        Lista de vectores de embeddings
    """
    client = get_openai_client()
    embeddings = []

    # Procesar en batches
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i:i + EMBEDDING_BATCH_SIZE]

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch
        )

        batch_embeddings = [item.embedding for item in response.data]
        embeddings.extend(batch_embeddings)

    return embeddings


def process_contract(
    ocr_file: Path,
    metadata_file: Path,
    contract_id: str,
    mode: str = "sentence"
) -> List[Dict]:
    """
    Procesa un contrato: chunking + embeddings

    Args:
        ocr_file: Archivo OCR con texto
        metadata_file: Archivo JSON con metadata
        contract_id: ID único del contrato

    Returns:
        Lista de documentos listos para indexar
    """
    # Cargar metadata
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    # Chunking según el modo
    if mode == "semantic":
        print(f"   🧠 Modo semántico activado")

        # Para modo semántico, leer archivo completo (con marcadores y estructura)
        with open(ocr_file, 'r', encoding='utf-8') as f:
            full_content = f.read()

        # Extraer solo la sección de texto completo
        start_marker = "TEXTO COMPLETO:"
        start_marker_line = "=" * 60
        if start_marker in full_content:
            parts = full_content.split(start_marker, 1)
            if len(parts) > 1:
                text = parts[1].split(start_marker_line, 1)
                if len(text) > 1:
                    text = text[1].strip()
                else:
                    text = parts[1].strip()
            else:
                text = full_content
        else:
            text = full_content

        chunks_semantic = chunk_text_semantic(text, count_tokens)

        # Convertir a formato compatible con chunks_with_pages
        chunks_with_pages = []
        for chunk_data in chunks_semantic:
            chunks_with_pages.append({
                'text': chunk_data['text'],
                'page_number': chunk_data['pagina_inicio'],
                'semantic_metadata': {
                    'seccion_tipo': chunk_data.get('seccion_tipo'),
                    'seccion_nombre': chunk_data.get('seccion_nombre'),
                    'numero_clausula': chunk_data.get('numero_clausula'),
                    'pagina_inicio': chunk_data.get('pagina_inicio'),
                    'pagina_fin': chunk_data.get('pagina_fin'),
                }
            })
        print(f"   📄 Texto: {len(text):,} chars → {len(chunks_with_pages)} chunks semánticos")
    else:
        # Extraer texto (mantener marcadores de página)
        text = extract_ocr_text(str(ocr_file))
        # Chunking tradicional con tracking de páginas
        chunks_with_pages = chunk_text_with_pages(text)
        print(f"   📄 Texto: {len(text):,} chars → {len(chunks_with_pages)} chunks")

    # Crear chunks con metadata
    chunks_with_metadata = [
        create_chunk_with_metadata(
            chunk_text=chunk_data['text'],
            chunk_id=idx,
            total_chunks=len(chunks_with_pages),
            metadata=metadata,
            filename=metadata.get('nombre_archivo', ocr_file.name)
        )
        for idx, chunk_data in enumerate(chunks_with_pages)
    ]

    # Generar embeddings
    print(f"   🔢 Generando embeddings...")
    embeddings = generate_embeddings(chunks_with_metadata)

    # Crear documentos para indexar
    documents = []
    for idx, (chunk_data, embedding) in enumerate(zip(chunks_with_pages, embeddings)):
        doc_id = f"{contract_id}-chunk-{idx:03d}"

        # Parsear fechas si existen
        fecha_contrato = None
        fecha_vencimiento = None

        if metadata.get('fecha_contrato'):
            try:
                fecha_contrato = datetime.fromisoformat(metadata['fecha_contrato']).isoformat() + 'Z'
            except:
                pass

        if metadata.get('fecha_vencimiento'):
            try:
                fecha_vencimiento = datetime.fromisoformat(metadata['fecha_vencimiento']).isoformat() + 'Z'
            except:
                pass

        # Extraer metadata semántica si existe
        semantic_meta = chunk_data.get('semantic_metadata', {})

        document = {
            "id": doc_id,
            "content": chunk_data['text'],
            "content_vector": embedding,
            "titulo": metadata.get('titulo'),
            "tipo_contrato": metadata.get('tipo_contrato'),
            "numero_contrato": metadata.get('numero_contrato'),
            "fecha_contrato": fecha_contrato,
            "fecha_vencimiento": fecha_vencimiento,
            "proveedor": metadata.get('proveedor'),
            "cliente": metadata.get('cliente'),
            "monto": metadata.get('monto'),
            "moneda": metadata.get('moneda'),
            "nombre_archivo": metadata.get('nombre_archivo'),
            "url_sharepoint": None,  # Por ahora null, se llenará con SharePoint integration
            "numero_pagina": chunk_data['page_number'],
            "chunk_id": idx,
            "total_chunks": len(chunks_with_pages),
            "fecha_indexacion": datetime.now().isoformat() + 'Z',
            "partes_firmantes": metadata.get('partes_firmantes', []),
            "clausulas_principales": metadata.get('clausulas_principales', []),
            # Campos semánticos (Phase 2)
            "seccion_tipo": semantic_meta.get('seccion_tipo'),
            "seccion_nombre": semantic_meta.get('seccion_nombre'),
            "numero_clausula": semantic_meta.get('numero_clausula'),
            "pagina_inicio": semantic_meta.get('pagina_inicio'),
            "pagina_fin": semantic_meta.get('pagina_fin'),
            "chunking_mode": mode,
        }

        documents.append(document)

    return documents


def upload_documents(documents: List[Dict]):
    """
    Sube documentos a Azure AI Search en batches

    Args:
        documents: Lista de documentos a indexar
    """
    client = get_search_client(INDEX_NAME)

    batch_size = 100  # Azure AI Search recomienda batches de 100-1000

    print(f"\n   ☁️  Subiendo {len(documents)} documentos a Azure AI Search...")

    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]

        try:
            result = client.upload_documents(documents=batch)

            # Verificar resultados
            succeeded = sum(1 for r in result if r.succeeded)
            failed = len(result) - succeeded

            if failed > 0:
                print(f"      ⚠️  Batch {i // batch_size + 1}: {succeeded} OK, {failed} fallidos")
            else:
                print(f"      ✅ Batch {i // batch_size + 1}: {succeeded} documentos")

        except Exception as e:
            print(f"      ❌ Error en batch {i // batch_size + 1}: {str(e)}")


def process_all_contracts(mode: str = "sentence"):
    """Procesa todos los contratos y los indexa

    Args:
        mode: Modo de chunking - "sentence" (tradicional) o "semantic" (estructura)
    """

    print("=" * 70)
    print(f"🚀 Procesando contratos para indexación - Modo: {mode.upper()}")
    print("=" * 70)

    metadata_dir = Path("output/metadata")
    ocr_dir = Path("output/ocr_results")

    # Encontrar archivos de metadata
    metadata_files = sorted(metadata_dir.glob("*_metadata.json"))

    if not metadata_files:
        print(f"\n❌ No se encontraron archivos de metadata en {metadata_dir}")
        print(f"   Ejecuta primero: python scripts/search/2_extract_metadata.py")
        return

    print(f"\n📁 Encontrados: {len(metadata_files)} contratos con metadata")
    print("-" * 70)

    all_documents = []
    total_chunks = 0

    # Procesar cada contrato
    for idx, metadata_file in enumerate(metadata_files, 1):
        # Encontrar archivo OCR correspondiente
        ocr_filename = metadata_file.name.replace("_metadata.json", ".txt")
        ocr_file = ocr_dir / ocr_filename

        if not ocr_file.exists():
            print(f"\n[{idx}/{len(metadata_files)}] ❌ No se encontró OCR: {ocr_filename}")
            continue

        # Generar ID de contrato (sanitizado para Azure AI Search)
        contract_id = sanitize_document_id(
            metadata_file.stem.replace("_ocr_metadata", "")
        )

        print(f"\n[{idx}/{len(metadata_files)}] {ocr_file.stem.replace('_ocr', '')}")

        try:
            documents = process_contract(ocr_file, metadata_file, contract_id, mode=mode)
            all_documents.extend(documents)
            total_chunks += len(documents)
            print(f"   ✅ {len(documents)} chunks listos")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

    # Subir todos los documentos
    if all_documents:
        print("\n" + "=" * 70)
        print(f"📤 Indexando {total_chunks} chunks en Azure AI Search")
        print("=" * 70)

        upload_documents(all_documents)

        # Resumen final
        print("\n" + "=" * 70)
        print("📊 Resumen Final")
        print("=" * 70)
        print(f"\n✅ Contratos procesados: {len(metadata_files)}")
        print(f"📦 Total de chunks: {total_chunks}")
        print(f"☁️  Indexados en: {INDEX_NAME}")

        # Estimación de costos
        total_tokens = sum(count_tokens(doc["content"]) for doc in all_documents)
        embedding_cost = (total_tokens / 1_000_000) * 0.13  # $0.13 por 1M tokens
        print(f"\n💰 Costo estimado de embeddings: ${embedding_cost:.4f} USD")

        print("\n" + "=" * 70)
        print("✅ Proceso completado")
        print("=" * 70)
        print(f"\n🎯 Siguiente paso:")
        print(f"   python scripts/search/4_test_search.py")

    else:
        print("\n❌ No se procesaron documentos")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Chunk and index contracts')
    parser.add_argument(
        '--mode',
        type=str,
        choices=['sentence', 'semantic'],
        default='sentence',
        help='Chunking mode: sentence (traditional) or semantic (structure-based)'
    )

    args = parser.parse_args()

    process_all_contracts(mode=args.mode)
