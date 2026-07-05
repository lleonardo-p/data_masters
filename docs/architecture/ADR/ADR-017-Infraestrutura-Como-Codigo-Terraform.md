# ADR-017: Infraestrutura como Código com Terraform

- **Status:** Aceito
- **Data:** 2026-07-05
- **Decisor:** Leonardo Lucas Pereira

---

## Contexto

O BAIP usa múltiplos serviços AWS e precisa de provisionamento reproduzível, versionado e seguro.

Configuração manual aumenta risco de erro, dificulta replicação de ambientes e prejudica evolução da arquitetura.

## Decisão

A infraestrutura será definida com **Terraform**.

A implementação deve considerar:

- módulos por domínio ou serviço;
- variáveis por ambiente;
- backend remoto com locking em cenário produtivo;
- tags obrigatórias para custo e ownership;
- validação em pull request com `terraform fmt`, `validate` e `plan`;
- análise estática com ferramentas como Checkov ou tfsec;
- `prevent_destroy` para recursos críticos quando aplicável.

## Justificativa

Terraform é amplamente usado no mercado, é cloud-agnostic e permite versionar a infraestrutura junto ao projeto.

Isso torna a arquitetura mais profissional e reduz o risco de drift entre documentação e ambiente real.

## Alternativas consideradas

- **AWS CloudFormation:** integração nativa AWS, mas menos flexível para eventual evolução multicloud.
- **AWS CDK:** produtivo para times de desenvolvimento, mas adiciona dependência de linguagem e build.
- **Provisionamento manual:** rejeitado por risco operacional e baixa reprodutibilidade.

## Consequências

### Positivas

- Infraestrutura versionada e reproduzível.
- Melhor rastreabilidade de mudanças.
- Base para CI/CD.
- Redução de configuração manual.

### Negativas

- Exige disciplina de estado remoto.
- Mudanças incorretas podem afetar recursos críticos.
- Requer revisão e validação antes do apply.

## Critérios de evolução

Revisar esta decisão se:

- o projeto migrar para estratégia multi-cloud com ferramentas diferentes;
- a equipe preferir abordagem programática com CDK;
- a gestão de estado ficar complexa;
- houver necessidade de plataforma interna de provisionamento.

## Referências

- Terraform
- Terraform AWS Provider
- Checkov
- tfsec
