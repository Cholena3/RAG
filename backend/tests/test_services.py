import pytest
import os
import tempfile
from app.services.document_processor import DocumentProcessor


class TestDocumentProcessor:
    def setup_method(self):
        self.processor = DocumentProcessor()

    def test_extract_txt(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world.\nSecond line.")
        text, pages = self.processor.extract_text(str(f), "txt")
        assert "Hello world" in text
        assert pages is None

    def test_extract_md(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Title\n\nSome content here.")
        text, pages = self.processor.extract_text(str(f), "md")
        assert "Title" in text

    def test_extract_csv(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("name,age\nAlice,30\nBob,25")
        text, pages = self.processor.extract_text(str(f), "csv")
        assert "Alice" in text
        assert "Bob" in text

    def test_unsupported_type(self):
        with pytest.raises(ValueError, match="Unsupported"):
            self.processor.extract_text("fake.xyz", "xyz")

    def test_chunk_text_recursive(self):
        text = "A " * 1000  # long text
        chunks = self.processor.chunk_text(text, strategy="recursive")
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) > 0

    def test_chunk_text_short(self):
        text = "Short text."
        chunks = self.processor.chunk_text(text)
        assert len(chunks) == 1
        assert chunks[0] == "Short text."

    def test_count_tokens(self):
        count = self.processor.count_tokens("Hello world")
        assert count > 0
        assert isinstance(count, int)


class TestRAGEngineRerank:
    def test_bm25_rerank(self):
        from app.services.rag_engine import RAGEngine
        from app.schemas.chat import SourceCitation

        engine = RAGEngine.__new__(RAGEngine)
        citations = [
            SourceCitation(
                document_id="1", document_name="a.pdf",
                page_number=1, chunk_text="python programming language basics",
                relevance_score=0.8,
            ),
            SourceCitation(
                document_id="2", document_name="b.pdf",
                page_number=2, chunk_text="java enterprise development guide",
                relevance_score=0.85,
            ),
            SourceCitation(
                document_id="3", document_name="c.pdf",
                page_number=3, chunk_text="python data science with pandas",
                relevance_score=0.7,
            ),
        ]
        result = engine._bm25_rerank("python programming", citations)
        # Python-related chunks should rank higher after BM25 boost
        assert result[0].chunk_text.startswith("python programming")
        assert len(result) == 3
