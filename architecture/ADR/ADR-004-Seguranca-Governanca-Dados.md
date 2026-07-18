# ADR-004: Segurança e Governança de Dados

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP armazena e processa dados de múltiplas fontes, incluindo dados públicos, dados enriquecidos e eventos hospitalares simulados que podem representar cenários com identificadores pessoais.

A arquitetura precisa demonstrar boas práticas de segurança, privacidade, controle de acesso, rastreabilidade e governança, mesmo em um MVP.

## Decisão

A arquitetura adotará controles de segurança e governança desde a concepção.

As principais diretrizes serão:

- bloqueio de acesso público nos buckets S3;
- criptografia em repouso com KMS quando aplicável;
- criptografia em trânsito para comunicação entre serviços;
- segregação de permissões por camada: Staging, Bronze, Silver, Gold e DW;
- uso do princípio do menor privilégio em políticas IAM;
- uso de Secrets Manager e/ou KMS para segredos, chaves e parâmetros sensíveis;
- logs operacionais sem PII ou payloads sensíveis;
- trilhas de auditoria com CloudTrail quando aplicável;
- monitoramento operacional com CloudWatch;
- separação clara entre dados identificáveis, dados pseudonimizados e dados analíticos;
- ausência de CPF ou identificadores sensíveis em Gold, DW, dashboards e APIs analíticas.

## Justificativa

A segurança precisa ser considerada desde o início para evitar propagação indevida de dados sensíveis e reduzir riscos de exposição.

A camada Staging merece controle específico porque pode receber dados brutos temporários antes da validação e da pseudonimização. Bronze, Silver, Gold e DW também exigem níveis distintos de permissão conforme finalidade, sensibilidade e público consumidor.

A adoção de IAM com menor privilégio, criptografia, logs sem PII e segregação por camada cria uma base mais adequada para evolução futura com dados reais e requisitos formais de governança.

## Alternativas consideradas

- **Controle de acesso amplo no MVP:** simplifica testes, mas aumenta risco de exposição e cria dívida técnica de segurança.
- **Aplicar segurança apenas em produção:** reduz esforço inicial, mas pode exigir retrabalho significativo e permitir padrões inseguros desde o início.
- **Manter dados sensíveis em todas as camadas:** facilita rastreabilidade, mas aumenta risco e reduz aderência a princípios de minimização e privacidade.
- **Governança apenas documental:** insuficiente sem controles técnicos aplicados em IAM, S3, logs, catálogo e pipelines.

## Consequências

### Positivas

- Redução do risco de exposição de dados.
- Melhor aderência a privacidade e minimização de dados.
- Separação clara de responsabilidades por camada.
- Base técnica mais adequada para evolução com dados reais.
- Maior rastreabilidade operacional.
- Melhor controle sobre acesso a dados brutos, tratados e analíticos.

### Negativas / Trade-offs

- Maior esforço inicial de configuração.
- Necessidade de manter políticas IAM, KMS, Secrets Manager e permissões atualizadas.
- Pode aumentar complexidade para desenvolvimento e testes.
- Erros de configuração podem bloquear pipelines ou consultas legítimas.

## Escalabilidade e alternativas

IAM por recurso/prefixo atende uma equipe no MVP. Com múltiplos times, dados
reais ou compartilhamento, Lake Formation deve centralizar permissões de
catálogo e filtros por linha/coluna, e AWS Organizations deve separar ambientes.

CloudTrail data events em todos os objetos pode gerar custo e ruído; selecionar
buckets sensíveis e retenção. KMS também possui quotas e custo por request; S3
Bucket Keys, cache seguro e chaves por sensibilidade devem ser avaliados.

## Critérios de evolução

Esta decisão deve ser revisada se:

- dados reais forem utilizados;
- houver exigência formal de Lake Formation;
- múltiplos usuários ou times passarem a consumir o Data Lake;
- houver necessidade de segregação por conta AWS;
- houver requisito formal de auditoria, compliance ou RIPD;
- forem criadas APIs ou produtos de dados externos.

## Referências

- AWS IAM
- AWS KMS
- AWS Secrets Manager
- Amazon S3 Block Public Access
- AWS CloudTrail
- Amazon CloudWatch
- AWS Lake Formation
- LGPD
