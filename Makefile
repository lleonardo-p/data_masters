SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

AWS_PROFILE ?= baip-dev
AWS_REGION ?= us-east-1
GRANULARITY ?= month
PERIOD ?= 2024-01
PROCESSING_DATE ?= $(shell date -u +%F)
START_PERIOD ?= 2024-01
END_PERIOD ?= 2024-02
FORCE ?= false
COUNT ?= 10
INTERVAL ?= 3
SCOPE_TYPE ?= GLOBAL
SCOPE_VALUE ?=
WINDOW_MINUTES ?= 60
REFRESH_SECONDS ?= 120
CPF ?= 90088005780
LIMIT ?= 50
TF_PLAN ?= baip-dev.tfplan

.PHONY: help check infra-validate infra-plan infra-apply infra-output \
	source-download source-setup source-up source-import source-health \
	tunnel-up tunnel-url \
	tunnel-health hospital-build nrt-publish nrt-queues nrt-health \
	nrt-indicators nrt-history nrt-logs nrt-dashboard-up nrt-dashboard-health \
	nrt-dashboard-logs batch-run batch-backfill batch-status \
	batch-watch batch-history batch-manifest batch-validate \
	athena-deploy-views views down

help: ## Lista os comandos de demonstração.
	@echo "Uso: make <alvo> [VAR=valor]"
	@echo
	@echo "Infraestrutura"
	@echo "  infra-validate  Formata e valida o Terraform"
	@echo "  infra-plan      Gera um plano salvo (TF_PLAN=baip-dev.tfplan)"
	@echo "  infra-apply     Aplica exatamente o plano salvo"
	@echo "  infra-output    Exibe os outputs provisionados"
	@echo
	@echo "Fonte externa local"
	@echo "  source-download Baixa e converte os arquivos oficiais para .csv.gz"
	@echo "  source-setup    Prepara os dados, sobe a fonte e executa a importação"
	@echo "  source-up       Sobe PostgreSQL e a API local"
	@echo "  source-import   Importa os arquivos de api-local/data"
	@echo "  source-health   Verifica API local e PostgreSQL"
	@echo "  tunnel-up       Expõe a API local temporariamente com ngrok"
	@echo "  tunnel-url      Exibe a URL HTTPS atual do ngrok"
	@echo "  tunnel-health   Verifica a API por meio do túnel"
	@echo
	@echo "Batch"
	@echo "  batch-run       Executa um período (PERIOD=2024-01)"
	@echo "  batch-backfill  Executa intervalo (START_PERIOD=2024-01 END_PERIOD=2024-02)"
	@echo "  batch-status    Exibe o status da execução mais recente"
	@echo "  batch-watch     Monitora a execução até o estado terminal"
	@echo "  batch-history   Lista as últimas execuções"
	@echo "  batch-manifest  Exibe o relatório de reconciliação"
	@echo "  batch-validate  Executa os testes de aceitação no Athena"
	@echo "  athena-deploy-views  Cria ou atualiza as views analíticas no Athena"
	@echo "  views                Alias curto para athena-deploy-views"
	@echo
	@echo "NRT"
	@echo "  hospital-build  Constrói a imagem do simulador hospitalar"
	@echo "  nrt-publish     Publica eventos (COUNT=10 INTERVAL=3)"
	@echo "  nrt-queues      Exibe a quantidade de mensagens e a DLQ"
	@echo "  nrt-health      Consulta o endpoint público de saúde"
	@echo "  nrt-indicators  Consulta indicadores agregados"
	@echo "  nrt-history     Consulta histórico por CPF sintético"
	@echo "  nrt-logs        Exibe logs recentes do processador e da API"
	@echo "  nrt-dashboard-up     Sobe o painel Streamlit em http://localhost:8501"
	@echo "  nrt-dashboard-health Verifica a disponibilidade do painel"
	@echo "  nrt-dashboard-logs   Acompanha os logs do painel"
	@echo
	@echo "Ambiente"
	@echo "  check           Valida dependências e configuração local"
	@echo "  down            Encerra os contêineres locais"

check:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" ./scripts/local_demo.sh check

infra-validate:
	@terraform -chdir=infra/terraform/environments/dev fmt -check
	@terraform -chdir=infra/terraform/environments/dev validate

infra-plan: infra-validate
	@terraform -chdir=infra/terraform/environments/dev plan -out="$(TF_PLAN)"

infra-apply:
	@test -f "infra/terraform/environments/dev/$(TF_PLAN)" || \
	 (echo "Plano ausente. Execute: make infra-plan" >&2; exit 1)
	@terraform -chdir=infra/terraform/environments/dev apply "$(TF_PLAN)"

infra-output:
	@terraform -chdir=infra/terraform/environments/dev output

source-up:
	@./scripts/local_demo.sh source-up

source-download:
	@./scripts/local_demo.sh source-download

source-setup:
	@./scripts/local_demo.sh source-setup

source-import:
	@./scripts/local_demo.sh source-import

source-health:
	@./scripts/local_demo.sh source-health

tunnel-up:
	@./scripts/local_demo.sh tunnel-up

tunnel-url:
	@./scripts/local_demo.sh tunnel-url

tunnel-health:
	@./scripts/local_demo.sh tunnel-health

batch-run:
	@API_BASE_URL="$$(./scripts/local_demo.sh tunnel-url)" \
	 AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" \
	 LOAD_MODE=single GRANULARITY="$(GRANULARITY)" \
	 REFERENCE_PERIOD="$(PERIOD)" PROCESSING_DATE="$(PROCESSING_DATE)" \
	 FORCE="$(FORCE)" ./scripts/dengue_batch.sh start

batch-backfill:
	@API_BASE_URL="$$(./scripts/local_demo.sh tunnel-url)" \
	 AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" \
	 LOAD_MODE=backfill GRANULARITY="$(GRANULARITY)" \
	 START_PERIOD="$(START_PERIOD)" END_PERIOD="$(END_PERIOD)" \
	 PROCESSING_DATE="$(PROCESSING_DATE)" FORCE="$(FORCE)" \
	 ./scripts/dengue_batch.sh start

batch-status:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" ./scripts/dengue_batch.sh status

batch-watch:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" ./scripts/dengue_batch.sh watch

batch-history:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" ./scripts/dengue_batch.sh history

batch-manifest:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" ./scripts/dengue_batch.sh manifest | python3 -m json.tool

batch-validate:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" ./scripts/dengue_batch.sh validate

athena-deploy-views:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" ./scripts/deploy_athena_dengue_views.sh

views: athena-deploy-views

hospital-build:
	@./scripts/local_demo.sh hospital-build

nrt-publish:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" \
	 COUNT="$(COUNT)" INTERVAL="$(INTERVAL)" ./scripts/local_demo.sh nrt-publish

nrt-queues:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" ./scripts/local_demo.sh nrt-queues

nrt-health:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" ./scripts/dengue_nrt.sh health

nrt-indicators:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" \
	 SCOPE_TYPE="$(SCOPE_TYPE)" SCOPE_VALUE="$(SCOPE_VALUE)" \
	 WINDOW_MINUTES="$(WINDOW_MINUTES)" ./scripts/dengue_nrt.sh indicators

nrt-history:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" \
	 CPF="$(CPF)" LIMIT="$(LIMIT)" ./scripts/dengue_nrt.sh history

nrt-logs:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" ./scripts/dengue_nrt.sh logs

nrt-dashboard-up:
	@AWS_PROFILE="$(AWS_PROFILE)" AWS_REGION="$(AWS_REGION)" \
	 WINDOW_MINUTES="$(WINDOW_MINUTES)" REFRESH_SECONDS="$(REFRESH_SECONDS)" \
	 ./scripts/local_demo.sh nrt-dashboard-up

nrt-dashboard-health:
	@./scripts/local_demo.sh nrt-dashboard-health

nrt-dashboard-logs:
	@./scripts/local_demo.sh nrt-dashboard-logs

down:
	@./scripts/local_demo.sh down
