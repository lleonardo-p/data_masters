# Data Masters — Trilha de Engenharia de Dados

## BAIP — Brazil Arbovirus Intelligence Platform

### Plataforma de Inteligência Epidemiológica e Assistencial — Caso Dengue

**Autor:** Leonardo Lucas Pereira<br>
**Formação:** Engenheiro de Computação e especialista em Engenharia de Machine Learning<br>
**Atuação no projeto:** Arquitetura e desenvolvimento

---

## 1. Objetivo

A **BAIP — Brazil Arbovirus Intelligence Platform** transforma dados de dengue em informações para apoiar decisões de saúde pública.

A plataforma oferece duas visões complementares:

* **análise histórica:** identifica os territórios e grupos mais impactados, além da evolução de casos, hospitalizações e ocorrências graves;
* **monitoramento ativo:** acompanha triagens recentes por território, unidade, faixa etária e nível de risco.

Com essas informações, gestores e profissionais autorizados podem priorizar investigações, campanhas preventivas, equipes, insumos e capacidade hospitalar.

A BAIP não realiza diagnóstico médico nem prevê epidemias automaticamente. Seus indicadores apoiam a análise do cenário e a preparação da rede de atendimento.

> **Em resumo:** a plataforma ajuda a responder **onde agir, quando agir, para quem direcionar os esforços e como preparar a rede de atendimento**.

### 1.1 Visão histórica

O painel apresenta os territórios e grupos com maior impacto nos registros processados entre janeiro de 2024 e fevereiro de 2026.

![Indicadores históricos de dengue](docs/assets/baip-indicadores-historicos.png)

Os rankings utilizam valores absolutos e percentuais calculados a partir dos dados disponíveis.

### 1.2 Monitoramento NRT

O painel NRT apresenta as triagens processadas em tempo quase real, permitindo acompanhar o volume recente de atendimentos por UF e nível de risco.

A visualização destaca:

- as UFs com maior volume de triagens;
- a quantidade total de triagens no período;
- o número de UFs com atividade;
- os atendimentos classificados com risco laranja ou vermelho;
- a distribuição das triagens entre os diferentes níveis de risco.

![Monitoramento NRT de triagens de dengue](docs/assets/baip-indicadores-NRT.png)

Os indicadores podem apoiar a identificação de mudanças recentes na procura por atendimento e orientar a investigação e a preparação da rede assistencial. Eles não representam diagnóstico médico nem confirmação automática de epidemia.

---

## 2. Fluxos da plataforma

A BAIP contempla dois fluxos de processamento: **Batch** e **Near Real-Time**. As decisões adotadas estão registradas nos [Architecture Decision Records](architecture/ADR/).

### 2.1 Fluxo Batch

O fluxo Batch consome dados históricos de dengue por meio de uma API alimentada com arquivos oficiais do DATASUS.

Os registros percorrem etapas de extração, armazenamento, tratamento, qualidade, modelagem e reconciliação até serem disponibilizados em views analíticas.

**Serviços AWS envolvidos:** 9.

> [!IMPORTANT]
> [Acessar a documentação do fluxo Batch](docs/batch/README.md)

![Arquitetura do fluxo Batch](architecture/c4/batch/fluxo_batch.drawio.svg)

---

### 2.2 Fluxo NRT — Near Real-Time

O fluxo NRT recebe mensagens publicadas por sistemas hospitalares e processa eventos recentes de triagem.

Os dados são validados, pseudonimizados e transformados em indicadores operacionais. A plataforma também permite a consulta autorizada do histórico de triagem de um paciente sem expor diretamente seus dados pessoais.

**Serviços AWS envolvidos:** 8.

> [!IMPORTANT]
> [Acessar a documentação do fluxo NRT](docs/nrt/README.md)

> **Diagrama da arquitetura NRT:** em desenvolvimento.

<!--
![Arquitetura do fluxo NRT](architecture/c4/nrt/fluxo_nrt.drawio.svg)
-->

---

## 3. Considerações

## Fonte dos dados

> [!NOTE]
> As limitações do MVP, fontes dos dados, plano de recuperação e estimativa de custos estão documentados em [Considerações do projeto](docs/considerations/README.md).

---

## 4. Instalação e utilização

> [!IMPORTANT]
> [Acessar o guia de instalação](docs/usage/installation.md)

> [!NOTE]
> [Acessar os comandos de demonstração](docs/usage/COMANDOS_MAKE.md)
