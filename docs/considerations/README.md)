# Considerações do projeto

A BAIP foi desenvolvida como um MVP para demonstrar uma solução de engenharia de dados de ponta a ponta. O projeto prioriza processamento, qualidade, segurança, rastreabilidade e disponibilização dos dados para consumo.

## 1. Componentes locais de apoio

A pasta `api-local/` contém componentes criados exclusivamente para viabilizar a demonstração dos fluxos:

- API local responsável por disponibilizar os arquivos históricos de dengue;
- banco PostgreSQL utilizado pela API local;
- simulador de triagens hospitalares com dados pessoais sintéticos;
- dashboard Streamlit utilizado para visualizar os indicadores NRT;
- configuração do ngrok para exposição temporária da fonte Batch.

Esses componentes representam sistemas externos que, em um cenário real, seriam mantidos por órgãos governamentais, hospitais ou aplicações consumidoras.

Por esse motivo, a implementação interna desses componentes não faz parte do núcleo avaliativo da plataforma. O escopo principal começa na ingestão dos dados pela AWS e termina na disponibilização das informações pelo Athena e pela API NRT.

Nenhum dado real de paciente é utilizado no fluxo NRT. CPF, nome, telefone e e-mail são gerados exclusivamente para simulação.

## 2. Limitações e decisões do MVP

Por se tratar de um MVP desenvolvido em um período limitado, foram priorizados serviços gerenciados e serverless, reduzindo custos e esforço operacional.

A solução não utiliza uma VPC dedicada, sub-redes privadas ou endpoints privados. Os serviços se comunicam por meio dos endpoints gerenciados da AWS, protegidos por controles de IAM, criptografia e políticas de acesso.

Uma evolução para produção poderia incluir:

- VPC dedicada e sub-redes privadas;
- VPC Endpoints para S3, DynamoDB, SQS e outros serviços;
- restrição adicional do tráfego de entrada e saída;
- AWS WAF na API pública;
- autenticação integrada a um provedor corporativo de identidade;
- separação mais granular de políticas e responsabilidades;
- ambientes independentes para desenvolvimento, homologação e produção.

A infraestrutura atual utiliza funções e políticas IAM específicas para os principais componentes. Em uma evolução produtiva, essas permissões poderiam ser ainda mais restritivas, considerando recursos, operações e condições específicas para cada responsabilidade.

A observabilidade está concentrada no Amazon CloudWatch, com logs, métricas e alarmes. A centralização em ferramentas como Prometheus e Grafana não foi incluída devido ao tempo e ao escopo do MVP, mas permanece como possibilidade de evolução.

## 3. Fonte dos dados históricos

Os dados históricos utilizados no projeto foram obtidos no conjunto oficial [Sinan/Dengue — Portal de Dados Abertos do SUS](https://dadosabertos.saude.gov.br/dataset/arboviroses-dengue).

Arquivos utilizados:

- [Dengue 2024 — DENGBR24.csv.zip](https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR24.csv.zip)
- [Dengue 2025 — DENGBR25.csv.zip](https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR25.csv.zip)
- [Dengue 2026 — DENGBR26.csv.zip](https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR26.csv.zip)

Os arquivos têm como fonte o Sistema de Informação de Agravos de Notificação — SINAN, mantido pelo Ministério da Saúde.

Os dados de 2026 representam um período parcial e podem ser atualizados ou revisados pela fonte oficial.

## 4. Limites de interpretação

Os indicadores produzidos pela BAIP devem ser utilizados como apoio à análise epidemiológica e ao planejamento da rede de atendimento.

A plataforma:

- não realiza diagnóstico médico;
- não confirma automaticamente a ocorrência de epidemias;
- não substitui sistemas ou indicadores oficiais;
- não utiliza dados reais de pacientes no fluxo NRT;
- apresenta resultados condicionados à cobertura e à qualidade dos dados de origem.

O objetivo é reduzir o tempo necessário para transformar dados em informações úteis, oferecendo sinais que possam orientar investigação, priorização territorial e preparação da rede assistencial.

## 5. Continuidade e recuperação de desastre

O projeto possui um plano conceitual de continuidade e recuperação de desastre. O documento identifica os componentes críticos, os mecanismos de proteção existentes e as estratégias necessárias para recuperação dos fluxos Batch e NRT.

O plano aborda:

- cenários de falha;
- classificação dos componentes críticos;
- estratégias de backup e restauração;
- reprocessamento dos dados;
- recuperação dos recursos por infraestrutura como código;
- objetivos conceituais de RPO e RTO;
- possíveis estratégias de recuperação regional.

A recuperação completa em outra região não foi implementada no MVP. O documento registra como a plataforma poderia evoluir para atender requisitos produtivos de continuidade.

> [Acessar o plano de continuidade e recuperação de desastre](disaster-recovery.md)

## 6. Estimativa de custos

O projeto também possui uma estimativa conceitual dos custos da plataforma. Os valores são calculados com base em volumes e frequências de execução assumidos para os fluxos Batch e NRT.

A análise considera os principais serviços utilizados:

- Amazon S3;
- AWS Glue;
- AWS Lambda;
- AWS Step Functions;
- Amazon SQS;
- Amazon DynamoDB;
- Amazon API Gateway;
- Amazon Athena;
- Amazon CloudWatch;
- AWS KMS.

Os valores apresentados são projeções e não representam uma fatura real. O custo efetivo pode variar conforme região, volume processado, retenção, frequência das consultas, quantidade de eventos e alterações nos preços da AWS.

> [Acessar a estimativa de custos da plataforma](cost-estimate.md)