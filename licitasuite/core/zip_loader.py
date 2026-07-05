from pathlib import Path
from zipfile import ZipFile
import shutil
import time

class ZipLoader:
    def __init__(self, zip_path, workdir="temp/processo_atual"):
        self.zip_path = Path(zip_path)
        self.workdir = Path(workdir)

    def extract(self):
        if not self.zip_path.exists():
            raise FileNotFoundError(f"ZIP não localizado: {self.zip_path}")
        if self.workdir.exists():
            shutil.rmtree(self.workdir, ignore_errors=True)
        self.workdir.mkdir(parents=True, exist_ok=True)
        with ZipFile(self.zip_path, "r") as z:
            z.extractall(self.workdir)
        return self.workdir
