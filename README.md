# quanto-vale-uma-carreira-tech — Quanto vale uma carreira tech? (State of Data 2025-2026)

Projeto **novo e independente** (não altera o repositório antigo `salarios_por_senioridade`).
O app entrevista a pessoa (com IA), recomenda áreas tech e de dados, mostra salários por cargo, senioridade,
experiência e macrorregião, e aponta habilidades a desenvolver.

| Arquivo | Papel |
|---|---|
| `motor.py` | Carrega/trata o CSV; ranking de áreas, lacunas de habilidades, salários e o diagnóstico do radar (pandas, **sem IA**) |
| `ia.py` | Claude conduz a entrevista e **explica** números já calculados (não vê microdados) |
| `app.py` | Interface em página única, com três camadas que se sobrepõem ao rolar: Descobrir minha área (com radar de diagnóstico) · Painel geral · Hipóteses H1–H3 |
| `.streamlit/config.toml` | Tema escuro fixo, para o visual ficar legível em qualquer navegador (este arquivo **vai** para o GitHub; o `secrets.toml` não) |

Sem chave de API o app continua funcionando (formulário no lugar do chat).

## 1. Criar o projeto novo (sem tocar no antigo)
```bash
# fora da pasta do projeto antigo
mkdir quanto-vale-uma-carreira-tech && cd quanto-vale-uma-carreira-tech
# extraia aqui o conteúdo deste zip
cp "../salarios_por_senioridade/dados/"*.csv dados/            # o mesmo CSV que você já usa
cp ../salarios_por_senioridade/dados/brasil_estados.geojson dados/   # opcional