import pytest
from app.services.pdf_processor import chunk_text, validate_pdf


def test_validate_pdf_checks_extension_signature_and_size():
    validate_pdf("report.pdf", b"%PDF-1.7 example", 100)
    with pytest.raises(ValueError): validate_pdf("report.txt", b"%PDF-1.7", 100)
    with pytest.raises(ValueError): validate_pdf("report.pdf", b"not pdf", 100)
    with pytest.raises(ValueError): validate_pdf("report.pdf", b"%PDF-1.7" * 20, 10)


def test_chunk_text_keeps_page_and_chunk_metadata():
    chunks = chunk_text(["abcdefghij"], chunk_size=6, overlap=2)
    assert [(c["text"], c["page_number"], c["chunk_index"]) for c in chunks] == [
        ("abcdef", 1, 0), ("efghij", 1, 1)
    ]
