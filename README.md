# Agente de Extração de Eventos Corporativos (Asset Servicing / BTG)

Agente *code-first* que recebe um lote de avisos de eventos corporativos (PDFs nativos e
escaneados, heterogêneos) e produz, **por documento**, um registro estruturado, **validado e
auditável**, com tratamento de incerteza e roteamento para revisão humana.

No domínio (Asset Servicing) erro de extração = erro financeiro/regulatório: classificar errado o
tipo de provento muda o tratamento tributário, datas incoerentes quebram conciliações, valores
inventados viram prejuízo. Por isso o sistema é construído em torno de **verificação** e
**auditabilidade**, não só de extração.

## Como rodar

Requer **Python 3.13** (testado em 3.13.14).

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt

# 1) Offline, sem API key — roda o pipeline inteiro com fixtures (demonstra o encanamento):
python -m src.main --provider replay

# 2) Agente real (DeepSeek v4): copie .env.example -> .env e preencha DEEPSEEK_API_KEY
python -m src.main --provider deepseek
#    (troque por --provider openai com OPENAI_API_KEY para confirmar a abstração)

pytest -q                                           # 39 testes (tools, loop, routing, harness, e2e)
```

Saída em `output/`: `records/<nome-do-documento>.json` (1 por documento, **nomeado pelo arquivo
original**, ex.: `01_energetica_vale_tiete_dividendo.json`) e `exceptions_report.md` (relatório de
exceções curto). O trace de auditoria por documento (`traces/<doc>.jsonl`) é **opt-in** — rode com
`--trace`; sem a flag, `output/` contém apenas `records/` e `exceptions_report.md`.

> O `output/` versionado foi gerado com `--provider deepseek` (extração real do modelo). O
> `--provider replay` é determinístico (offline, sem chave) e reproduz os mesmos **desfechos**
> auto/review; pode diferir apenas em **motivos secundários** de um documento escaneado (doc 07),
> porque as fixtures do replay são propositalmente conservadoras.

O lote é processado **em paralelo** (fan-out por documento, I/O-bound). Ajuste a concorrência em
`config.yaml` → `max_workers` (default 4); `retry` controla backoff em rate limit da API.

> **OCR (doc 07):** usa **RapidOCR** (modelos PP-OCR em ONNX) + **pypdfium2** — 100% pip/offline,
> **sem binários de sistema** (nada de Tesseract/Poppler). Se as libs falharem, o `run_ocr` retorna indisponível e o documento é escalado para revisão.

## Segurança

- O `.env` **nunca** é versionado (está no `.gitignore`). Copie `.env.example` → `.env` e preencha a
  chave do provider **localmente**.
- Não há segredos no repositório; os PDFs do lote e o `golden_records.csv` são sintéticos (fictícios).

## Arquitetura: núcleo agêntico + harness determinístico

A decisão central foi implementar um **agente real** (fluxo de controle dirigido pelo LLM via
tools, com loop de verificação e autocorreção) — **não** uma pipeline procedural. O ganho de
acurácia vem do loop *chamar tool → observar → refletir → corrigir/escalar*. Auditabilidade e
reprodutibilidade são preservadas por um **harness determinístico** ao redor.

```
HARNESS (código, determinístico)              ← reprodutibilidade, guardrails, fan-out, trace
  └─ por documento:
       AGENT LOOP (dirigido pelo LLM)         ← agência real
         plan → call tool → observe → reflect → (corrige relendo | escala) → submit_record
         tools: read_document/read_page, run_ocr, validate_isin, lookup_golden_record,
                check_date_coherence, check_value_coherence, log_reasoning, submit_record
       RECOMPUTA validações sobre a submissão  ← defense in depth (não confia no agente)
       CRITIC PASS (LLM-as-judge)              ← refuta o registro campo a campo
       SELF-CONSISTENCY (OCR / baixa confiança)← re-extrai e mede concordância
       CONFIANÇA agregada + GUARDRAILS         ← regras sempre escalam casos graves
