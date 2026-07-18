# ADR-023: Padrões de Ingestão da Plataforma

- **Status:** Proposto
- **Data:** 2026-07-18
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP deixou de representar apenas um pipeline batch e passou a demonstrar uma
plataforma com três necessidades: arquivos periódicos de dengue, eventos
hospitalares NRT e dados diários de API externa.

Forçar todas as fontes a usar o mesmo mecanismo, todas as camadas e as mesmas
regras aumentaria custo e acoplamento sem melhorar o produto de dados.

## Decisão

A plataforma adotará três padrões de ingestão:

1. **Managed file intake:** arquivo entregue por operador/parceiro na Staging,
   seguido de Bronze, Silver, quarentena, Gold e consumo.
2. **Event-driven NRT:** evento sintético em SQS, processamento Lambda,
   idempotência e serving DynamoDB/API, com persistência pseudonimizada quando
   necessária.
3. **Scheduled external API:** EventBridge Scheduler e orquestração de extração
   diária, com publicação até a Silver.

Os padrões compartilham metadados, observabilidade, IAM, idempotência e
convenções. Qualidade detalhada, quarentena e Gold são aplicadas conforme risco
e consumidor, não obrigatoriamente em toda fonte.

## Justificativa

Arquivos, eventos e APIs possuem cadência, falhas e requisitos diferentes. A
separação permite usar Glue onde o Spark é útil, Lambda onde eventos pequenos
precisam de baixa operação e Fargate somente quando duração/dependências
justificarem containers.

## Alternativas consideradas

- **Um pipeline genérico para tudo:** reduz quantidade de componentes, mas
  oculta diferenças de retry, replay, contrato e latência.
- **Glue para todas as cargas:** padroniza o motor, mas é caro e inadequado para
  evento a evento ou extrações simples.
- **Lambda para tudo:** simples inicialmente, mas não atende batch distribuído e
  possui limite máximo de execução.
- **Streaming para todas as fontes:** aumenta custo e complexidade sem reduzir a
  latência de fontes publicadas diariamente ou anualmente.

## Consequências

### Positivas

- adequação entre requisito e tecnologia;
- demonstração de múltiplos padrões de engenharia;
- escala e falha tratadas conforme cada fonte;
- possibilidade de onboarding por template;
- evita criar Gold e quarentena sem consumidor ou risco que justifique.

### Negativas / Trade-offs

- mais de um runbook e modelo operacional;
- observabilidade precisa correlacionar tecnologias diferentes;
- convenções compartilhadas precisam ser governadas;
- a equipe precisa conhecer batch, eventos e APIs.

## Escalabilidade e alternativas

File intake evolui para canais gerenciados e processamento particionado. API
diária evolui de Lambda para fan-out limitado e Fargate quando duração ou
dependências exigirem. NRT evolui de SQS/Lambda para Kinesis/MSK/Flink quando
replay, ordenação, consumidores ou estado contínuo justificarem.

O onboarding de novas fontes deve usar contrato, ownership, SLO e estimativa de
volume para escolher um padrão. Quantidade de fontes, por si só, não determina o
serviço; o gargalo pode ser rate limit externo, subnet, downstream ou custo.

## Critérios de evolução

Revisar se:

- uma quarta categoria de ingestão não couber nos padrões;
- houver plataforma corporativa de integração obrigatória;
- contratos e observabilidade divergirem entre times;
- escala exigir control plane próprio de onboarding;
- dados reais alterarem requisitos de privacidade e isolamento.

## Referências

- [AWS Data Analytics Lens](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/)
- [EventBridge Scheduler](https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html)
- [Lambda com SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [AWS Glue ETL](https://docs.aws.amazon.com/prescriptive-guidance/latest/serverless-etl-aws-glue/aws-glue-etl.html)
- [Fargate networking](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-task-networking.html)

