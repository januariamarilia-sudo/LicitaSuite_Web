from pathlib import Path
import zipfile
import time
import uuid
from licitasuite.core.exceptions import ZipValidationError

class ZipLoader:
    def __init__(self, zip_path, temp_root="temp"):
        self.zip_path = Path(zip_path)
        self.temp_root = Path(temp_root)

    def extract(self):
        if not self.zip_path.exists():
            raise ZipValidationError("Arquivo ZIP não localizado.")

        if self.zip_path.suffix.lower() != ".zip":
            raise ZipValidationError("O arquivo selecionado não é um ZIP.")

        if not zipfile.is_zipfile(self.zip_path):
            raise ZipValidationError("ZIP inválido ou corrompido.")

        self.temp_root.mkdir(parents=True, exist_ok=True)
        folder = self.temp_root / ("execucao_" + time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6])
        folder.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(self.zip_path, "r") as z:
            z.extractall(folder)

        return folder
