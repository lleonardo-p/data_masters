# Data Masters — Trilha de Engenharia de Dados

## Plataforma de Processamento de Dados — Caso Arboviroses

**Autor:** Leonardo Lucas Pereira  
**Formação:** Engenheiro de Computação e especialista em Engenharia de Machine Learning
**Atuação no projeto:** Arquitetura e desenvolvimento

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

## 2. Apresentação do case

O case escolhido utiliza dados públicos de notificações de dengue disponibilizados pelo Ministério da Saúde. A dengue pertence ao grupo das arboviroses e foi selecionada como domínio para demonstrar diferentes padrões de processamento em uma mesma plataforma de dados.

O período analisado compreende os anos de 2024 e 2025, além dos dados disponíveis entre janeiro e julho de 2026. O arquivo de 2026 representa uma fotografia parcial correspondente à última atualização disponível durante o desenvolvimento do projeto.

Toda a solução foi projetada para execução na AWS. As decisões arquiteturais, alternativas consideradas, consequências e possibilidades de evolução estão registradas nos *Architecture Decision Records* do repositório:

- [Decisões arquiteturais — ADRs](architecture/ADR/)

A plataforma é composta por dois fluxos:

| Fluxo | Dados | Processamento | Resultado |
|---|---|---|---|
| Batch | Arquivos públicos de notificações de dengue | Processamento em lote seguindo a arquitetura Medallion | Views consolidadas com indicadores por período, estado, município, faixa etária e classificação |
| NRT — Near Real Time | Eventos sintéticos de triagem hospitalar, incluindo dados pessoais igualmente sintéticos | Publicação em mensageria, tratamento de PII e processamento orientado a eventos | Indicadores operacionais atualizados e disponibilizados por uma API |

O fluxo Batch utiliza exclusivamente dados públicos. O fluxo NRT utilizará somente dados sintéticos e não processará informações reais de pacientes.

O projeto não tem como objetivo substituir sistemas ou indicadores epidemiológicos oficiais. Seu propósito é utilizar esse domínio para demonstrar conceitos, decisões e práticas de engenharia de dados.