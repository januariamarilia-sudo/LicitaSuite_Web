from portal.process_store import (
    create_process,
    process_metrics,
    record_generation,
    search_processes,
    update_process_status,
)


def test_process_lifecycle_and_metrics():
    process = create_process(
        "PL 10/2026",
        "Pregão Eletrônico",
        "Aquisição de materiais",
        "Januária",
    )

    assert process["status"] == "Em criação"
    assert search_processes([process], "materiais") == [process]

    record_generation(process, atas=3, suppliers=3, items=18, pending=1)
    assert process["status"] == "Com pendências"

    update_process_status(process, "Concluído")
    metrics = process_metrics([process])
    assert metrics == {
        "active": 0,
        "atas": 3,
        "suppliers": 3,
        "pending": 1,
        "completed": 1,
    }
