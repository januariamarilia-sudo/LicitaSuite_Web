from dataclasses import dataclass, field
from licitasuite.core.zip_loader import ZipLoader
from licitasuite.core.file_detector import FileDetector
from licitasuite.parsers.appendix_parser import AppendixParser
from licitasuite.parsers.pdf_parser import PdfWinnersParser
from licitasuite.engine.cross_checker import CrossChecker
from licitasuite.reports.conference_report import ConferenceReport
from licitasuite.generators.docx_engine.model_based_generator import ModelBasedAtaGenerator

@dataclass
class PipelineResult:
    ok: bool
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

class Pipeline:
    def run(self, zip_path):
        return self.run_initial_scan(zip_path)

    def execute(self, zip_path):
        return self.run_initial_scan(zip_path)

    def process(self, zip_path):
        return self.run_initial_scan(zip_path)

    def run_initial_scan(self, zip_path):
        messages = []
        errors = []
        try:
            folder = ZipLoader(zip_path).extract()
            messages.append(f"ZIP extraído em: {folder}")

            detected = FileDetector(folder).detect()
            messages.append(f"Modelo da Ata: {detected.modelo_ata}")
            messages.append(f"Apêndice: {detected.apendice}")
            messages.append(f"PDF dos vencedores: {detected.vencedores_pdf}")

            faltando = detected.missing()
            if faltando:
                errors.append("Arquivos obrigatórios não localizados: " + ", ".join(faltando))
                return PipelineResult(ok=False, messages=messages, errors=errors)

            itens_apendice = AppendixParser().parse(detected.apendice)
            messages.append(f"Itens do Apêndice: {len(itens_apendice)}")

            pdf_result = PdfWinnersParser().parse(detected.vencedores_pdf)
            fornecedores = pdf_result.fornecedores
            messages.append(f"Fornecedores reais identificados no PDF: {len(fornecedores)}")

            cross_result = CrossChecker().build_atas(itens_apendice, fornecedores)

            if cross_result["inconsistencias_gerais"]:
                errors.extend(cross_result["inconsistencias_gerais"])

            report = ConferenceReport()
            txt_path = report.write(cross_result)
            json_path = report.write_json(cross_result)

            messages.append("")
            messages.append("CONFERÊNCIA POR FORNECEDOR:")
            for ata in cross_result["atas"]:
                itens = ", ".join(str(item.numero_item) for item in ata.itens) or "nenhum"
                total = ("R$ " + f"{ata.valor_total:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")
                messages.append(f"- {ata.fornecedor_nome} | Itens: {len(ata.itens)} ({itens}) | Total: {total}")

            if errors:
                messages.append("Geração interrompida por inconsistências relevantes.")
                return PipelineResult(ok=False, messages=messages, errors=errors)

            generator = ModelBasedAtaGenerator(detected.modelo_ata)
            generated_files, final_zip = generator.generate_all(cross_result["atas"])

            messages.append("")
            messages.append("Atas DOCX geradas:")
            for path in generated_files:
                messages.append(f"- {path}")
            messages.append(f"ZIP final gerado em: {final_zip}")

            if cross_result["itens_sem_vencedor"]:
                messages.append("Itens do Apêndice sem vencedor identificado: " + ", ".join(map(str, cross_result["itens_sem_vencedor"])))

            messages.append(f"Relatório de conferência salvo em: {txt_path}")
            messages.append(f"Dados para atas salvos em: {json_path}")
            messages.append("LicitaSuite Web 2.0 – Correção PL 53 concluída.")

            return PipelineResult(ok=True, messages=messages)

        except Exception as exc:
            return PipelineResult(ok=False, messages=messages, errors=[str(exc)])
