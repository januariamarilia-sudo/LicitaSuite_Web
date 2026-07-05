class PlaceholderReplacer:
    def replace_document(self, document, mapping):
        count = 0

        for paragraph in document.paragraphs:
            count += self._replace_paragraph(paragraph, mapping)

        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        count += self._replace_paragraph(paragraph, mapping)

        for section in document.sections:
            for paragraph in section.header.paragraphs:
                count += self._replace_paragraph(paragraph, mapping)
            for paragraph in section.footer.paragraphs:
                count += self._replace_paragraph(paragraph, mapping)

        return count

    def _replace_paragraph(self, paragraph, mapping):
        changed = 0

        for run in paragraph.runs:
            original = run.text
            updated = original

            for key, value in mapping.items():
                updated = updated.replace(key, str(value))

            if updated != original:
                run.text = updated
                changed += 1

        return changed