```

**Por que isto dá alta acurácia e ainda é auditável:**
1. **Tools determinísticas = grounding.** ISIN (mod-10), golden cross-check, bruto/líquido e
   coerência de datas são *código Python*, não geração. O modelo não consegue alucinar um valor
   "validado". O harness **recomputa** as validações sobre a submissão final — o registro reflete
   o código, não a alegação do agente.
2. **Loop de verificação obrigatório.** `submit_record` só é aceito após as validações terem rodado
   (regra forçada no loop). Falha → o agente relê a página para distinguir "li errado" de "o
   documento está incoerente" (chave no doc 05).
3. **Critic pass + self-consistency** rebaixam confiança quem diverge.
4. **Guardrails determinísticos** escalam casos graves *independente* do julgamento do agente.
5. **Determinismo + trace.** Temperatura 0, prompt versionado, e — com `--trace` — um **trace completo
   de tool calls** por documento (`output/traces/*.jsonl`) = trilha de auditoria reproduzível. Sem a
   flag, o `agent_audit` no próprio record já registra passos, tool calls, veredito do crítico e tokens.

## Observabilidade

- **Trace por documento** (`output/traces/<doc>.jsonl`, **opt-in** via `--trace`): cada evento do agente —
  `llm_request/response`, `tool_call/result`, `reasoning`, `critic`, `self_consistency`, `final` —
  com timestamp e tempo decorrido. Permite reabrir a decisão sem reabrir o PDF.
- **`log_reasoning`**: tool de observabilidade que o agente usa para registrar plano/reflexão.
- **`agent_audit`** no record: passos, tool calls, veredito do crítico, nº de re-extrações, tokens, duração.

## Como ler um record (auditar sem reabrir o PDF)

Cada `records/<doc>.json` é auditável campo a campo:
- **Campos extraídos** (`issuer`, `cnpj`, `isin`, `ticker`, `event_type`, `value_or_ratio`, `dates`) são
  objetos com `value` + `confidence_score` (0..1) + `source_text` (trecho verbatim do aviso) +
  `source_location` (tabela|corpo|cabeçalho) + `rationale` (por que aquele valor).
- **`validation`**: resultado das tools determinísticas — `golden_record` (matched/partial/unmatched),
  `isin` (formato + dígito), `coherence` (datas e bruto/líquido).
- **`confidence_overall`**: `confidence_score` agregado + `drivers` (o que subiu/baixou a confiança).
- **`review`**: `required` + `severity` + `reasons[]` (cada um com `code`, `severity`, `detail`,
  `suggested_action`) — **o que precisa de revisão humana e por quê**.
- **`ingestion`** / **`agent_audit`** / **`extraction_metadata`**: origem (text_native|ocr +
  `ocr_confidence`), passos e tool calls do agente, provider/modelo/timestamp.

## Estrutura

```
src/
  main.py                 CLI: processa o lote
  agent/  loop.py         AGENT LOOP (plan→tool→observe→reflect→submit, budget de passos)
          harness.py      orquestra; recomputa validações; critic; self-consistency; routing
          critic.py       CRITIC PASS (LLM-as-judge)
          prompts.py      system prompts + taxonomia + heurísticas
  llm/    base.py         LLMClient (ABC) + tipos de mensagem/resposta
          deepseek_client.py  adapter OpenAI-compatível (DeepSeek/OpenAI)
          replay_client.py + replay_data.py  provider offline (fixtures)
          factory.py
  tools/  ingestion.py    read_document / read_page / run_ocr
          isin.py         validate_isin (formato + mod-10)
          golden.py       lookup_golden_record (cross-check)
          coherence.py    check_date_coherence / check_value_coherence
          registry.py     JSON Schema das tools / submit.py (ação terminal)
  schema.py               modelos pydantic (AgentSubmission + Record)
  confidence.py           confiança agregada (drivers)
  routing.py              guardrails determinísticos
  observability.py        Tracer (trace de auditoria por documento)
tests/                    isin/golden/coherence/schema/routing/critic/loop/harness/report/e2e
```

## O lote (8 documentos) e desfechos

| Doc | Evento | Desafio | Desfecho |
|-----|--------|---------|----------|
| 01 | Dividendo | baseline limpo | auto |
| 02 | JCP | bruto→líquido (×0,825) | auto |
| 03 | "Dividendos" | **substância é JCP** (TJLP) → conflito título×substância | review |
| 04 | JCP | data de pagamento "A definir" → campo ausente | review |
| 05 | Dividendo intercalar | pagamento antes do ex → incoerência de datas | review |
| 06 | Grupamento | proporção 10:1, sem caixa | auto |
| 07 | JCP | escaneado → OCR, baixa confiança | review |
| 08 | Bonificação | emissor fora do golden_records | review |

Reproduzido pelo `--provider replay` (auto: 01,02,06; review: 03,04,05,07,08).

## Trade-offs — o que NÃO fiz e por quê

- **Sem pipeline distribuída (Celery/Redis/Postgres/Docker).** Foi avaliada como evolução de
  escala, mas é over-engineering para um lote de 8 documentos e deslocaria o foco da avaliação
  (qualidade/auditoria da extração) para orquestração. Em produção com alto volume, o harness
  in-process seria trocado por workers + fila + banco; a fronteira agente/tools não muda.
- **Sem fine-tuning.** Zero-shot com tools + loop de verificação é suficiente e auditável no prazo.
- **Agência limitada, não autônoma.** Conjunto fechado de tools + `max_steps` + saída forçada por
  schema + guardrails por cima. Agência ≠ autonomia ilimitada.
- **OCR via RapidOCR (PP-OCR/ONNX, offline)**, desacoplado do raciocínio — assim o provider de
  raciocínio pode ser text-only (DeepSeek v4). Escolhido sobre Tesseract por dispensar binários de
  sistema (só pip) e ter melhor acurácia em scans; sobre OCR de nuvem por manter o dado on-prem
  (contexto bancário). Fallback por vision-model fica documentado, não implementado.
- **OCR sempre escala para revisão (default conservador, não definitivo).** Todo documento de origem
  OCR é roteado para humano via guardrail, e a confiança fica limitada a 0,79. A justificativa é a
  **assimetria de custo**: em banco, um falso-aprovado com dígito trocado pelo OCR vira erro
  financeiro/regulatório, enquanto um falso-escalado custa minutos de revisão. OCR aqui é tratado
  como *não-confirmado*, não *não-confiável*. **Evolução possível** (não implementada): auto-aprovar
  um scan quando ele for **corroborado** — confiança do RapidOCR acima de um limiar **E** campos
  críticos batendo em ≥2 sinais independentes (golden + contas bruto/líquido + redundância
  prosa/tabela). Primeiro passo já feito: o `run_ocr` **captura** o score por trecho do RapidOCR e
  expõe `ocr_confidence` no record (`ingestion`); falta só a regra de corroboração. Mantido
  conservador no v1 porque o enunciado pesa *roteamento de incerteza* e o desfecho esperado do doc
  escaneado é revisão.
- **Calendário B3 simplificado.** `ex ≈ data com + 1 dia útil` é aproximado (sem base de feriados) →
  apenas *warning*, nunca escala sozinho.
- **ISIN check-digit é warning, não gate.** Descoberta importante: os ISINs do `golden_records` são
  sintéticos e **não** têm dígito mod-10 válido. O algoritmo mod-10 é o real (verificado contra
  `US0378331005`/Apple nos testes), mas o gate duro é **formato + cross-check no golden**; o dígito
  entra como sinal informativo. Sem isso, todo documento seria escalado indevidamente.
- **Provider `replay`.** Fixtures para rodar o pipeline offline e nos testes. **Não** é a extração do
  modelo — a assertividade da extração depende do LLM real (`--provider deepseek`); o replay prova o
  encanamento (validação, routing, confiança, saída, trace) de forma determinística.

## Premissas documentadas

- **Confiança numérica única**: todo campo extraído usa `confidence_score` (float 0..1) + proveniência
  rica (`source_text`, `source_location`, `rationale`) — schema padronizado, sem enum por campo. O
  rótulo legível (alta/media/baixa) é derivado do score só na exibição do relatório.
- **Baixa confiança**: score < 0,6 OU origem OCR (teto de score 0,79) OU campo inferido de prosa OU
  crítico/self-consistency divergiu. Thresholds em `config.yaml`.
- **Coerência de datas**: aprovação ≤ data com ≤ ex ≤ pagamento (violação = alta); `ex ≈ data com +
  1 dia útil` (warning); ano plausível.
- **Coerência de valor**: líquido ≈ bruto × (1 − IRRF), tolerância relativa 1%; evento de proporção
  sem valor monetário.
- **Classificação por substância, não por título** (regra explícita; justificada por registro).

## Limitações conhecidas (e por quê)

- **Detecção de camada de texto é por documento, não por página.** Um PDF misto (uma página nativa,
  outra escaneada) reporta `has_text_layer=true` e a página escaneada é perdida silenciosamente.
  Evolução: detectar por página e rodar OCR só nas vazias. Não implementado — nenhum documento do
  lote é misto, então não há caso real para validar o ganho.
- **Sem teto global de tokens/custo do lote.** `max_steps` limita o orçamento por documento; um teto
  agregado exigiria estado compartilhado entre as threads do fan-out, com ganho irrelevante para 8
  documentos. Fica como evolução para escala.
