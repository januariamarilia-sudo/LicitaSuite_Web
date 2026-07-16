from dataclasses import dataclass, field
import re

from licitasuite.core.zip_loader import ZipLoader
from licitasuite.core.file_detector import FileDetector
from licitasuite.models.item_apendice import ItemApendice
from licitasuite.parsers.appendix_parser import AppendixParser
from licitasuite.parsers.pdf_winners_parser import PdfWinnersParser
from licitasuite.engine.cross_checker import CrossChecker
from licitasuite.generators.docx_engine.copy_model_generator import CopyModelAtaGenerator
from licitasuite.generators.docx_engine.formatacao_homologada import aplicar_em_lote, recriar_zip
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
            if getattr(detected, "apendice_embutido", False):
                messages.append(f"Apêndice usado: {detected.apendice} (tabela dentro do modelo da ata)")
            else:
                messages.append(f"Apêndice usado: {detected.apendice}")
            messages.append(f"PDF usado: {detected.vencedores_pdf}")

            if detected.banco_fornecedores:
                messages.append(f"Banco de fornecedores usado: {detected.banco_fornecedores}")
            else:
                messages.append("Banco de fornecedores: não enviado")

            fornecedores = PdfWinnersParser().parse(detected.vencedores_pdf)

            if getattr(detected, "apendice_embutido", False):
                apendice = self._build_virtual_appendix_from_winners(fornecedores)
                messages.append(
                    "Apêndice separado não enviado: itens oficiais montados a partir do PDF de vencedores."
                )
            else:
                appendix_parser = AppendixParser()
                apendice = appendix_parser.parse(detected.apendice)
                messages.extend(appendix_parser.diagnostics)

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

            # LICITASUITE 3.2 LTS
            # Não interrompe toda a geração por causa de uma pendência isolada.
            # A pendência fica registrada no relatório e nas mensagens.
            if hard_errors:
                messages.append("Pendências identificadas, mas a geração continuará com as atas possíveis:")
                for err in hard_errors:
                    messages.append("PENDÊNCIA: " + str(err))

            gen = CopyModelAtaGenerator(detected.modelo_ata)
            files, zip_final = gen.generate_all(result["atas"])
            aplicar_em_lote(files, result["atas"], detected.banco_fornecedores)
            recriar_zip(files, zip_final)

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

    def _build_virtual_appendix_from_winners(self, fornecedores):
        itens = []
        seen = set()
        for fornecedor in fornecedores:
            for item in fornecedor.itens:
                if item.numero_item in seen:
                    continue
                seen.add(item.numero_item)
                descricao = self._winner_description(item)
                quantidade = item.quantidade_pdf or 0
                itens.append(ItemApendice(
                    numero_item=item.numero_item,
                    codigo_siplan="",
                    descricao=descricao,
                    apresentacao="",
                    total=quantidade,
                    cells_text=[
                        "",
                        str(item.numero_item),
                        descricao,
                        "",
                        str(int(quantidade)) if float(quantidade or 0).is_integer() else str(quantidade),
                    ],
                ))
        return itens

    def _winner_description(self, item):
        text = str(getattr(item, "linha_origem", "") or "").strip()
        text = text.split("|", 1)[0].strip()
        text = re.sub(r"^\d+\s+", "", text)
        qty_money = re.search(r"\s+\d{1,3}(?:\.\d{3})*\s*[A-ZÇ]{0,8}\s+R\$", text, flags=re.I)
        if qty_money:
            text = text[:qty_money.start()].strip()
        else:
            text = re.split(r"\s+R\$", text, maxsplit=1)[0].strip()
        return text or getattr(item, "marca", "") or f"Item {item.numero_item}"
