from pathlib import Path
import fitz

output = Path(__file__).with_name("smoke_document.pdf")
document = fitz.open()
page = document.new_page()
page.insert_text((72, 72), "DocChat smoke test document")
page.insert_textbox(
    fitz.Rect(72, 110, 520, 220),
    "The DocChat project uses OpenAI text-embedding-3-small for 1536-dimensional embeddings. "
    "The answer model is gpt-4o-mini. This document exists only for a local integration smoke test.",
)
document.save(output)
document.close()
print(output)
