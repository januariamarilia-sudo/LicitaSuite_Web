def paragraph_text(paragraph):
    return "".join(run.text for run in paragraph.runs)

def replace_in_paragraph(paragraph, replacements):
    """
    Substitui textos em um parágrafo tentando preservar a formatação.
    Se o placeholder estiver dividido em vários runs, consolida no primeiro run.
    """
    changed = 0

    for run in paragraph.runs:
        original = run.text
        updated = original
        for old, new in replacements.items():
            updated = updated.replace(old, str(new))
        if updated != original:
            run.text = updated
            changed += 1

    full = paragraph_text(paragraph)
    updated_full = full

    for old, new in replacements.items():
        updated_full = updated_full.replace(old, str(new))

    if updated_full != full and paragraph.runs:
        paragraph.runs[0].text = updated_full
        for run in paragraph.runs[1:]:
            run.text = ""
        changed += 1

    return changed
