from pathlib import Path
import shutil


PIPELINE = Path("licitasuite/engine/pipeline.py")


def main():
    if not PIPELINE.exists():
        print("ERRO: não encontrei licitasuite/engine/pipeline.py")
        return

    text = PIPELINE.read_text(encoding="utf-8")
    original = text

    backup = PIPELINE.with_suffix(".py.bak_4_0_homologada_v2_2")
    if not backup.exists():
        shutil.copy2(PIPELINE, backup)
        print(f"Backup criado: {backup}")

    import_line = "from licitasuite.generators.docx_engine.formatacao_homologada import aplicar_em_lote, recriar_zip\n"
    if import_line not in text:
        marker = "from licitasuite.generators.docx_engine.copy_model_generator import CopyModelAtaGenerator\n"
        if marker in text:
            text = text.replace(marker, marker + import_line)
        else:
            print("ERRO: não encontrei o import do CopyModelAtaGenerator.")
            return

    text = text.replace(
        '            aplicar_em_lote(files, result["atas"])\n',
        '            aplicar_em_lote(files, result["atas"], detected.banco_fornecedores)\n'
    )

    old = '            files, zip_final = gen.generate_all(result["atas"])\n'
    new = '''            files, zip_final = gen.generate_all(result["atas"])
            aplicar_em_lote(files, result["atas"], detected.banco_fornecedores)
            recriar_zip(files, zip_final)
'''

    if 'aplicar_em_lote(files, result["atas"], detected.banco_fornecedores)' not in text:
        if old in text:
            text = text.replace(old, new)
        else:
            print('ERRO: não encontrei a linha files, zip_final = gen.generate_all(result["atas"]).')
            return

    if text != original:
        PIPELINE.write_text(text, encoding="utf-8")
        print("PATCH APLICADO COM SUCESSO.")
    else:
        print("Nenhuma alteração necessária. O patch já estava aplicado.")

    print("Agora rode:")
    print("git add licitasuite docs aplicar_patch_build_homologada_v2_2.py")
    print('git commit -m "Build homologada v2.2 - banco de dados no preambulo"')
    print("git push")


if __name__ == "__main__":
    main()
