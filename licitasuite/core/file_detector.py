from dataclasses import dataclass
from pathlib import Path

@dataclass
class DetectedFiles:
    modelo_ata: Path | None = None
    apendice: Path | None = None
    vencedores_pdf: Path | None = None
    cadastro_fornecedores: Path | None = None

    def missing(self):
        faltando = []
        if self.modelo_ata is None:
            faltando.append("Modelo da Ata em DOCX")
        if self.apendice is None:
            faltando.append("Apêndice em DOCX")
        if self.vencedores_pdf is None:
            faltando.append("PDF dos vencedores")
        return faltando

class FileDetector:
    def __init__(self, folder):
        self.folder = Path(folder)

    def detect(self):
        result = DetectedFiles()

        for file in self.folder.rglob("*"):
            if not file.is_file():
                continue

            name = file.name.lower()
            suffix = file.suffix.lower()

            if suffix == ".pdf":
                if "venced" in name or result.vencedores_pdf is None:
                    result.vencedores_pdf = file

            elif suffix == ".docx":
                if "apend" in name or "apênd" in name:
                    result.apendice = file
                elif "ata" in name and result.modelo_ata is None:
                    result.modelo_ata = file
                elif result.modelo_ata is None:
                    result.modelo_ata = file

            elif suffix in [".xlsx", ".xls"]:
                if any(k in name for k in ["fornecedor", "cadastro", "dados"]):
                    result.cadastro_fornecedores = file
                elif result.cadastro_fornecedores is None:
                    result.cadastro_fornecedores = file

        return result
