from typing import List, Dict, Optional
from .models import LicitationProcess


class ProcessWorkspaceService:
    def __init__(self):
        self.processes: Dict[str, LicitationProcess] = {}

    def create_process(self, process_number: str, modality: str, object_description: str) -> LicitationProcess:
        process = LicitationProcess(
            process_number=process_number,
            modality=modality,
            object_description=object_description,
        )
        process.add_event("Processo criado", "Workspace inicial criado.")
        self.processes[process_number] = process
        return process

    def get_process(self, process_number: str) -> Optional[LicitationProcess]:
        return self.processes.get(process_number)

    def list_processes(self) -> List[LicitationProcess]:
        return list(self.processes.values())

    def register_ata_generation_result(
        self,
        process_number: str,
        suppliers_count: int,
        items_count: int,
        atas_count: int,
        total_value: float,
        artifact_path: str,
        divergences_count: int = 0,
    ) -> LicitationProcess:
        process = self.processes[process_number]
        process.suppliers_count = suppliers_count
        process.items_count = items_count
        process.atas_count = atas_count
        process.total_value = total_value
        process.pending_count = divergences_count
        process.status = "Com pendências" if divergences_count else "Atas geradas"
        process.module_status.atas = "amarelo" if divergences_count else "verde"
        process.add_version("Geração de atas", artifact_path)
        process.add_event(
            "Atas processadas",
            f"{atas_count} atas geradas para {suppliers_count} fornecedores.",
        )
        return process

    def search(self, term: str) -> List[LicitationProcess]:
        normalized = term.lower().strip()
        results = []
        for process in self.processes.values():
            searchable = " ".join([
                process.process_number,
                process.modality,
                process.object_description,
                process.status,
                process.observations,
            ]).lower()
            if normalized in searchable:
                results.append(process)
        return results
