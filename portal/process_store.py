from __future__ import annotations

from datetime import datetime
from uuid import uuid4


PROCESS_STATUSES = (
    "Em criação",
    "Arquivos recebidos",
    "Em processamento",
    "Atas geradas",
    "Com pendências",
    "Concluído",
    "Arquivado",
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_process(
    number: str,
    modality: str,
    object_description: str,
    responsible: str = "",
    observations: str = "",
) -> dict:
    timestamp = _now()
    return {
        "id": uuid4().hex,
        "number": number.strip(),
        "modality": modality.strip(),
        "object": object_description.strip(),
        "responsible": responsible.strip(),
        "observations": observations.strip(),
        "status": "Em criação",
        "suppliers": 0,
        "items": 0,
        "atas": 0,
        "pending": 0,
        "total_value": 0.0,
        "created_at": timestamp,
        "updated_at": timestamp,
        "history": [
            {
                "title": "Processo criado",
                "description": "Workspace operacional iniciado.",
                "created_at": timestamp,
            }
        ],
    }


def format_timestamp(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y, %H:%M")
    except (TypeError, ValueError):
        return str(value or "-")


def search_processes(processes: list[dict], term: str) -> list[dict]:
    normalized = term.casefold().strip()
    if not normalized:
        return list(processes)

    return [
        process
        for process in processes
        if normalized
        in " ".join(
            [
                process.get("number", ""),
                process.get("modality", ""),
                process.get("object", ""),
                process.get("responsible", ""),
                process.get("status", ""),
            ]
        ).casefold()
    ]


def process_metrics(processes: list[dict]) -> dict:
    active = [
        process
        for process in processes
        if process.get("status") not in {"Concluído", "Arquivado"}
    ]
    return {
        "active": len(active),
        "atas": sum(int(process.get("atas", 0) or 0) for process in processes),
        "suppliers": sum(
            int(process.get("suppliers", 0) or 0) for process in processes
        ),
        "pending": sum(int(process.get("pending", 0) or 0) for process in processes),
        "completed": sum(
            process.get("status") == "Concluído" for process in processes
        ),
    }


def update_process_status(process: dict, status: str) -> None:
    if status not in PROCESS_STATUSES:
        raise ValueError(f"Situação inválida: {status}")
    timestamp = _now()
    process["status"] = status
    process["updated_at"] = timestamp
    process.setdefault("history", []).append(
        {
            "title": "Situação atualizada",
            "description": f"Processo alterado para {status}.",
            "created_at": timestamp,
        }
    )


def record_generation(
    process: dict,
    *,
    atas: int,
    suppliers: int = 0,
    items: int = 0,
    pending: int = 0,
    artifact: str = "atas_geradas.zip",
) -> None:
    timestamp = _now()
    process["atas"] = int(atas or 0)
    process["suppliers"] = int(suppliers or atas or 0)
    process["items"] = int(items or 0)
    process["pending"] = int(pending or 0)
    process["status"] = "Com pendências" if pending else "Atas geradas"
    process["updated_at"] = timestamp
    process.setdefault("history", []).append(
        {
            "title": "Atas processadas",
            "description": (
                f"{process['atas']} ata(s) gerada(s); arquivo {artifact} registrado."
            ),
            "created_at": timestamp,
        }
    )
