from pathlib import Path

class AppPaths:
    def __init__(self, root="."):
        self.root = Path(root)
        self.temp = self.root / "temp"
        self.output = self.root / "output"
        self.atas = self.output / "atas_geradas"
        self.logs = self.root / "logs"

    def ensure(self):
        self.temp.mkdir(parents=True, exist_ok=True)
        self.output.mkdir(parents=True, exist_ok=True)
        self.atas.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
