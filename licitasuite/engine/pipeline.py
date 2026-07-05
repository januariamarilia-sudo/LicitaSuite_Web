from dataclasses import dataclass, field
from licitasuite.core.paths import AppPaths
from licitasuite.core.zip_loader import ZipLoader
from licitasuite.core.file_detector import FileDetector
from licitasuite.parsers.appendix_parser import AppendixParser
from licitasuite.parsers.pdf_parser import PdfWinnersParser
from licitasuite.parsers.supplier_registry_parser import SupplierRegistryParser
from licitasuite.engine.supplier_enricher import SupplierEnricher
from licitasuite.engine.cross_checker import CrossChecker
from licitasuite.validation.engine import ValidationEngine
from licitasuite.reports.conference_report import ConferenceReport
from licitasuite.generators.docx_engine.ata_generator import AtaGenerator

@dataclass
class PipelineResult:
    ok: bool
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

class Pipeline:
    def run(self, zip_path):
        paths = AppPaths()
        paths.ensure()
        messages = []
        errors = []

        try:
            folder = ZipLoader(zip_path, paths.temp).extract()
            messages.append(f"ZIP extraído em: {folder}")

            detected = FileDetector(folder).detect()
            messages.append(f"Modelo da Ata: {detected.modelo_ata}")
            messages.append(f"Apêndice: {detected.apendice}")
            messages.append(f"PDF dos vencedores: {detected.vencedores_pdf}")
            messages.append(f"Cadastro fornecedores: {detected.cadastro_fornecedores}")

            missing = detected.missing()
            if missing:
                return PipelineResult(False, messages, ["Arquivos obrigatórios não localizados: " + ", ".join(missing)])

            apendice = AppendixParser().parse(detected.apendice)
            messages.append(f"Itens do Apêndice: {len(apendice)}")

            pdf_result = PdfWinnersParser().parse(detected.vencedores_pdf)
            fornecedores = pdf_result.fornecedores
            messages.append(f"Fornecedores identificados no PDF: {len(fornecedores)}")
            messages.append(f"Linhas prováveis de itens no PDF: {len(pdf_result.item_lines)}")

            registry = SupplierRegistryParser().parse(detected.cadastro_fornecedores)
            if registry:
                fornecedores = SupplierEnricher().enrich(fornecedores, registry)
                messages.append(f"Cadastro de fornecedores aplicado: {len(registry)} registro(s)")
            else:
                messages.append("Cadastro de fornecedores não informado ou não localizado.")

            cross = CrossChecker().build_atas(apendice, fornecedores)
            validation = ValidationEngine().validate(cross)

            report = ConferenceReport()
            report_txt = report.write(cross, validation)
            report_json = report.write_json(cross, validation)

            generator = AtaGenerator(detected.modelo_ata, paths.atas)
            generated, zip_final = generator.generate_all(cross["atas"])

            messages.append("")
            messages.append("CONFERÊNCIA POR FORNECEDOR:")
            for ata in cross["atas"]:
                itens = ", ".join(str(item.numero_item) for item in ata.itens) or "nenhum"
                messages.append(f"- {ata.fornecedor_nome} | Itens: {len(ata.itens)} ({itens})")

            messages.append("")
            messages.append(f"Validação: {'OK' if validation.ok else 'COM ERROS'}")
            for err in validation.errors:
                messages.append(f"ERRO DE VALIDAÇÃO: {err}")
            for warn in validation.warnings:
                messages.append(f"ALERTA: {warn}")

            messages.append("")
            messages.append(f"Atas geradas: {len(generated)}")
            for file in generated:
                messages.append(f"- {file}")

            messages.append(f"ZIP final: {zip_final}")
            messages.append(f"Relatório: {report_txt}")
            messages.append(f"JSON: {report_json}")
            messages.append("Processo concluído.")

            return PipelineResult(True, messages, [])

        except Exception as exc:
            return PipelineResult(False, messages, [str(exc)])
