from portal.process_store import (
    create_process,
    process_metrics,
    record_generation,
    search_processes,
    update_technical_qualification,
    update_process_status,
)


def test_process_lifecycle_and_metrics():
    process = create_process(
        "PL 10/2026",
        "Pregão Eletrônico",
        "Aquisição de materiais",
        "Januária",
        technical_qualification="AFE da ANVISA e licença sanitária.",
    )

    assert process["status"] == "Em criação"
    assert search_processes([process], "materiais") == [process]
    assert search_processes([process], "anvisa") == [process]

    update_technical_qualification(
        process,
        "AFE da ANVISA, licença sanitária e atestado de capacidade técnica.",
    )
    assert "atestado" in process["technical_qualification"]
    assert process["history"][-1]["title"] == "Qualificação técnica atualizada"

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
