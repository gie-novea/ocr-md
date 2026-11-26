# Ticket à déposer sur le dépôt PyMuPDF4LLM

Texte préparé pour le dépôt https://github.com/pymupdf/pymupdf4llm (section « Issues »). Le corps du ticket est en anglais, langue du dépôt. L'exemple a été vérifié le 26/11/2026 avec PyMuPDF et PyMuPDF4LLM 1.28.2, Python 3.12, Windows 11 ; il reproduit le défaut corrigé par `src/ocr_md/correctifs.py`.

Une seconde particularité pourrait faire l'objet d'un ticket distinct, si vous le souhaitez : une page scannée qui porte aussi un peu de texte visible (mention de dépôt d'une plateforme) n'est plus reconnue comme page OCR, et le calque invisible est absorbé par la zone d'image (voir `docs/avancement.md`, jalon 6).

---

**Titre** : Words are concatenated in table cells of OCR'd pages (spaces lost in `extract_cells(..., markdown=True)`)

**Description**

On a scanned page carrying an invisible OCR text layer (render mode 3), where the OCR tool writes one text object per word, each followed by a real space character and horizontally scaled to its OCR box (common practice), `to_markdown()` returns table cells with the words glued together: `AnnaSmith` instead of `Anna Smith`. `page.get_text()` returns the spaces correctly.

**Minimal reproducible example**

```python
import pymupdf
import pymupdf4llm

rows = [["Name", "Role", "Days"], ["Anna Smith", "Lead architect", "42"], ["John Doe", "Fluid engineer", "18"]]
X0, Y0, W, H, SIZE = 72, 100, 150, 24, 11

# 1. A "scanned" page: an image of a ruled table.
src = pymupdf.open()
p = src.new_page()
for i in range(len(rows) + 1):
    p.draw_line((X0, Y0 + i * H), (X0 + 3 * W, Y0 + i * H))
for j in range(4):
    p.draw_line((X0 + j * W, Y0), (X0 + j * W, Y0 + len(rows) * H))
positions = []
for i, row in enumerate(rows):
    for j, cell in enumerate(row):
        x = X0 + j * W + 4
        words = cell.split()
        for k, word in enumerate(words):
            p.insert_text((x, Y0 + i * H + 16), word, fontsize=SIZE)
            positions.append((x, Y0 + i * H + 16, word + (" " if k < len(words) - 1 else "")))
            x += pymupdf.get_text_length(word + " ", fontsize=SIZE)
pix = p.get_pixmap(dpi=200)

# 2. The OCR'd page: the image plus an invisible text layer, one text object per word,
#    each word followed by a real space and stretched to its OCR box.
doc = pymupdf.open()
page = doc.new_page()
page.insert_image(page.rect, pixmap=pix)
for n, (x, y, text) in enumerate(positions):
    stretch = pymupdf.Matrix(1.0 + 0.01 * (n % 3), 1)
    page.insert_text((x, y), text, fontsize=SIZE, render_mode=3, morph=(pymupdf.Point(x, y), stretch))

print(repr(page.get_text()))
print(pymupdf4llm.to_markdown(doc, use_ocr=False))
```

**Actual output**

```
|Name|Role|Days|
|---|---|---|
|AnnaSmith|Leadarchitect|42|
|JohnDoe|Fluidengineer|18|
```

**Expected output**

```
|Name|Role|Days|
|---|---|---|
|Anna Smith|Lead architect|42|
|John Doe|Fluid engineer|18|
```

**Analysis**

In `pymupdf4llm/helpers/utils.py`, `extract_cells(table_blocks, cell, markdown=True, ...)` builds the cell text span by span. In Markdown mode each span is stripped (`span_text.rstrip()` when longer than 2 characters, then `prefix + span_text.strip() + suffix`) before being appended, without inserting a separator. When every word is its own span (one text object per word, which happens as soon as consecutive words have different transformation matrices), the separating spaces are lost. With `markdown=False`, the spaces are preserved. Without the per-word horizontal scaling, MuPDF merges the words into one span and the problem does not show.

**Possible fix**

When joining stripped spans in Markdown mode, insert a single space between two consecutive spans of the same line if the previous span ended with whitespace (or if the horizontal gap between them is larger than a fraction of the font size), as is done for plain text extraction.

**Environment**

PyMuPDF 1.28.2, pymupdf4llm 1.28.2, pymupdf-layout 1.28.2, Python 3.12, Windows 11.
