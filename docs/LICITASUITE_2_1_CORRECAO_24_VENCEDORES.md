# LicitaSuite 2.1 — Correção do motor para 24 vencedores

Esta correção adiciona um parser robusto para o PDF de vencedores do Portal de Compras Públicas.

Objetivo:
- identificar todos os fornecedores do PDF por `| Tipo:`;
- não depender somente de `TOTAL DO VENCEDOR`;
- evitar perda de fornecedores no começo/fim de página;
- corrigir casos como Acácia, Conquista, Medilar e Zion;
- preservar a montagem das atas existente.

A aplicação é feita pelo script `aplicar_patch_motor_24_vencedores.py`.
