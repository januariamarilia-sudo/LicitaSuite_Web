from pathlib import Path
import shutil


APP = Path("web/app.py")


def main():
    if not APP.exists():
        print("ERRO: não encontrei web/app.py")
        return

    text = APP.read_text(encoding="utf-8")
    backup = APP.with_suffix(".py.bak_3_3_conferencia")

    if not backup.exists():
        shutil.copy2(APP, backup)
        print(f"Backup criado: {backup}")

    import_block = """from validador_conferencia import (
    build_conferencia,
    write_conferencia_xlsx,
    add_conferencia_to_zip,
    format_conferencia_markdown,
)
"""

    if "from validador_conferencia import" not in text:
        marker = "import streamlit as st\n"
        if marker in text:
            text = text.replace(marker, marker + "\n" + import_block)
        else:
            print("ERRO: não encontrei import streamlit as st")
            return

    marker = """                    progress.progress(100)

                    st.success(f"{len(files)} ata(s) gerada(s).")
"""
    insert = """                    try:
                        conferencia = build_conferencia(zip_path, OUTPUT_DIR, files)
                        conferencia_file = write_conferencia_xlsx(conferencia, OUTPUT_DIR)
                        add_conferencia_to_zip(zip_final, conferencia_file)
                        st.markdown(format_conferencia_markdown(conferencia))
                    except Exception as conferencia_exc:
                        st.warning(f"Atas geradas. A conferência automática não foi concluída: {conferencia_exc}")

                    progress.progress(100)

                    st.success(f"{len(files)} ata(s) gerada(s).")
"""

    if "build_conferencia(zip_path, OUTPUT_DIR, files)" in text:
        print("Conferência automática já estava inserida no app.py")
    elif marker in text:
        text = text.replace(marker, insert)
    else:
        print("ERRO: não encontrei o bloco de progress.progress(100) para inserir a conferência.")
        print("Envie o trecho do app.py da parte do download.")
        return

    APP.write_text(text, encoding="utf-8")
    print("PATCH APLICADO COM SUCESSO.")
    print("Agora rode:")
    print("git add web/app.py web/validador_conferencia.py docs/LICITASUITE_WEB_3_3_CONFERENCIA_AUTOMATICA.md aplicar_patch_conferencia_3_3.py")
    print('git commit -m "Adiciona conferencia automatica"')
    print("git push")


if __name__ == "__main__":
    main()
