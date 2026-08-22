from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from apps.documents.services.extractors import (
    DocumentExtractionError,
    extract_text,
)
from apps.documents.services.processor import (
    normalize_text,
    process_document,
)


class DocumentExtractionTests(SimpleTestCase):

    def test_extract_txt_file(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"

            file_path.write_text(
                "KnowledgeOS test document.\n\n"
                "This is enterprise knowledge.",
                encoding="utf-8",
            )

            text = extract_text(str(file_path))

            self.assertIn(
                "KnowledgeOS test document.",
                text,
            )

    def test_normalize_text(self):
        text = (
            "KnowledgeOS   test\r\n"
            "\r\n\r\n"
            "document."
        )

        result = normalize_text(text)

        self.assertEqual(
            result,
            "KnowledgeOS test\n\ndocument.",
        )

    def test_unsupported_file_type(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.exe"

            file_path.write_bytes(b"binary")

            with self.assertRaises(
                DocumentExtractionError
            ):
                extract_text(str(file_path))

    def test_process_document(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.md"

            file_path.write_text(
                "# KnowledgeOS\n\n"
                "Enterprise AI knowledge platform.",
                encoding="utf-8",
            )

            text = process_document(
                str(file_path)
            )

            self.assertEqual(
                text,
                "# KnowledgeOS\n\n"
                "Enterprise AI knowledge platform.",
            )
