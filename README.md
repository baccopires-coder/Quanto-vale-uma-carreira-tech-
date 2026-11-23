# Quanto vale uma carreira tech?

App em Streamlit que ajuda quem está começando (ou mudando de área) a descobrir quais profissões de tecnologia e dados
combinam com o seu perfil e quanto o mercado paga em cada uma. Os números vêm da pesquisa **State of Data Brasil 2025-2026**
(Data Hackers + Bain & Company, dados abertos no Kaggle).

Você marca as tecnologias que usa, conta um pouco do seu momento (experiência, nível, região e interesse) e recebe:

- as **5 áreas** que mais combinam com você, com salário médio e número de respondentes;
- um **diagnóstico em radar**: onde você está, onde está o profissional típico da área que você quer seguir e o que falta;
- **comparativos de salário** por nível de carreira, tempo de experiência e região do Brasil;
- um **painel geral** com filtros e **três hipóteses** do projeto explicadas em linguagem simples.

Sem chave de API, o app funciona com o formulário. Com a chave, uma entrevista por chat com IA ocupa o lugar do formulário.

## Arquivos

| Arquivo | Papel |
|---|---|
| `app.py` | Interface (Streamlit): abertura, formulário, resultado, painel geral e hipóteses, em três camadas que se sobrepõem ao rolar |
| `motor.py` | Carrega e trata o CSV; calcula ranking de áreas, diagnóstico do radar, salários e hipóteses (pandas, **sem IA**) |
| `ia.py` | Claude conduz a entrevista e **explica** números já calculados. Ele nunca vê os microdados |
| `requirements.txt` | Dependências |
| `.streamlit/config.toml` | Tema escuro fixo (este arquivo **vai** para o GitHub; o `secrets.toml` **não**) |
| `dados/` | CSV da pesquisa (o app lê daqui) |

## Rodar no seu computador (Windows, PowerShell)

```powershell
python -m venv venv312
.\venv312\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Para ativar a entrevista com IA localmente, crie `.streamlit/secrets.toml` (não vai para o GitHub) com:

```toml
ANTHROPIC_API_KEY = "sua-chave"
```

## Publicar no Streamlit Community Cloud

1. Envie o projeto para o GitHub (`git add`, `git commit`, `git push`).
2. Em share.streamlit.io, escolha **Create app**, o repositório, a branch `main` e o arquivo `app.py`.
3. Opcional: em **Advanced settings → Secrets**, cole `ANTHROPIC_API_KEY = "sua-chave"` para ativar a entrevista com IA.

Depois, cada `git push` atualiza o app sozinho (de alguns segundos a poucos minutos).

## Como os números são calculados

- **Salário = média.** Os gráficos, os cartões e a análise da IA usam a média (a soma dos salários dividida pelo número de
  respondentes). A única exceção é o cartão "Salário do meio (mediana)" no painel geral, mostrado como referência: se ele for
  bem menor que a média, poucos salários muito altos estão puxando a média para cima.
- **Faixas salariais.** A pesquisa pergunta uma faixa por mês (por exemplo, de R$ 8.001 a R$ 12.000). Usamos o valor do meio de cada faixa.
- **Respondentes.** Em todo o app, "respondentes" é o número de pessoas por trás de cada resultado. Um recorte só aparece quando
  tem **pelo menos 20 respondentes** (`MIN_N` em `motor.py`); abaixo disso, o app avisa que o resultado é só uma pista.
- **Afinidade.** Compara as tecnologias que você usa com as de cada profissão e considera o seu interesse. Nos cargos de gestão e
  liderança, que não respondem à parte técnica da pesquisa, considera interesse, nível e experiência. É um guia, não uma previsão.
- **Radar.** Cada ponta é uma área de conhecimento. Em tecnologias, 100% significa usar todas as que costumam ser usadas na
  profissão. As linhas mostram você, o profissional típico da profissão escolhida e a média de todos os respondentes.
- **Hipóteses.** H1 compara quanto cada fator (senioridade, profissão, experiência, região, porte da empresa) ajuda a explicar as
  diferenças de salário (medida técnica: η²). H2 compara o salário médio dos grupos de profissões em cada nível de carreira.
  H3 mostra as tecnologias mais usadas. As conclusões de cada uma são calculadas a partir dos dados, não escritas à mão.

## Privacidade e limites

- Só resultados somados são exibidos, nunca respostas individuais (LGPD). Gênero, cor/raça e deficiência não são usados.
- A IA recebe apenas números já calculados, nunca os microdados.
- Responderam pessoas voluntárias, a maioria do Sudeste; os dados são do fim de 2025 e do começo de 2026.
- A pesquisa não pergunta a cidade, então **não existe dado por capital**, só por região do Brasil.

## Histórico de melhorias recentes

- Página única em três camadas que se sobrepõem ao rolar, com navegação lateral.
- Formulário com botões de marcar (cada grupo numa caixa) e destaque claro das opções escolhidas.
- Botões de texto longo quebram em linhas e não são mais cortados no celular.
- Ao concluir, a página abre já no resultado, abaixo da barra fixa do Streamlit.
- Salários padronizados em **média**, com a nota sobre o "salário do meio"; "n=" trocado por "respondentes" em todo o app.
- Textos do painel e das hipóteses reescritos para quem está começando, com a conclusão de cada hipótese calculada dos dados.
- Gráficos ajustados para telas estreitas (rótulos quebrados em linhas, faixas salariais curtas).
