# ADR-019: Disaster Recovery e Multi-Region

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

A arquitetura inicial do BAIP prioriza baixo custo e simplicidade, usando uma única região AWS. Porém, uma solução produtiva deve considerar indisponibilidade regional, perda de metadados, recuperação de dados críticos e continuidade operacional.

## Decisão

Para o MVP, a arquitetura permanecerá **single-region**, com serviços gerenciados e Multi-AZ quando suportado nativamente.

Para produção, a arquitetura deverá evoluir para uma estratégia formal de Disaster Recovery, incluindo:

- replicação cross-region de dados críticos do S3;
- backup/versionamento de metadados do catálogo;
- infraestrutura reproduzível via Terraform;
- documentação de RTO e RPO;
- plano de restauração testável;
- separação entre dados críticos e dados reprocessáveis.

## Justificativa

Multi-Region aumenta custo e complexidade. Para o MVP, a prioridade é demonstrar arquitetura clara e economicamente viável. Para produção crítica, DR precisa ser planejado explicitamente.

## Alternativas consideradas

- **Multi-Region ativo-ativo desde o início:** robusto, mas caro e excessivo para o MVP.
- **Sem estratégia de DR:** reduz custo, mas não é aceitável para produção.
- **Backup manual:** frágil e pouco confiável.

## Consequências

### Positivas

- Mantém o MVP barato e simples.
- Cria caminho claro para produção resiliente.
- Permite priorizar dados realmente críticos.

### Negativas

- MVP não tolera indisponibilidade regional completa.
- Produção exigirá investimento adicional.
- Replicação entre regiões pode aumentar custo e complexidade de governança.

## Critérios de evolução

Evoluir para DR formal quando:

- houver uso com dados reais;
- houver SLA de disponibilidade;
- o custo de indisponibilidade for relevante;
- consumidores dependerem da plataforma para decisão operacional.

## Referências

- AWS Disaster Recovery
- Amazon S3 Cross-Region Replication
- AWS Well-Architected Reliability Pillar
