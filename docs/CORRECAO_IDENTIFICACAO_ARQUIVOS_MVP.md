# Correção MVP — Identificação automática dos arquivos

Esta correção substitui apenas:

`licitasuite/core/file_detector.py`

Ela evita que o LicitaSuite dependa do nome exato do arquivo da ata.

Exemplo aceito:

`ATA DE REGISTRO DE PREÇOS PL 48.2026 PE 37.2026 - ACACIA.DOCX.docx`

Desde que o conteúdo do arquivo seja uma Ata, ele será identificado como modelo.
