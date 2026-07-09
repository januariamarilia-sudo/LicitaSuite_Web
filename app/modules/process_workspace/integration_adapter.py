class AtaEngineAdapter:
    """
    Adaptador de integração com o motor homologado:
    LicitaSuite Web 4.0 LTS — Build Homologada v2.2

    Regra: este arquivo NÃO altera o motor de atas.
    Apenas recebe os resultados produzidos por ele.
    """

    def __init__(self, ata_engine):
        self.ata_engine = ata_engine

    def run_generation(self, process_payload: dict) -> dict:
        """
        Espera-se que o motor homologado retorne:
        - suppliers_count
        - items_count
        - atas_count
        - total_value
        - divergences_count
        - artifact_path
        """
        return self.ata_engine.generate(process_payload)
