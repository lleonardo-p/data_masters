# Data Masters — Trilha de Engenharia de Dados

## Plataforma de Processamento de Dados — Caso Arboviroses

**Autor:** Leonardo Lucas Pereira<br>
**Formação:** Engenheiro de Computação e especialista em Engenharia de Machine Learning<br>
**Atuação no projeto:** Arquitetura e desenvolvimento

---

## 1. Objetivo

Este projeto corresponde à segunda fase do processo interno de certificação da empresa. O objetivo desta etapa é desenvolver e documentar uma solução de engenharia de dados que contemple os seguintes tópicos:

| Tópico | Objetivo |
|---|---|
| Extração de dados | Obter dados a partir de diferentes fontes e formatos |
| Ingestão de dados | Receber e encaminhar os dados para processamento |
| Armazenamento de dados | Organizar e disponibilizar os dados conforme suas etapas de processamento |
| Observabilidade | Permitir o acompanhamento das execuções, métricas e falhas |
| Segurança de dados | Proteger os dados e controlar o acesso aos recursos |
| Mascaramento de dados | Evitar a exposição de informações pessoais ou sensíveis |
| Arquitetura de dados | Definir componentes, responsabilidades e integração entre os serviços |
| Escalabilidade | Preparar a solução para evolução de volume, frequência e necessidades de negócio |

O desenvolvimento deverá considerar não apenas o funcionamento da solução, mas também os desafios encontrados, suas limitações e as melhorias futuras. O resultado esperado é uma plataforma de dados segura, eficiente, rastreável e capaz de evoluir de acordo com o crescimento da demanda.

---

## 2. Apresentação do case — Plataforma de dados para arboviroses

O case escolhido utiliza dados públicos de notificações de dengue disponibilizados pelo Ministério da Saúde. A dengue pertence ao grupo das arboviroses e foi selecionada como domínio para demonstrar diferentes padrões de processamento em uma mesma plataforma de dados.

O período analisado compreende os anos de 2024 e 2025, além dos dados disponíveis entre janeiro e julho de 2026. O arquivo de 2026 representa uma fotografia parcial correspondente à última atualização disponível durante o desenvolvimento do projeto.

Toda a solução foi projetada para execução na AWS. As decisões arquiteturais, alternativas consideradas, consequências e possibilidades de evolução estão registradas nos *Architecture Decision Records* do repositório.

> [!IMPORTANT]
> ### [Acessar as decisões arquiteturais — ADRs](architecture/ADR/)
>
> Os ADRs registram o contexto, a decisão adotada, as alternativas avaliadas, os impactos e os possíveis caminhos de evolução da plataforma.

### 2.1 Problema de negócio

Gestores e analistas de saúde pública precisam identificar municípios, períodos
e grupos populacionais que apresentam crescimento nos casos de dengue para
priorizar análises epidemiológicas, campanhas de orientação e a preparação da
rede de atendimento.

A plataforma apoia a vigilância e a preparação para possíveis surtos,
transformando dados de dengue em indicadores que ajudam a priorizar
territórios, identificar tendências, orientar os grupos mais afetados e avaliar
a necessidade de preparação da capacidade hospitalar.

O fluxo Batch disponibiliza uma visão histórica consolidada das notificações,
permitindo analisar a evolução dos casos por período, município, UF, gravidade
e faixa etária. O fluxo NRT complementa essa visão com o acompanhamento de
eventos de triagem em tempo quase real, reduzindo o intervalo entre o aumento da
procura por atendimento e sua identificação pelos responsáveis.

A combinação dos dois fluxos pode contribuir para uma resposta antecipada,
apoiando a intensificação de campanhas preventivas, a orientação da população e
a preparação de equipes, insumos, unidades de atendimento e leitos. Os
indicadores funcionam como sinais para investigação e planejamento, e não como
confirmação automática de uma epidemia.

As informações disponibilizadas permitem responder:

