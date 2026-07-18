# Dashboard de dengue no Amazon QuickSight

## Objetivo e estado

O dashboard é um consumidor downstream do batch aprovado. Ele não transforma
Bronze, Silver ou Gold e não participa da reconciliação. O código do repositório
prepara:

- a view Athena `vw_dengue_dashboard`;
- um datasource QuickSight ligado ao workgroup Athena do BAIP;
- um dataset SPICE agregado para o painel;
- um script de atualização do SPICE após um batch concluído.

Os recursos QuickSight ficam desativados por padrão. A assinatura é uma ação
manual e explícita porque cria cobrança recorrente.

## Dataset do painel

A view `src/athena/dengue/views/06_vw_dengue_dashboard.sql` agrega os casos no
grão:

```text
mês + doença + município + UF + região + faixa etária + classificação
```

Esse grão suporta os filtros e indicadores do painel sem importar as colunas
detalhadas das 8,5 milhões de notificações para o SPICE. Cada caso pertence a
uma única combinação dessas dimensões; por isso, as medidas continuam
aditivas quando o usuário remove ou aplica filtros.

## Custo

Use QuickSight Standard Edition, sem recursos Pro ou Q. A assinatura Standard
mensal custa US$ 12 por autor e inclui 10 GB de SPICE, além do custo normal das
consultas Athena usadas durante ingestões. Confirme o preço exibido na conta
antes de assinar.

O Terraform não cria nem cancela a assinatura QuickSight. Remover datasource e
dataset não encerra a cobrança da assinatura.

Referência: [preços do Amazon QuickSight](https://aws.amazon.com/quick/quicksight/pricing/).

## Pré-requisitos

1. O batch e o crawler Gold devem estar concluídos.
2. As views Athena devem estar implantadas, incluindo
   `vw_dengue_dashboard`.
3. A conta QuickSight Standard deve estar ativa em `us-east-1`.
4. O QuickSight deve estar autorizado a usar Athena, o bucket do Data Lake e o
   bucket de resultados Athena.
5. Um usuário QuickSight com papel `AUTHOR` deve existir.

Implante ou atualize as views:

```bash
./scripts/deploy_athena_dengue_views.sh
```

Confirme a nova view:

```sql
SHOW VIEWS IN baip_dev_gold LIKE 'vw_dengue_dashboard';
```

Na administração do QuickSight, em **Security & permissions / AWS resources**,
autorize Athena e selecione somente os buckets necessários. Essa autorização
cria ou atualiza a role de serviço usada pelo QuickSight no MVP.

Referências:

- [conectar o QuickSight ao Athena](https://docs.aws.amazon.com/quick/latest/userguide/create-a-data-set-athena.html);
- [solucionar permissões Athena e S3](https://docs.aws.amazon.com/quick/latest/userguide/troubleshoot-athena-insufficient-permissions.html).

## Recuperar o ARN do autor

```bash
AWS_PROFILE="baip-dev"
AWS_REGION="us-east-1"

AWS_ACCOUNT_ID="$(
  aws sts get-caller-identity \
    --profile "${AWS_PROFILE}" \
    --query Account \
    --output text
)"

aws quicksight list-users \
  --aws-account-id "${AWS_ACCOUNT_ID}" \
  --namespace default \
  --profile "${AWS_PROFILE}" \
  --region "${AWS_REGION}" \
  --query 'UserList[].{Name:UserName,Role:Role,Arn:Arn}' \
  --output table
```

Use o ARN do usuário `AUTHOR` retornado pelo comando.

## Habilitar os recursos Terraform

Copie o exemplo versionado para um arquivo local ignorado pelo Git:

```bash
cp \
  infra/terraform/environments/dev/quicksight.auto.tfvars.example \
  infra/terraform/environments/dev/quicksight.auto.tfvars
```

Edite `infra/terraform/environments/dev/quicksight.auto.tfvars`:

```hcl
enable_quicksight_dengue = true
quicksight_author_arn     = "arn:aws:quicksight:us-east-1:<account-id>:user/default/<user>"
```

Depois:

```bash
TF_DIR="infra/terraform/environments/dev"

terraform -chdir="${TF_DIR}" fmt -recursive
terraform -chdir="${TF_DIR}" validate
terraform -chdir="${TF_DIR}" plan -out=quicksight-dengue.tfplan
terraform -chdir="${TF_DIR}" apply quicksight-dengue.tfplan
```

O plan esperado adiciona dois recursos:

```text
aws_quicksight_data_source.dengue_athena[0]
aws_quicksight_data_set.dengue_dashboard[0]
```

Não aplique se o plan indicar remoção inesperada de recursos do lake ou do
pipeline.

## Construir o painel

No QuickSight:

1. Abra **Analyses** e crie uma análise usando o dataset
   `Dengue - panorama epidemiologico`.
2. Nomeie a análise e o dashboard como
   `Panorama Epidemiológico da Dengue`.
3. Crie os campos calculados abaixo.
4. Monte os filtros e visuais conforme a especificação.
5. Publique a análise como dashboard.

Campos calculados:

```text
confirmation_rate =
ifelse(
  sum({notification_count}) = 0,
  0,
  sum({confirmed_case_count}) / sum({notification_count})
)

hospitalization_rate =
ifelse(
  sum({confirmed_case_count}) = 0,
  0,
  sum({hospitalized_case_count}) / sum({confirmed_case_count})
)

lethality_rate =
ifelse(
  sum({confirmed_case_count}) = 0,
  0,
  sum({death_by_disease_count}) / sum({confirmed_case_count})
)
```

Formate as três taxas como percentual.

### Layout recomendado

| Visual | Dimensão | Medida |
|---|---|---|
| KPI Notificações | — | soma de `notification_count` |
| KPI Confirmados | — | soma de `confirmed_case_count` |
| KPI Hospitalizados | — | soma de `hospitalized_case_count` |
| KPI Óbitos | — | soma de `death_by_disease_count` |
| KPI Letalidade | — | `lethality_rate` |
| Linha temporal | `notification_period` | notificações e confirmados |
| Ranking UF | `uf_abbreviation` | confirmados |
| Ranking município | `municipality_name` | confirmados, Top 15 |
| Barras por idade | `age_group_name` | confirmados |
| Barras por classificação | `classification_name` | notificações |

Filtros da página:

```text
notification_year
notification_month
region_name
uf_abbreviation
municipality_name
age_group_name
classification_name
```

Um mapa pode ser incluído depois de validar a geocodificação dos municípios.
Não publique localizações incorretas apenas com base no texto do nome; uma
evolução segura é enriquecer a dimensão IBGE com latitude e longitude.

## Atualizar depois do batch

Depois que a Step Functions, o crawler e os checks Athena terminarem com
sucesso:

```bash
chmod +x scripts/refresh_quicksight_dengue.sh
./scripts/refresh_quicksight_dengue.sh
```

O script cria uma ingestão SPICE, acompanha o estado e falha se o QuickSight
retornar `FAILED` ou `CANCELLED`. O refresh não foi colocado dentro da Step
Functions porque o dashboard é opcional e não deve alterar o sucesso do
produto Gold.

## Encerrar o custo

Para remover os assets gerenciados pelo Terraform:

```hcl
enable_quicksight_dengue = false
quicksight_author_arn     = ""
```

Execute `terraform plan` e `terraform apply`. Depois, se o QuickSight não for
mais utilizado, cancele também a assinatura na administração do serviço. Essa
segunda ação é necessária para interromper a mensalidade do autor.
