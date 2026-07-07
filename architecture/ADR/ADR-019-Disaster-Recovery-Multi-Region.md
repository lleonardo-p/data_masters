# ADR-019: Estratégia de Disaster Recovery

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP será implementado inicialmente como MVP em uma única região AWS, com foco em simplicidade, baixo custo e velocidade de desenvolvimento.

Mesmo sem requisito produtivo crítico no momento, a arquitetura deve deixar explícitos os limites de resiliência assumidos e os critérios para evolução futura de Disaster Recovery.

## Decisão

O MVP será implantado em **uma única região AWS**, sem estratégia ativa de **Multi-Region**.

Não será desenhada uma estratégia explícita de alta disponibilidade Multi-AZ além da disponibilidade nativa oferecida pelos serviços gerenciados utilizados.

A recuperação no MVP será baseada em:

- infraestrutura versionada com Terraform;
- dados armazenados no S3 com versionamento quando aplicável;
- políticas de lifecycle e retenção;
- backups ou exportações de metadados quando necessário;
- documentação dos recursos necessários para reconstrução do ambiente.

Uma estratégia formal de DR, com RTO/RPO definidos, replicação cross-region e testes periódicos, será considerada apenas em uma evolução produtiva ou crítica da plataforma.

## Justificativa

No escopo atual, o custo e a complexidade de uma arquitetura Multi-Region não são proporcionais ao objetivo do MVP.

A escolha single-region reduz esforço operacional e permite concentrar o projeto na arquitetura de dados, pipelines, governança e consumo analítico.

Ao mesmo tempo, manter infraestrutura como código e dados organizados no S3 permite uma base mínima de recuperação e evolução futura para DR formal.

## Alternativas consideradas

- **Multi-Region ativo-ativo:** oferece maior disponibilidade, mas adiciona alta complexidade de replicação, consistência, rede, custo e operação.
- **Multi-Region ativo-passivo:** reduz tempo de recuperação em cenários críticos, mas ainda adiciona custo e desenho operacional fora do escopo do MVP.
- **Backups manuais sem IaC:** simples, mas pouco confiável e difícil de reproduzir.
- **Ignorar DR completamente:** reduz esforço inicial, mas não documenta riscos e limitações assumidas.

## Consequências

### Positivas

- Menor custo no MVP.
- Menor complexidade operacional.
- Decisão alinhada ao escopo de portfólio e validação arquitetural.
- Infraestrutura pode ser reconstruída a partir de código.
- Evolução futura para DR formal permanece possível.

### Negativas / Trade-offs

- Indisponibilidade regional pode afetar toda a solução.
- RTO/RPO não são agressivos no MVP.
- Recuperação pode depender de reexecução de pipelines e reconstrução de recursos.
- Sem replicação cross-region ativa no escopo inicial.

## Critérios de evolução

Esta decisão deve ser revisada se:

- o projeto evoluir para produção crítica;
- forem definidos RTO/RPO formais e agressivos;
- houver exigência de continuidade em caso de falha regional;
- dados ou metadados precisarem ser replicados entre regiões;
- consumidores externos dependerem da plataforma com SLA;
- houver requisito regulatório ou corporativo de DR testado.

## Referências

- AWS Well-Architected Framework — Reliability Pillar
- AWS Disaster Recovery Strategies
- Amazon S3 Replication
- Terraform
- AWS Backup
