class TableWriter:
    """
    Escreve valores em células preservando a estrutura básica.
    """

    def write_cell(self, cell, value):
        text = "" if value is None else str(value)

        if cell.paragraphs:
            paragraph = cell.paragraphs[0]
            if paragraph.runs:
                paragraph.runs[0].text = text
                for run in paragraph.runs[1:]:
                    run.text = ""
            else:
                paragraph.add_run(text)

            for extra in cell.paragraphs[1:]:
                for run in extra.runs:
                    run.text = ""
        else:
            cell.text = text

    def write_row(self, row, values):
        for index, value in enumerate(values):
            if index < len(row.cells):
                self.write_cell(row.cells[index], value)
