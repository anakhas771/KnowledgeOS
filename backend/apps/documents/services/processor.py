import re

from .extractors import extract_text


def normalize_text(text: str) -> str:
    """
    Normalize extracted document text for downstream processing.
    """

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def process_document(
    file_path: str,
    file_type: str | None = None,
) -> str:
    """
    Extract and normalize document text.
    """

    extracted_text = extract_text(
        file_path=file_path,
        file_type=file_type,
    )

    return normalize_text(extracted_text)
