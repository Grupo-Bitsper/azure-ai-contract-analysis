"""
Semantic Chunker - Phase 2
Crea chunks basados en la estructura semántica del documento usando Document Intelligence layout
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SemanticSection:
    """Representa una sección semántica del documento"""
    tipo: str  # DECLARACIONES, CLAUSULA, ANEXO, METADATA
    nombre: str  # Título de la sección
    numero: Optional[str]  # Número de cláusula (ej: "PRIMERA", "DECIMA_SEXTA")
    contenido: str  # Texto completo
    pagina_inicio: int  # Primera página
    pagina_fin: int  # Última página
    nivel: int  # Nivel de jerarquía (0=principal, 1=sub-sección)


class SemanticChunker:
    """
    Chunker que divide documentos basándose en su estructura semántica
    en lugar de límites arbitrarios de tokens
    """

    # Patrones para detectar secciones
    CLAUSULA_PATTERN = re.compile(
        r'(Primera|Segunda|Tercera|Cuarta|Quinta|Sexta|S[eé]ptima|Octava|'
        r'Novena|D[eé]cima|Und[eé]cima|Duod[eé]cima|Decima\s+Primera|Decima\s+Segunda|'
        r'Decima\s+Tercera|Decima\s+Cuarta|Decima\s+Quinta|Decima\s+Sexta|'
        r'Decima\s+S[eé]ptima|Decima\s+Octava|Decima\s+Novena|Vig[eé]sima)\s*[.:\-]',
        re.IGNORECASE
    )

    DECLARACIONES_PATTERN = re.compile(
        r'DECLARACIONES|Declara(?:n|ciones)',
        re.IGNORECASE
    )

    ANEXO_PATTERN = re.compile(
        r'ANEXO\s*["\']?([A-Z])["\']?',
        re.IGNORECASE
    )

    # Mapeo de números de cláusulas
    NUMERO_MAPPING = {
        'primera': '01', 'segunda': '02', 'tercera': '03', 'cuarta': '04',
        'quinta': '05', 'sexta': '06', 'séptima': '07', 'septima': '07',
        'octava': '08', 'novena': '09', 'décima': '10', 'decima': '10',
        'undécima': '11', 'undecima': '11', 'duodécima': '12', 'duodecima': '12',
        'decima primera': '11', 'decima segunda': '12', 'decima tercera': '13',
        'decima cuarta': '14', 'decima quinta': '15', 'decima sexta': '16',
        'decima séptima': '17', 'decima septima': '17', 'decima octava': '18',
        'decima novena': '19', 'vigésima': '20', 'vigesima': '20',
    }

    def __init__(self, max_chunk_size: int = 1024, min_chunk_size: int = 256):
        """
        Args:
            max_chunk_size: Tamaño máximo en tokens para un chunk (must be < 8192 for embeddings)
            min_chunk_size: Tamaño mínimo en tokens para un chunk
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size

    def extract_sections(self, text: str) -> List[SemanticSection]:
        """
        Extrae secciones semánticas del texto

        Args:
            text: Texto completo del documento con marcadores [Page N]

        Returns:
            Lista de secciones semánticas
        """
        sections = []
        lines = text.split('\n')
        current_section = None
        current_lines = []
        current_page = 1

        for line in lines:
            # Detectar marcador de página
            page_match = re.match(r'\[Page (\d+)\]', line)
            if page_match:
                current_page = int(page_match.group(1))
                continue

            # Detectar nueva sección
            new_section = self._detect_section(line, current_page)

            if new_section:
                # Guardar sección anterior
                if current_section and current_lines:
                    current_section.contenido = '\n'.join(current_lines).strip()
                    current_section.pagina_fin = current_page
                    if current_section.contenido:  # Solo agregar si tiene contenido
                        sections.append(current_section)

                # Iniciar nueva sección
                current_section = new_section
                current_lines = [line]
            elif current_section:
                # Continuar sección actual
                current_lines.append(line)
            else:
                # Texto antes de la primera sección (metadata, encabezados)
                if not current_section:
                    current_section = SemanticSection(
                        tipo='METADATA',
                        nombre='Encabezado',
                        numero=None,
                        contenido='',
                        pagina_inicio=current_page,
                        pagina_fin=current_page,
                        nivel=0
                    )
                    current_lines = [line]

        # Agregar última sección
        if current_section and current_lines:
            current_section.contenido = '\n'.join(current_lines).strip()
            current_section.pagina_fin = current_page
            if current_section.contenido:
                sections.append(current_section)

        return sections

    def _detect_section(self, line: str, page: int) -> Optional[SemanticSection]:
        """
        Detecta si una línea marca el inicio de una nueva sección

        Args:
            line: Línea de texto
            page: Número de página actual

        Returns:
            SemanticSection si se detecta nueva sección, None si no
        """
        line_upper = line.strip()

        # Detectar DECLARACIONES
        if self.DECLARACIONES_PATTERN.search(line_upper):
            return SemanticSection(
                tipo='DECLARACIONES',
                nombre='Declaraciones',
                numero=None,
                contenido='',
                pagina_inicio=page,
                pagina_fin=page,
                nivel=0
            )

        # Detectar CLÁUSULAS
        clausula_match = self.CLAUSULA_PATTERN.search(line)
        if clausula_match:
            numero_texto = clausula_match.group(1).lower().replace('é', 'e')
            numero = self.NUMERO_MAPPING.get(numero_texto, '00')

            # Extraer nombre de la cláusula
            nombre_match = re.search(r'[:\-]\s*(.+?)(?:\.|$)', line, re.IGNORECASE)
            nombre = nombre_match.group(1).strip() if nombre_match else 'Sin título'

            return SemanticSection(
                tipo='CLAUSULA',
                nombre=nombre,
                numero=numero,
                contenido='',
                pagina_inicio=page,
                pagina_fin=page,
                nivel=0
            )

        # Detectar ANEXOS
        anexo_match = self.ANEXO_PATTERN.search(line_upper)
        if anexo_match:
            letra = anexo_match.group(1)
            # Extraer descripción del anexo
            desc_match = re.search(r'ANEXO\s*["\']?[A-Z]["\']?\s*[:\-]?\s*(.+)', line_upper, re.IGNORECASE)
            nombre = desc_match.group(1).strip() if desc_match else f'Anexo {letra}'

            return SemanticSection(
                tipo='ANEXO',
                nombre=nombre,
                numero=letra,
                contenido='',
                pagina_inicio=page,
                pagina_fin=page,
                nivel=0
            )

        return None

    def chunk_by_sections(
        self,
        sections: List[SemanticSection],
        count_tokens_fn
    ) -> List[Dict]:
        """
        Crea chunks a partir de secciones semánticas

        Args:
            sections: Lista de secciones semánticas
            count_tokens_fn: Función para contar tokens

        Returns:
            Lista de chunks con metadata semántica
        """
        chunks = []

        for section in sections:
            content = section.contenido
            tokens = count_tokens_fn(content)

            # Si la sección cabe en un chunk, crear un solo chunk
            if tokens <= self.max_chunk_size:
                chunk = self._create_chunk(section, content)
                chunks.append(chunk)

            # Si la sección es muy grande, dividirla en sub-chunks
            else:
                sub_chunks = self._split_large_section(
                    section,
                    content,
                    count_tokens_fn
                )
                chunks.extend(sub_chunks)

        # SAFETY CHECK: Verificar que ningún chunk exceda el límite
        # (puede pasar si el header es muy largo o hay texto sin párrafos)
        final_chunks = []
        for chunk in chunks:
            chunk_tokens = count_tokens_fn(chunk['text'])
            if chunk_tokens > self.max_chunk_size:
                # Forzar división por líneas
                print(f"⚠️ WARNING: Chunk de {chunk_tokens} tokens excede límite. Forzando división...")
                forced_sub_chunks = self._force_split_chunk(chunk, count_tokens_fn)
                final_chunks.extend(forced_sub_chunks)
            else:
                final_chunks.append(chunk)

        return final_chunks

    def _create_chunk(
        self,
        section: SemanticSection,
        content: str,
        sub_index: Optional[int] = None
    ) -> Dict:
        """
        Crea un chunk con metadata semántica

        Args:
            section: Sección semántica
            content: Contenido del chunk
            sub_index: Índice de sub-chunk si aplica

        Returns:
            Diccionario con chunk y metadata
        """
        # Crear header contextual
        header_parts = [
            f"DOCUMENTO: Contrato",
            f"SECCIÓN: {section.tipo}",
        ]

        if section.numero:
            if section.tipo == 'CLAUSULA':
                header_parts.append(f"CLÁUSULA: {section.numero}")
            elif section.tipo == 'ANEXO':
                header_parts.append(f"ANEXO: {section.numero}")

        header_parts.append(f"NOMBRE: {section.nombre}")
        header_parts.append(f"PÁGINAS: {section.pagina_inicio}-{section.pagina_fin}")

        if sub_index is not None:
            header_parts.append(f"PARTE: {sub_index + 1}")

        header = '\n'.join(header_parts)
        full_content = f"{header}\n\n{content}"

        return {
            'text': full_content,
            'seccion_tipo': section.tipo,
            'seccion_nombre': section.nombre,
            'numero_clausula': section.numero,
            'pagina_inicio': section.pagina_inicio,
            'pagina_fin': section.pagina_fin,
        }

    def _split_large_section(
        self,
        section: SemanticSection,
        content: str,
        count_tokens_fn
    ) -> List[Dict]:
        """
        Divide una sección grande en sub-chunks preservando el contexto

        Args:
            section: Sección a dividir
            content: Contenido completo
            count_tokens_fn: Función para contar tokens

        Returns:
            Lista de sub-chunks
        """
        # Dividir por párrafos
        paragraphs = content.split('\n\n')
        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = count_tokens_fn(para)

            # Si agregar este párrafo excede el límite
            if current_tokens + para_tokens > self.max_chunk_size and current_chunk:
                # Guardar chunk actual
                chunk_content = '\n\n'.join(current_chunk)
                chunk = self._create_chunk(section, chunk_content, len(chunks))
                chunks.append(chunk)

                # Iniciar nuevo chunk (con overlap del último párrafo)
                current_chunk = [current_chunk[-1], para] if current_chunk else [para]
                current_tokens = count_tokens_fn('\n\n'.join(current_chunk))
            else:
                # Agregar párrafo al chunk actual
                current_chunk.append(para)
                current_tokens += para_tokens

        # Agregar último chunk
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            chunk = self._create_chunk(section, chunk_content, len(chunks))
            chunks.append(chunk)

        return chunks

    def _force_split_chunk(
        self,
        chunk: Dict,
        count_tokens_fn
    ) -> List[Dict]:
        """
        Divide forzosamente un chunk que excede el límite de tokens

        Args:
            chunk: Chunk a dividir
            count_tokens_fn: Función para contar tokens

        Returns:
            Lista de sub-chunks
        """
        text = chunk['text']
        lines = text.split('\n')

        # Separar header del contenido
        header_lines = []
        content_lines = []
        in_header = True

        for line in lines:
            if in_header and (line.startswith('DOCUMENTO:') or
                            line.startswith('SECCIÓN:') or
                            line.startswith('CLÁUSULA:') or
                            line.startswith('NOMBRE:') or
                            line.startswith('PÁGINAS:') or
                            line.startswith('PARTE:') or
                            line.strip() == ''):
                header_lines.append(line)
            else:
                in_header = False
                content_lines.append(line)

        header = '\n'.join(header_lines)
        header_tokens = count_tokens_fn(header)

        # Dividir contenido en chunks que quepan
        sub_chunks = []
        current_lines = []
        current_tokens = header_tokens

        for line in content_lines:
            line_tokens = count_tokens_fn(line)

            if current_tokens + line_tokens > self.max_chunk_size and current_lines:
                # Guardar chunk actual
                chunk_content = '\n'.join(current_lines)
                full_text = f"{header}\n\n{chunk_content}"

                new_chunk = chunk.copy()
                new_chunk['text'] = full_text
                sub_chunks.append(new_chunk)

                # Reiniciar
                current_lines = [line]
                current_tokens = header_tokens + line_tokens
            else:
                current_lines.append(line)
                current_tokens += line_tokens

        # Agregar último chunk
        if current_lines:
            chunk_content = '\n'.join(current_lines)
            full_text = f"{header}\n\n{chunk_content}"

            new_chunk = chunk.copy()
            new_chunk['text'] = full_text
            sub_chunks.append(new_chunk)

        return sub_chunks if sub_chunks else [chunk]


def chunk_text_semantic(
    text: str,
    count_tokens_fn,
    max_chunk_size: int = 1024,
    min_chunk_size: int = 256
) -> List[Dict]:
    """
    Función principal para chunking semántico

    Args:
        text: Texto completo del documento con marcadores [Page N]
        count_tokens_fn: Función para contar tokens
        max_chunk_size: Tamaño máximo del chunk
        min_chunk_size: Tamaño mínimo del chunk

    Returns:
        Lista de chunks con metadata semántica
    """
    chunker = SemanticChunker(max_chunk_size, min_chunk_size)

    # Extraer secciones
    sections = chunker.extract_sections(text)

    # Crear chunks
    chunks = chunker.chunk_by_sections(sections, count_tokens_fn)

    return chunks