- Quais municípios e UFs concentram os maiores volumes de notificações e casos
  confirmados?
- Quais municípios e UFs registram mais casos graves, hospitalizações e óbitos?
- Como as notificações evoluem ao longo dos meses em cada município e UF?
- Em quais períodos ocorreu crescimento nas notificações, confirmações ou
  hospitalizações?
- Onde e quando foram registrados os maiores volumes de casos graves?
- Quais grupos etários concentram mais notificações, casos confirmados,
  hospitalizações e óbitos?
- Quais territórios e grupos etários podem ser priorizados em campanhas de
  prevenção e orientação?
- Em quais regiões houve crescimento recente na procura por triagem?
- O volume de triagens está aumentando em comparação com períodos anteriores?
- Quais regiões podem exigir uma avaliação antecipada da capacidade de
  atendimento?

As respostas devem ser interpretadas como apoio à análise epidemiológica e ao
planejamento. A plataforma não substitui indicadores oficiais, não realiza
diagnósticos e não confirma automaticamente a ocorrência de surtos ou
epidemias.


### 2.2 Estrutura da solução

A plataforma é composta por dois fluxos de processamento.

### Fluxo Batch

O fluxo Batch processa arquivos públicos de notificações de dengue. Os dados percorrem um pipeline distribuído em lote, organizado segundo a arquitetura Medallion, passando pelas etapas de recebimento, preservação, tratamento, qualidade e modelagem analítica.

O resultado é disponibilizado por meio de views consolidadas com indicadores por período, estado, município, faixa etária, classificação e outras perspectivas analíticas.

> [!IMPORTANT]
> ### [Acessar a documentação do fluxo Batch](docs/batch/README.md)
>
> Este é o fluxo implementado de ponta a ponta, desde a entrada dos arquivos na Staging até a disponibilização das views no Athena.

![Arquitetura do fluxo Batch](architecture/c4/batch/fluxo_batch.drawio.svg)

---

### Fluxo NRT — Near Real Time

O fluxo NRT simulará eventos de triagem hospitalar relacionados a casos suspeitos de dengue. Os eventos incluirão dados pessoais exclusivamente sintéticos e serão publicados em um serviço de mensageria.

Durante o processamento, serão aplicados controles de validação, idempotência e proteção de PII. O resultado será composto por indicadores operacionais atualizados em Near Real Time e disponibilizados para consumo por meio de uma API.

> [!NOTE]
> ### [Acessar a documentação do fluxo NRT — em desenvolvimento](docs/nrt/README.md)
>
> Esta frente demonstrará mensageria, processamento orientado a eventos, proteção de dados pessoais sintéticos e disponibilização de indicadores por API.

> **Diagrama da arquitetura NRT:** em desenvolvimento.

<!--
Substituir este comentário pelo diagrama final do fluxo NRT.
![Arquitetura do fluxo NRT](architecture/c4/nrt/nrt-flow.png)
-->

---

O fluxo Batch utiliza exclusivamente dados públicos. O fluxo NRT utilizará somente dados sintéticos e não processará informações reais de pacientes.

O projeto não tem como objetivo substituir sistemas ou indicadores epidemiológicos oficiais. Seu propósito é utilizar esse domínio para demonstrar conceitos, decisões e práticas de engenharia de dados.

## 3. Considerações

<!--
Seção reservada para as considerações finais, limitações identificadas,
trade-offs e possibilidades de evolução da plataforma.
-->

## 4. Utilização

O guia de instalação e utilização apresenta os pré-requisitos, a configuração
das credenciais AWS, o provisionamento da infraestrutura com Terraform e os
procedimentos necessários para executar e validar a plataforma.

> [!IMPORTANT]
> ### [Acessar o guia de instalação e utilização](docs/usage/installation.md)
>
> Consulte este documento para preparar o ambiente, provisionar os recursos e
> executar os fluxos da plataforma.