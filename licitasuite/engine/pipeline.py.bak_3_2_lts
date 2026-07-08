from dataclasses import dataclass, field

from licitasuite.core.zip_loader import ZipLoader
from licitasuite.core.file_detector import FileDetector
from licitasuite.parsers.appendix_parser import AppendixParser
from licitasuite.parsers.pdf_winners_parser import PdfWinnersParser
from licitasuite.engine.cross_checker import CrossChecker
from licitasuite.generators.docx_engine.copy_model_generator import CopyModelAtaGenerator
from licitasuite.reports.conference_report import ConferenceReport
from licitasuite.core.supplier_database import SupplierDatabase

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
            messages.append(f"ZIP extraído: {folder}")

            detected = FileDetector(folder).detect()
            if detected.missing():
                return PipelineResult(False, messages, ["Arquivos obrigatórios ausentes: " + ", ".join(detected.missing())])

            messages.append(f"Modelo usado: {detected.modelo_ata}")
            messages.append(f"Apêndice usado: {detected.apendice}")
            messages.append(f"PDF usado: {detected.vencedores_pdf}")

            if detected.banco_fornecedores:
                messages.append(f"Banco de fornecedores usado: {detected.banco_fornecedores}")
            else:
                messages.append("Banco de fornecedores: não enviado")

            apendice = AppendixParser().parse(detected.apendice)
            fornecedores = PdfWinnersParser().parse(detected.vencedores_pdf)
            messages.append(f"Itens no Apêndice: {len(apendice)}")
            messages.append(f"Fornecedores reais identificados: {len(fornecedores)}")

            result = CrossChecker().build(apendice, fornecedores)

            supplier_db = SupplierDatabase(detected.banco_fornecedores) if detected.banco_fornecedores else SupplierDatabase.empty()
            for ata in result["atas"]:
                supplier_db.enrich_ata(ata)

            if supplier_db.warnings:
                result.setdefault("inconsistencias", [])
                result["inconsistencias"].extend(supplier_db.warnings)
                messages.append("Observações do banco de fornecedores:")
                for warning in supplier_db.warnings:
                    messages.append("- " + warning)

            report = ConferenceReport()
            report_txt = report.write(result)
            report_json = report.write_json(result)

            hard_errors = [
                e for e in result.get("inconsistencias", [])
                if not str(e).startswith("DUPLICIDADE NO BANCO")
                and not str(e).startswith("Há mais de um fornecedor")
            ]
            if hard_errors:
                return PipelineResult(False, messages, hard_errors)

            gen = CopyModelAtaGenerator(detected.modelo_ata)
            files, zip_final = gen.generate_all(result["atas"])

            for ata in result["atas"]:
                messages.append(f"- {ata.fornecedor_nome}: {len(ata.itens)} item(ns)")

            messages.append(f"Atas geradas: {len(files)}")
            messages.append(f"ZIP final: {zip_final}")
            messages.append(f"Relatório: {report_txt}")
            messages.append(f"Relatório JSON: {report_json}")
            messages.append("LicitaSuite Web 3.1.3 LTS concluído.")
            return PipelineResult(True, messages, [])

        except Exception as exc:
            return PipelineResult(False, messages, [str(exc)])
