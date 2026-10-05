# Benchmark de Proveniência Temporal

Experimento controlado para comparar uma ordenação ingênua de logs com uma pipeline que usa manifesto de proveniência temporal.

## O que este artefato testa

O benchmark não avalia uma ferramenta policial nem afirma frequência de erros em investigações reais. Ele testa uma proposição limitada: quando logs heterogêneos não trazem, de forma suficiente, informações sobre fuso, offset e semântica, uma pipeline deve reduzir ou suspender afirmações cronológicas categóricas.

## Desenho fatorial

24 cenários: 3 perfis de relógio x 2 formatos temporais x 2 atrasos de fila x 2 níveis de proveniência.

- Perfis de relógio: sincronizado; API com +300 segundos; worker com -120 segundos.
- Formatos: UTC explícito; horário local sem offset no registro bruto.
- Atraso de fila: 0 ou 90 segundos.
- Proveniência: completa ou incompleta.

Cada cenário contém 12 transações correlacionadas e seis eventos por transação: cliente, API, fila, worker, banco de dados e coletor. A sequência-oráculo é separada dos logs de análise.

## Execução local

Requisito: Python 3.11 ou superior, apenas biblioteca padrão.

```bash
python3 src/generate_benchmark.py
python3 src/analyze.py
```

Os resultados ficam em `results/`.

## Reprodutibilidade

- Dados sintéticos e determinísticos.
- O oráculo é gerado separadamente e não é usado pelas pipelines de análise.
- O manifesto identifica versão, fatores, semântica e, nos cenários completos, parâmetros de normalização.
- `analyze.py` gera métricas por cenário e um resumo agregável para o artigo.

## Métricas

- **Acurácia de pares ordenados:** pares de eventos cuja ordem coincide com o oráculo.
- **Taxa de falsa certeza:** pares afirmados como ordenáveis pela pipeline, mas incompatíveis com o oráculo.
- **Cobertura decisória:** proporção de pares sobre os quais a pipeline emite conclusão categórica.
- **Abstenção justificada:** pares sobre os quais a pipeline de proveniência se recusa a concluir por ausência de metadados necessários.

## Fase de validação externa

O conjunto aberto de Vanini et al. é complementar, não substitui este benchmark, pois contém artefatos de quatro imagens Windows e totaliza 17,2 GB no registro Zenodo. Antes de reutilizá-lo, serão selecionados apenas artefatos necessários, verificada a licença e documentado o adaptador de leitura.

