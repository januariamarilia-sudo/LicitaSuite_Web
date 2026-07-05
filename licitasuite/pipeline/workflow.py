from dataclasses import dataclass

@dataclass
class WorkflowStatus:
    stage:str=""
    success:bool=False

class Workflow:
    STEPS=[
        "Selecionar ZIP",
        "Detectar arquivos",
        "Ler Apêndice",
        "Ler PDF",
        "Ler cadastro",
        "Validar",
        "Gerar Atas",
        "Gerar relatórios",
        "Compactar ZIP"
    ]

    def run(self):
        history=[]
        for step in self.STEPS:
            history.append(WorkflowStatus(stage=step, success=True))
        return history
