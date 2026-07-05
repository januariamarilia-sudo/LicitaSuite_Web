from licitasuite.utils.docx_text import replace_in_paragraph

class DocumentReplacer:
    """
    Substitui placeholders no documento inteiro:
    - corpo;
    - tabelas;
    - cabeçalhos;
    - rodapés.
    """

    def replace(self, document, replacements):
        count = 0

        for paragraph in document.paragraphs:
            count += replace_in_paragraph(paragraph, replacements)

        for table in document.tables:
            count += self._replace_in_table(table, replacements)

        for section in document.sections:
            for paragraph in section.header.paragraphs:
                count += replace_in_paragraph(paragraph, replacements)
            for table in section.header.tables:
                count += self._replace_in_table(table, replacements)

            for paragraph in section.footer.paragraphs:
                count += replace_in_paragraph(paragraph, replacements)
            for table in section.footer.tables:
                count += self._replace_in_table(table, replacements)

        return count

    def _replace_in_table(self, table, replacements):
        count = 0
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    count += replace_in_paragraph(paragraph, replacements)
                for nested in cell.tables:
                    count += self._replace_in_table(nested, replacements)
        return count
