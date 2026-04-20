import os
import fitz  # PyMuPDF
from docx import Document as DocxDocument
import pandas as pd
import markdown
from langchain_text_splitters import RecursiveCharacterTextSplitter, TokenTextSplitter
import tiktoken
from app.config import get_settings

settings = get_settings()


class DocumentProcessor:
    """Extracts text from various document types and chunks it."""

    SUPPORTED_TYPES = {"pdf", "docx", "txt", "md", "csv"}

    def extract_text(self, file_path: str, file_type: str) -> tuple[str, int | None]:
        """Returns (text, page_count)."""
        extractors = {
            "pdf": self._extract_pdf,
            "docx": self._extract_docx,
            "txt": self._extract_text_file,
            "md": self._extract_text_file,
            "csv": self._extract_csv,
        }
        extractor = extractors.get(file_type)
        if not extractor:
            raise ValueError(f"Unsupported file type: {file_type}")
        return extractor(file_path)

    def _extract_pdf(self, path: str) -> tuple[str, int]:
        doc = fitz.open(path)
        pages = []
        for page in doc:
            pages.append(page.get_text())
        page_count = len(pages)
        doc.close()
        return "\n\n".join(pages), page_count

    def _extract_docx(self, path: str) -> tuple[str, None]:
        doc = DocxDocument(path)
        text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return text, None

    def _extract_text_file(self, path: str) -> tuple[str, None]:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), None

    def _extract_csv(self, path: str) -> tuple[str, None]:
        df = pd.read_csv(path)
        return df.to_string(index=False), None

    def chunk_text(self, text: str, strategy: str = "recursive") -> list[str]:
        if strategy == "token":
            splitter = TokenTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
        return splitter.split_text(text)

    def count_tokens(self, text: str) -> int:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
