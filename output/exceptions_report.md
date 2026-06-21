# Relatório de Exceções — Asset Servicing

Total: 8 | Auto-aprovados: 3 | Em revisão: 5


## Resumo do lote

| Doc | Emissor | Evento | Confiança | Desfecho | Motivos |
|-----|---------|--------|-----------|----------|---------|
| 01_energetica_vale_tiete_dividendo | Energética Vale do Tietê S.A. | DIVIDENDO | alta (1.0) | auto | — |
| 02_banco_meridional_jcp | Banco Meridional do Brasil S.A. | JCP | alta (1.0) | auto | — |
| 03_siderurgica_paranaense_proventos | COMPANHIA SIDERÚRGICA PARANENSE S.A. | JCP | alta (0.847) | REVIEW | agent_flagged, golden_partial, title_substance_conflict |
| 04_rede_varejo_jcp_sem_data | REDE VAREJO BRASIL S.A. | JCP | alta (1.0) | REVIEW | agent_flagged, missing_required |
| 05_aurora_saneamento_dividendo_datas | AURORA SANEAMENTO S.A. | DIVIDENDO | media (0.75) | REVIEW | agent_flagged, date_incoherence |
| 06_petroquimica_litoral_grupamento | PETROQUÍMICA LITORAL S.A. | GRUPAMENTO | alta (1.0) | auto | — |
| 07_telecom_norte_jcp_SCAN | Telecom Norte Participações S.A. | JCP | media (0.732) | REVIEW | ocr_origin |
| 08_construtora_horizonte_bonificacao | CONSTRUTORA HORIZONTE S.A. | BONIFICACAO | media (0.687) | REVIEW | agent_flagged, golden_unmatched |

## Documentos em revisão (detalhe)

### 03_siderurgica_paranaense_proventos — COMPANHIA SIDERÚRGICA PARANENSE S.A. (severidade: alta)
- Ação sugerida: **conferir identificadores contra a base**
- [media] `golden_partial` — divergências: ["issuer='siderurgica paranense' diverge do golden ('siderurgica paranaense')"]
- [alta] `title_substance_conflict` — titulado 'JCP' mas substância JCP
- [baixa] `agent_flagged` — Conflito título×substância: título do aviso é 'Distribuição de Dividendos', mas a substância do evento é JCP (Juros sobre Capital Próprio) — evidências: remuneração do capital próprio limitada à TJLP, IRRF 17,5%, imputação ao dividendo mínimo obrigatório.

### 04_rede_varejo_jcp_sem_data — REDE VAREJO BRASIL S.A. (severidade: media)
- Ação sugerida: **aguardar aviso complementar**
- [media] `missing_required` — data de pagamento ausente
- [baixa] `agent_flagged` — Data de pagamento ausente ("A definir" no documento) - campo obrigatório não disponível; revisão humana necessária para acompanhamento de aviso complementar.

### 05_aurora_saneamento_dividendo_datas — AURORA SANEAMENTO S.A. (severidade: alta)
- Ação sugerida: **reler datas no aviso / conciliar**
- [alta] `date_incoherence` — ex (2026-07-16) posterior a payment (2026-07-10)
- [alta] `agent_flagged` — A data de pagamento (10/07/2026) é ANTERIOR à data com (15/07/2026) e à data ex (16/07/2026), violando a ordenação esperada aprovação ≤ data_com ≤ ex ≤ pagamento. A leitura foi confirmada por re-leitura da página - não se trata de erro de OCR. O documento apresenta inconsistência factual entre as datas. Necessário esclarecimento com a companhia para definir qual(is) data(s) está(ão) correta(s).

### 07_telecom_norte_jcp_SCAN — Telecom Norte Participações S.A. (severidade: media)
- Ação sugerida: **validar campos contra o digitalizado**
- [media] `ocr_origin` — documento escaneado (OCR) — extração não confirmada por texto nativo

### 08_construtora_horizonte_bonificacao — CONSTRUTORA HORIZONTE S.A. (severidade: alta)
- Ação sugerida: **confirmar cadastro do emissor antes de processar**
- [alta] `golden_unmatched` — emissor/ISIN/ticker não constam na base de referência
- [baixa] `agent_flagged` — Golden record não encontrou correspondência para ISIN (BRCNHZACNOR5), ticker (CNHZ3), CNPJ (09.888.999/0001-21) e emissor (CONSTRUTORA HORIZONTE S.A.) — todos os campos estão 'fora do golden'. Documento é internamente coerente e válido; revisão para confirmar se é registro legítimo ou dado de teste.
