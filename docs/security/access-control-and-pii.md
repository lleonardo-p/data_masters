# Segurança, LGPD e modelo de acesso

## Escopo

O BAIP utiliza dados públicos no batch e dados hospitalares exclusivamente
sintéticos no NRT. Mesmo assim, o desenho demonstra controles que seriam
necessários antes de receber dados pessoais reais. Esta documentação não
substitui avaliação jurídica, RIPD ou políticas corporativas.

## Classificação

| Classe | Exemplo | Local permitido | Restrições |
|---|---|---|---|
| Público de origem | Extratos OpenDataSUS | Staging, Bronze, Silver e Gold conforme contrato | Integridade, linhagem e termos da fonte |
| Técnico operacional | `job_run_id`, checksum, logs sem payload | Logs e manifestos | Retenção e acesso operacional |
| PII sintética | Documento fictício do simulador | Memória do ingress e, se indispensável, zona restrita | Nunca em Git, logs, Silver, Gold, Athena ou BI |
| Pseudônimo | `patient_id` | Silver NRT e store operacional controlada | Ainda é dado controlado; não chamar de anônimo |
| Analítico | Métricas agregadas e dimensões aprovadas | Gold, views e API | Sem identificador direto |

## Papéis

### Ingestion operator

- `PutObject` somente na Staging e fonte autorizada;
- leitura opcional de metadados do próprio upload;
- sem permissão de alterar jobs, IAM, Gold ou quarentena;
- autenticação federada e credencial temporária em produção.

### Glue execution role

- leitura do prefixo de entrada e referência;
- escrita apenas no prefixo de saída do job;
- leitura do script no bucket de artefatos;
- logs e métricas necessários;
- sem wildcard para todos os buckets da conta em produção.

### Data engineer

- inicia e investiga pipelines;
- consulta datasets técnicos conforme ambiente;
- não recebe acesso automático ao identity store NRT;
- mudanças de produção passam por revisão de código.

### Data quality reviewer

- lê quarentena e metadados da regra;
- reprocessa por procedimento aprovado;
- não altera o dado original;
- acesso temporário quando houver conteúdo sensível.

### Analyst / BI

- usa Athena Workgroup específico;
- `SELECT` em views/tabelas Gold aprovadas;
- sem acesso a Staging, Bronze, Silver, quarentena ou identidade;
- limite de bytes e local de resultados controlados.

### Security auditor

- lê configuração, CloudTrail e evidências;
- não precisa ler o conteúdo epidemiológico para auditar mudanças;
- ações administrativas separadas das ações de consumo.

## Controles por camada

| Camada | Controle principal |
|---|---|
| Staging | Escrita restrita, checksum, retenção curta e ausência de consumo analítico |
| Bronze batch | Imutabilidade lógica, linhagem, criptografia e acesso de engenharia |
| Bronze NRT restrita | Evitar quando possível; se necessária, KMS, retenção mínima e auditoria de objetos |
| Silver | PII direta removida, qualidade e acesso técnico |
| Quarentena | Mesma ou maior classificação do dado de origem; acesso por finalidade |
| Gold | Dados aprovados para analytics e acesso por view/tabela |
| Athena results | Bucket próprio, criptografia, lifecycle e acesso do Workgroup |
| Logs | Nunca registrar payload ou identificador direto; retenção definida |

## IAM e Lake Formation

IAM controla quem chama APIs e acessa recursos. No MVP, policies por bucket,
prefixo, Glue job e Workgroup demonstram menor privilégio.

Quando múltiplas equipes ou dados reais entrarem na plataforma, Lake Formation
é a evolução para controlar permissões do Data Catalog e filtros por linha,
coluna ou célula. A migração deve remover permissões amplas herdadas e validar o
modelo de credenciais temporárias usado pelo Athena.

## Criptografia e chaves

- TLS em trânsito;
- SSE-S3 pode atender dados públicos do MVP;
- SSE-KMS é recomendado para áreas sensíveis, resultados e identidade;
- chaves separadas por ambiente e sensibilidade em produção;
- rotação e policy da chave documentadas;
- S3 Bucket Keys podem reduzir chamadas e custo de KMS em alto volume;
- segredo de HMAC no Secrets Manager/KMS, nunca em variável versionada.

## Auditoria

CloudTrail management events registra administração de recursos. Acesso a
objetos S3 exige habilitar data events para buckets/prefixos relevantes, o que
gera custo e deve ser aplicado conforme risco. Alertas devem cobrir mudanças de
bucket policy, KMS, IAM, Glue jobs, crawler, Lake Formation e trilhas.

## Hash, tokenização e anonimização

Há três conceitos diferentes:

- `record_hash` do batch: identidade técnica do conteúdo para deduplicação;
- HMAC/token do NRT: pseudonimização controlada de identificador;
- anonimização: processo que impede associação razoável ao titular e exige
  análise além de simplesmente aplicar hash.

Não documentar hash simples de CPF como anonimização. Domínios de identificador
possuem baixa entropia e podem ser testados; use pseudonimização com segredo,
isolamento e minimização.

## Produção

Antes de dados reais:

1. avaliar base legal, finalidade, minimização e retenção;
2. executar threat model e RIPD quando aplicável;
3. separar contas e ambientes;
4. implantar Lake Formation e acesso federado;
5. configurar KMS, CloudTrail data events e alertas;
6. testar revogação, expurgo, incident response e break-glass;
7. comprovar que logs, DLQ e quarentena não ampliam exposição.

## Referências

- [Lake Formation e Athena](https://docs.aws.amazon.com/lake-formation/latest/dg/athena-lf.html)
- [Controle fino no Lake Formation](https://docs.aws.amazon.com/lake-formation/latest/dg/access-control-fine-grained.html)
- [Integridade de objetos no S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html)
- [Proteção de dados no S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DataDurability.html)
- [LGPD — Lei 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)

