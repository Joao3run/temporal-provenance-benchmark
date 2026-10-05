# Protocolo robusto do experimento

## Desenho

Benchmark fatorial controlado de 24 cenários: 3 perfis de relógio x 2 formatos temporais x 2 atrasos de processamento x 2 níveis de proveniência.

Unidade de análise: pares de eventos de uma mesma execução. Cada cenário gera 12 transações e seis eventos correlacionados por transação, num total de 72 eventos e 2.556 pares cronológicos possíveis.

## Pipelines comparadas

### Pipeline ingênua

Ordena o campo textual `timestamp`; quando o horário não informa fuso, assume UTC. Não consulta metadados sobre componente, semântica, offset ou incerteza. Ela representa a prática inadequada de reduzir rastros heterogêneos a uma sequência textual única.

### Pipeline de Proveniência Temporal (FPT)

Lê um manifesto separado que informa fuso, offset conhecido, semântica e incerteza. Normaliza os horários somente com esses dados. Se a proveniência é incompleta, abstém-se de ordenar os registros de modo categórico.

## Oráculo e prevenção de viés

O gerador cria uma sequência-oráculo separada dos dados usados pelas pipelines. A ordenação de referência utiliza a sequência monotônica interna do cenário e os tempos UTC de ocorrência, não os timestamps apresentados nos logs. Após a geração, cada arquivo é incluído em `checksums.sha256`.

Para execução de artigo, o hash do oráculo será registrado antes da análise e o arquivo somente será usado no estágio de avaliação das métricas.

## Métricas

1. Acurácia de pares ordenados: percentual de pares decididos cuja ordem coincide com o oráculo.
2. Taxa de falsa certeza: percentual de pares decididos em desacordo com o oráculo.
3. Cobertura decisória: percentual de todos os pares sobre os quais a pipeline emite conclusão cronológica categórica.
4. Abstenção justificada: redução de cobertura da FPT quando faltam metadados necessários. A abstenção não é erro; é resultado de garantia epistêmica.

## Interpretação jurídica permitida

O experimento poderá sustentar que a qualidade da conclusão cronológica depende das informações de proveniência que acompanham o registro. Não poderá sustentar prevalência de falhas em perícias reais, validade ou invalidade geral de uma ferramenta forense, nem nulidade automática de provas digitais.

## Validação externa

O dataset aberto de Vanini et al. (Zenodo DOI 10.5281/zenodo.17122742) será usado em etapa separada, após seleção de artefatos e verificação da licença. O registro informa 17,2 GB de volume total e contém arquivos de histórico Chrome, cache e Windows Event Logs derivados de quatro imagens controladas. A validação externa verificará se a FPT consegue registrar os elementos de ancoragem temporal descritos pelos autores, sem alegar novo ground truth além do publicado no próprio estudo.

