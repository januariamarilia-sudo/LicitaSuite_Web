from pathlib import Path
import shutil
import re


PIPELINE = Path("licitasuite/engine/pipeline.py")


def main():
    if not PIPELINE.exists():
        print("ERRO: não encontrei licitasuite/engine/pipeline.py")
        return

    text = PIPELINE.read_text(encoding="utf-8")
    backup = PIPELINE.with_suffix(".py.bak_3_2_lts")

    if not backup.exists():
        shutil.copy2(PIPELINE, backup)
        print(f"Backup criado: {backup}")

    old = '''            hard_errors = [
                e for e in result.get("inconsistencias", [])
                if not str(e).startswith("DUPLICIDADE NO BANCO")
                and not str(e).startswith("Há mais de um fornecedor")
            ]
            if hard_errors:
                return PipelineResult(False, messages, hard_errors)

            gen = CopyModelAtaGenerator(detected.modelo_ata)
'''

    new = '''            hard_errors = [
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
'''

    if old in text:
        text = text.replace(old, new)
    else:
        print("ATENÇÃO: bloco exato não encontrado. Tentando alternativa.")
        pattern = re.compile(
            r'''            hard_errors = \[
                e for e in result\.get\("inconsistencias", \[\]\)
                if not str\(e\)\.startswith\("DUPLICIDADE NO BANCO"\)
                and not str\(e\)\.startswith\("Há mais de um fornecedor"\)
            \]
            if hard_errors:
                return PipelineResult\(False, messages, hard_errors\)

            gen = CopyModelAtaGenerator\(detected\.modelo_ata\)
''',
            flags=re.M,
        )
        text2 = pattern.sub(new, text)
        if text2 == text:
            print("ERRO: não consegui aplicar o patch automático no pipeline.")
            print("Envie o trecho do pipeline.py entre as linhas 55 e 75.")
            return
        text = text2

    PIPELINE.write_text(text, encoding="utf-8")
    print("PATCH APLICADO COM SUCESSO.")
    print("Agora rode:")
    print("git add licitasuite/parsers/pdf_winners_parser.py licitasuite/engine/pipeline.py aplicar_patch_lts_3_2.py docs/LICITASUITE_WEB_3_2_LTS.md")
    print('git commit -m "LicitaSuite Web 3.2 LTS parser confiavel"')
    print("git push")


if __name__ == "__main__":
    main()
