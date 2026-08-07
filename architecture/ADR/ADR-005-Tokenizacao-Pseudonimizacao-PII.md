# ADR-005: Pseudonimização de Dados Pessoais

* **Status:** Aceito
* **Data:** 2026-07-05
* **Decisor:** Leonardo Lucas Pereira

## Contexto

Os eventos do fluxo NRT contêm CPF, nome, telefone e e-mail sintéticos. A plataforma precisa relacionar diferentes triagens ao mesmo paciente e permitir consultas autorizadas por CPF, sem propagar identificadores pessoais nas tabelas operacionais.

## Decisão

Aplicar o seguinte processo:

1. normalizar o CPF recebido;
2. gerar um fingerprint determinístico com HMAC-SHA-256 no AWS KMS;
3. relacionar o fingerprint a um `patient_token` aleatório;
4. armazenar o histórico utilizando somente o `patient_token`;
5. descartar CPF, nome, telefone e e-mail após o processamento.

Na consulta individual, a API reproduz o HMAC do CPF, localiza o `patient_token` e recupera o histórico correspondente.

O CPF em texto aberto não é armazenado e não existe requisito para recuperá-lo.

## Justificativa

O HMAC permite localizar o mesmo paciente de forma determinística sem expor a chave criptográfica ou armazenar o CPF.

O token aleatório desacopla o histórico clínico do identificador utilizado na busca e reduz a propagação de dados pessoais entre os componentes.

Essa técnica representa **pseudonimização**, e não anonimização, pois um usuário autorizado ainda pode localizar o histórico ao informar o CPF.

## Alternativas

* **Hash SHA-256 sem chave:** não adotado porque CPFs pertencem a um domínio limitado e poderiam ser testados por força bruta.
* **Criptografia reversível do CPF:** não adotada porque a plataforma não precisa recuperar o documento em texto aberto e isso aumentaria o impacto de um acesso indevido.
* **Mascaramento do CPF:** não adotado porque protege apenas a apresentação e não o valor armazenado.
* **Armazenamento direto do CPF:** não adotado por aumentar a exposição de dados pessoais e contrariar o princípio da minimização.
* **Token aleatório sem HMAC:** não adotado porque impediria a busca determinística por CPF sem manter uma associação adicional com o documento.
