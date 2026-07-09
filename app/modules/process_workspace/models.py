from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class TimelineEvent:
    title: str
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProcessFile:
    name: str
    category: str
    path: str
    uploaded_at: datetime = field(default_factory=datetime.now)


@dataclass
class VersionRecord:
    version: int
    label: str
    artifact_path: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ModuleStatus:
    documentos: str = "cinza"
    atas: str = "cinza"
    habilitacao: str = "cinza"
    publicacoes: str = "cinza"
    contratos: str = "cinza"
    relatorios: str = "cinza"


@dataclass
class LicitationProcess:
    process_number: str
    modality: str
    object_description: str
    status: str = "Em criação"
    suppliers_count: int = 0
    items_count: int = 0
    atas_count: int = 0
    contracts_count: int = 0
    publications_count: int = 0
    pending_count: int = 0
    total_value: float = 0.0
    files: List[ProcessFile] = field(default_factory=list)
    timeline: List[TimelineEvent] = field(default_factory=list)
    versions: List[VersionRecord] = field(default_factory=list)
    module_status: ModuleStatus = field(default_factory=ModuleStatus)
    observations: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_event(self, title: str, description: str = "") -> None:
        self.timeline.append(TimelineEvent(title=title, description=description))
        self.updated_at = datetime.now()

    def add_file(self, name: str, category: str, path: str) -> None:
        self.files.append(ProcessFile(name=name, category=category, path=path))
        self.add_event("Arquivo recebido", f"{name} incluído em {category}.")

    def add_version(self, label: str, artifact_path: str) -> None:
        next_version = len(self.versions) + 1
        self.versions.append(VersionRecord(version=next_version, label=label, artifact_path=artifact_path))
        self.add_event("Nova versão gerada", f"Versão {next_version}: {label}")

    def to_dashboard(self) -> Dict:
        return {
            "processo": self.process_number,
            "modalidade": self.modality,
            "objeto": self.object_description,
            "status": self.status,
            "fornecedores": self.suppliers_count,
            "itens": self.items_count,
            "atas": self.atas_count,
            "contratos": self.contracts_count,
            "publicacoes": self.publications_count,
            "pendencias": self.pending_count,
            "valor_total": self.total_value,
        }
