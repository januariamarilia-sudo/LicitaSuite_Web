from pathlib import Path
from docx import Document

class DetectedFiles:
    def __init__(self, modelo_ata=None, apendice=None, vencedores_pdf=None):
        self.modelo_ata = modelo_ata
        self.apendice = apendice
        self.vencedores_pdf = vencedores_pdf

    def missing(self):
        missing = []
        if not self.modelo_ata:
            missing.append("modelo da ata")
        if not self.apendice:
            missing.append("apêndice")
        if not self.vencedores_pdf:
            missing.append("PDF dos vencedores")
        return missing

class FileDetector:
    def __init__(self, folder):
        self.folder = Path(folder)

    def detect(self):
        docs = list(self.folder.rglob("*.docx"))
        pdfs = list(self.folder.rglob("*.pdf"))

        apendice = None
        modelo = None

        for docx in docs:
            name = docx.name.lower()
            if "apendice" in name or "apêndice" in name:
                apendice = docx
                continue
            try:
                doc = Document(docx)
                text = "\n".join(p.text for p in doc.paragraphs[:30]).upper()
                table_text = " ".join(cell.text for t in doc.tables[:1] for r in t.rows[:2] for cell in r.cells).upper() if doc.tables else ""
                if "APÊNDICE" in text or "APENDICE" in text or ("CÓD" in table_text and "MUNIC" in table_text):
                    apendice = docx
                elif "ATA DE REGISTRO DE PREÇOS" in text or "PROCESSO LICITATÓRIO" in text:
                    modelo = docx
            except Exception:
                pass

        if not modelo:
            for docx in docs:
                if docx != apendice:
                    modelo = docx
                    break

        vencedores = None
        for pdf in pdfs:
            if "vencedor" in pdf.name.lower():
                vencedores = pdf
                break
        if not vencedores and pdfs:
            vencedores = pdfs[0]

        return DetectedFiles(modelo, apendice, vencedores)
