# Quanto vale uma carreira tech?

> Projeto final da turma 2026 do **Códigos do Amanhã** (EBANX em parceria com a HOW Bootcamps, trilha Análise de Dados · Big Data · IA).

App em Streamlit que ajuda quem está começando (ou mudando de área) a descobrir quais profissões de tecnologia e dados
combinam com o seu perfil e quanto o mercado paga em cada uma. Os números vêm da pesquisa **State of Data Brasil 2025-2026**
(Data Hackers + Bain & Company, dados abertos no Kaggle).

Você marca as tecnologias que usa, conta um pouco do seu momento (experiência, nível, região e interesse) e recebe:

- as **5 áreas** que mais combinam com você, com salário médio e número de respondentes;
- um **diagnóstico em radar**: onde você está, onde está o profissional típico da área que você quer seguir e o que falta;
- **comparativos de salário** por nível de carreira, tempo de experiência e região do Brasil;
- um **PDF para baixar** com o seu diagnóstico (perfil, áreas, radar, lacunas, análise e salários da profissão escolhida);
- um **painel geral** com filtros e **três hipóteses** do projeto explicadas em linguagem simples.

Sem chave de API, o app funciona com o formulário. Com a chave, uma entrevista por chat com IA ocupa o lugar do formulário.


---

## 1. Identificação

| | |
|---|---|
| **Título** | Quanto vale uma carreira tech? |
| **Integrantes** | Bacco Pires |
| **Programa** | Códigos do Amanhã 2026 (EBANX | HOW) |
| **App publicado** | <https://baccopires-coder-quanto-vale-uma-carreira-tech--app-dx6xhg.streamlit.app/> |
| **Versão inicial (dashboard)** | <https://projeto-salarios-por-senioridade-sjpzwqwtfs4vujbg7o9pgx.streamlit.app/> |

## 2. Problema, decisão que apoia e impacto

**Problema central.** Quem quer entrar ou migrar para tecnologia e dados enfrenta dezenas de cargos com nomes parecidos e
pouca informação confiável sobre o que cada um exige e paga. A pergunta do projeto é:
*dado o que uma pessoa já sabe, a que profissões de dados e tecnologia o seu perfil mais se parece, e o que o mercado paga nelas?*

**Perguntas norteadoras.**
- Como a remuneração varia conforme a área de atuação, a região e o tempo de experiência? Qual desses fatores pesa mais?
- A região onde a pessoa mora altera o salário típico, ou apenas a chance de chegar às faixas mais altas?
- No mesmo nível, quanto as posições de análise e BI se distanciam das de ciência, engenharia de dados e ML?

**Decisão que apoia e stakeholder.** Apoia a decisão de **qual trilha estudar, que expectativa salarial ter em cada fase e se vale buscar vagas fora da região**.
O beneficiário principal é a pessoa em início de carreira ou em transição para dados. O secundário são programas de formação, mentoria e profissionais de RH,
que ganham uma referência pública de faixas por cargo e nível.

**Impacto pretendido.** Reduzir o "chute" na escolha de área e de tecnologias a aprender: a pessoa sai com uma lista de lacunas
concretas (as tecnologias mais usadas na área-alvo que ela ainda não domina) e com uma referência salarial honesta, com o
número de respondentes por trás. O painel e o relatório são o meio; a mudança que se busca é uma decisão de carreira mais informada.

## 3. Hipóteses de trabalho

As três hipóteses são testadas no próprio app (seção "Hipóteses do projeto"). As conclusões mostradas lá são **calculadas dos dados**, não escritas à mão.

- **H1. Nível de carreira pesa mais no salário do que a região onde a pessoa mora.** Medida: η² (quanto cada fator, entre senioridade, profissão, experiência, região e porte da empresa, ajuda a explicar as diferenças de salário).
- **H2. Em cada nível de carreira, os grupos de profissões pagam de forma diferente.** Medida: salário médio de cada grupo de profissões em cada nível.
- **H3. Um conjunto pequeno de tecnologias concentra a maior parte do uso.** Medida: as 20 tecnologias e práticas mais usadas entre os respondentes técnicos.

Indícios da análise exploratória inicial (faixa salarial convertida no ponto médio), que o app agora testa com a base completa:

- **H1:** medianas de R$ 5.000 (Júnior), R$ 7.000 (Pleno), R$ 10.000 (Sênior) e R$ 18.000 (Especialista/Staff+ e Gestão), contra R$ 10.000 em todas as regiões.
- **H2:** entre Seniores, mediana de R$ 10.000 para Analista de Dados e de BI e R$ 14.000 para Cientista e Engenheiro de Dados.

Esta é uma leitura exploratória: mostra o que aparece nos dados, **não prova causa**.

## 4. Dados

### Fonte

- **State of Data Brasil 2025-2026**, pesquisa anual da comunidade Data Hackers com a Bain & Company: <https://www.bain.com/pt-br/insights/state-of-data-2025/>
- Dados abertos no Kaggle (organização Data Hackers): _[colar aqui o link direto do dataset 2025-2026]_
- Arquivo usado: CSV da pesquisa, guardado em `dados/`.
- Divulgação dos microdados: Data Hackers News.
- Mapa dos estados (painel geral): GeoJSON do repositório `click_that_hood`, baixado da internet.

### Viabilidade técnica

Os dados já estão acessíveis em um arquivo CSV público. Não há raspagem nem API de terceiros para os dados.
A única chamada externa é à API da Anthropic (opcional, para a camada de IA).

### Ciclo de vida dos dados

| Etapa | O que acontece no projeto |
|---|---|
| **Geração** | Respostas voluntárias de profissionais à pesquisa State of Data (fim de 2025 e começo de 2026) |
| **Ingestão** | `motor.py` lê só as colunas necessárias do CSV com pandas |
| **Armazenamento** | CSV versionado na pasta `dados/` do repositório |
| **Transformação** | Filtro de quem vive no Brasil e trabalha como CLT, PJ, servidor ou freelancer; padronização de cargos, grupos e portes; faixa salarial convertida no valor do meio da faixa |
| **Disponibilização** | App Streamlit publicado no Streamlit Community Cloud |

### Principais métricas

Salário (média por faixa, ponto médio), senioridade, tempo de experiência, região, porte da empresa, tipo de contrato,
profissão e as tecnologias/práticas de cada respondente (linguagens, bancos de dados, nuvem, BI, fontes de dados e IA).

## 5. Como os números são calculados

- **Salário = média.** Os gráficos, os cartões e a análise da IA usam a média (a soma dos salários dividida pelo número de
  respondentes). A única exceção é o cartão "Salário do meio (mediana)" no painel geral, mostrado como referência: se ele for
  bem menor que a média, poucos salários muito altos estão puxando a média para cima.
- **Faixas salariais.** A pesquisa pergunta uma faixa por mês (por exemplo, de R$ 8.001 a R$ 12.000). Usamos o valor do meio de cada faixa.
- **Respondentes.** Em todo o app, "respondentes" é o número de pessoas por trás de cada resultado. Um recorte só aparece quando
  tem **pelo menos 20 respondentes** (`MIN_N` em `motor.py`); abaixo disso, o app avisa que o resultado é só uma pista.
- **Afinidade.** Compara as tecnologias que você usa com as de cada profissão e considera o seu interesse. Nos cargos de gestão e
  liderança, que não respondem à parte técnica da pesquisa, considera interesse, nível e experiência. É um guia, não uma previsão. (Detalhes na seção 7.)
- **Radar.** Cada ponta é uma área de conhecimento. Em tecnologias, 100% significa usar todas as que costumam ser usadas na
  profissão. As linhas mostram você, o profissional típico da profissão escolhida e a média de todos os respondentes.

## 6. Arquivos

| Arquivo | Papel |
|---|---|
| `app.py` | Interface (Streamlit): abertura, formulário, resultado, painel geral e hipóteses, em três camadas que se sobrepõem ao rolar |
| `motor.py` | Carrega e trata o CSV; calcula ranking de áreas, diagnóstico do radar, salários e hipóteses (pandas, **sem IA**) |
| `relatorio.py` | Gera o PDF do diagnóstico (reportlab, gráficos desenhados direto no PDF; só formata números já calculados) |
| `ia.py` | Claude conduz a entrevista e **explica** números já calculados. Ele nunca vê os microdados |
| `requirements.txt` | Dependências |
| `.streamlit/config.toml` | Tema escuro fixo (este arquivo **vai** para o GitHub; o `secrets.toml` **não**) |
| `dados/` | CSV da pesquisa (o app lê daqui) |

## 7. Uso de IA no projeto

O projeto separa com clareza **o que é cálculo** do que é **linguagem**.

| Parte | Quem faz | Tipo |
|---|---|---|
| Ranking de áreas, salários, radar, hipóteses | `motor.py` (pandas, regras estatísticas determinísticas) | Sem IA. Não há modelo de machine learning treinado |
| Entrevista por chat e tradução do texto livre em perfil | Claude, via `ia.py` | IA generativa |
| Explicação em texto do resultado | Claude, via `ia.py` | IA generativa |
| PDF do diagnóstico | `relatorio.py` (reportlab), só formata números já calculados e o texto da análise | Sem IA |
| Interpretação final, escolha da área, decisão de carreira | A pessoa usuária | Humano |

### Por que a IA faz as análises que faz

**1. Ela não calcula, ela traduz.** O erro mais comum de um modelo de linguagem com dados é "chutar" números plausíveis.
Aqui isso é impedido pelo desenho: o `motor.py` calcula tudo e entrega um JSON pronto; o Claude só transforma esse JSON em texto.
O prompt de análise manda usar **somente os números do JSON**, não citar profissões que não estejam nele e tratar o salário como
referência, não promessa. Se a chamada à API falhar, `explicar_local()` gera uma versão do texto sem IA, com os mesmos números.

**2. Na entrevista, ele faz o trabalho em que é melhor que um formulário: entender texto livre.** A pessoa escreve "Postgres",
"Power BI" ou "Copilot" e o modelo mapeia para o rótulo exato do catálogo da pesquisa ("PostgreSQL", "Microsoft PowerBI",
"Uso soluções do tipo Copilot"). Isso é feito por *tool use*: o Claude chama a ferramenta `registrar_perfil`, cujo esquema aceita
**apenas valores do catálogo** (`enum`). Depois, `validar_perfil()` confere tudo de novo no código e descarta o que não existir.
Assim a IA não consegue inventar uma tecnologia, um nível ou uma região.

**3. A entrevista é curta e não induz.** Uma pergunta por vez, no máximo 6, sem falar de salário nem recomendar nada antes do
resultado (para não criar ancoragem). Estados viram macrorregião; cidade e endereço não são pedidos.

**4. O tom é calibrado para quem está começando.** A análise tem de 350 a 500 palavras, sem siglas sem explicação e sem emojis,
sempre diz "média" e "respondentes", e cobre cinco pontos: áreas mais aderentes, caminhos possíveis, remuneração, o que falta
aprender e uma nota metodológica curta com as limitações.

**5. Há travas de segurança e de custo.** O texto digitado pela pessoa é tratado como dado, não como instrução. Gênero, cor/raça,
deficiência, idade, nome e documentos são ignorados mesmo que a pessoa informe. Há limite de 25 chamadas à IA por sessão.

### De onde vem a afinidade (o que a IA explica)

Nas profissões técnicas, a afinidade combina duas medidas entre o seu perfil e o perfil de uso de cada profissão, mais um bônus de interesse:

```
afinidade = 0,85 × (0,5 × similaridade + 0,5 × destaque) + 0,15 × interesse
```

- **Similaridade (cosseno):** o quanto o seu conjunto de tecnologias se parece com o da profissão.
- **Destaque (lift):** compara com a média geral dos respondentes, para que tecnologias que *todo mundo* usa (como SQL ou Excel) não empurrem todas as profissões para o topo.
- **Interesse:** bônus quando a profissão pertence à área que a pessoa disse preferir.

Cargos de gestão não respondem à parte técnica da pesquisa, então usam interesse, nível e experiência, e ficam **limitados a 2 entre as 5 áreas**
(a menos que a pessoa tenha interesse em liderança ou já esteja nela). Isso corrige um viés que aparecia antes: perfis seniores
pontuavam alto em todos os cargos de gestão e dominavam o topo.

## 8. Escolhas de construção do front-end

- **Streamlit.** O motor de cálculo já é Python/pandas, e o Streamlit permite construir a interface na mesma linguagem, sem uma
  segunda stack em JavaScript, e publicar de graça no Community Cloud com `git push`. Para um projeto de dados feito por quem
  está em transição para a área, isso mantém o foco na análise e não na infraestrutura.
- **Plotly.** Gráficos interativos com *hover* mostrando média e número de respondentes, para que a base de cada barra esteja sempre à vista.
- **Uma página em três camadas.** A jornada é narrativa: *descobrir minha área* → *painel geral* → *hipóteses do projeto*. As seções
  se sobrepõem ao rolar, com navegação lateral. No celular (até 768 px) as camadas viram rolagem normal, e a animação respeita
  `prefers-reduced-motion`. A sobreposição usa CSS e um pequeno script injetado, algo que o Streamlit não oferece nativamente.
- **Formulário com botões de marcar, e não listas suspensas.** São centenas de tecnologias; botões agrupados por categoria (cada grupo numa caixa)
  deixam tudo visível de uma vez, com destaque claro do que foi escolhido. Textos longos quebram em linhas para não serem cortados no celular.
- **Cor com significado.** Cada família de cor identifica um grupo (profissões, tecnologias, filtros) e aparece igual em botões,
  cartões e gráficos. Duas cores fixas: **teal = você** e **âmbar = o que falta / alvo**. Fundo azul-petróleo escuro, sem brilho ou *glow*,
  com tipografia Fraunces (títulos) e Figtree (texto).
- **Linguagem para iniciantes.** "Respondentes" em vez de "n=", "média" explicada, hipóteses descritas como perguntas e a medida técnica (η²) escondida num detalhe opcional.
- **PDF do diagnóstico.** Botão "Baixar meu diagnóstico em PDF" no topo do resultado, que segue a profissão selecionada no radar. O `relatorio.py` usa reportlab e desenha os gráficos direto no PDF, sem depender de imagens do navegador, e não faz nenhum cálculo novo.
- **Funciona sem IA.** O formulário é a base; o chat com IA é um complemento que só aparece com a chave configurada.

## 9. Desafios, ética e privacidade

### Desafios e limitações

- **Amostra voluntária e autodeclarada**, concentrada no Sudeste (cerca de 62% das respostas; o Norte tem poucas): não representa todo o mercado.
- **Salário em faixas:** usamos o ponto médio, o que suaviza extremos.
- **Sem dado por cidade:** a pesquisa só informa macrorregião, então **não existe dado por capital**.
- **Dados de fim de 2025 e começo de 2026**, sem atualização contínua.
- **Cargos de gestão** não respondem ao bloco de ferramentas técnicas, então a afinidade deles é menos precisa.
- **Recortes pequenos:** ao cruzar cargo, nível e região, muitos grupos ficam com poucas respostas. Só aparecem com pelo menos 20 respondentes; abaixo disso o app sinaliza que é apenas uma pista.
- **Dados ausentes:** parte dos respondentes não informou salário, e gestores não têm cargo técnico e nível preenchidos como os demais.
- **Vínculos pouco comparáveis:** CLT, PJ, servidor público e freelancer têm lógicas salariais distintas.
- **Erros de digitação na base** (uma faixa salarial e uma faixa de número de funcionários escritas de forma inconsistente) são corrigidos no tratamento.

### Plano de verificação e vieses

- Toda explicação da IA é conferível contra os números calculados pelo `motor.py`; a IA não acessa os microdados.
- O limite de 20 respondentes evita conclusões sobre grupos pequenos e reduz o risco de superinterpretar ruído.
- As hipóteses são apresentadas como leitura exploratória, sem afirmar causalidade, para evitar viés de confirmação.
- A entrevista não cita salário antes do resultado, para evitar ancoragem.
- O texto avisa que o salário é referência, não promessa.

### Privacidade e LGPD

- Os microdados são públicos e foram divulgados sem campos de identificação direta, como nome e e-mail. Mesmo assim, o risco de reidentificação é um ponto de atenção:
  o app exibe **apenas resultados somados**, nunca respostas individuais, e não cruza a base com nenhuma outra base pessoal nem tenta reidentificar respondentes.
- A fonte é citada em todos os produtos do projeto, e a licença do dataset deve ser respeitada.
- **Gênero, cor/raça e deficiência não são usados** em nenhum cálculo.
- O perfil da pessoa usuária fica apenas na sessão do navegador e não é gravado em banco de dados. O PDF é gerado na hora, para quem pediu, e também não é armazenado pelo app.
- No modo com IA, o texto digitado no chat é enviado à API da Anthropic para gerar as respostas; por isso a entrevista pede só tecnologias, experiência, nível, região e interesse, e ignora nome, idade e documentos. A IA nunca recebe os microdados da pesquisa.

## 10. Cronograma e distribuição de tarefas

Todas as etapas são compartilhadas pela equipe, e cada entrega é revisada por outra pessoa.

| Fase | Entregas | Quem |
|---|---|---|
| Coleta / Ingestão | CSV em `dados/`, leitura no `motor.py` | Toda a equipe |
| Tratamento / Transformação | Limpeza, padronização de cargos, faixas e portes | Toda a equipe |
| Análise / Modelagem | Ranking de afinidade, radar, hipóteses H1-H3 | Toda a equipe |
| Interface e IA | `app.py`, `ia.py`, tema e responsividade | Toda a equipe |
| Documentação e Apresentação | README, pré-projeto, apresentação final | Toda a equipe |

## 11. Rodar no seu computador (Windows, PowerShell)

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

Opcionalmente, `ANTHROPIC_MODEL` troca o modelo usado (o padrão está em `ia.py`).

## 12. Publicar no Streamlit Community Cloud

1. Envie o projeto para o GitHub (`git add`, `git commit`, `git push`).
2. Em share.streamlit.io, escolha **Create app**, o repositório, a branch `main` e o arquivo `app.py`.
3. Opcional: em **Advanced settings → Secrets**, cole `ANTHROPIC_API_KEY = "sua-chave"` para ativar a entrevista com IA.

Depois, cada `git push` atualiza o app sozinho (de alguns segundos a poucos minutos).

## 13. Histórico de melhorias

- Página única em três camadas que se sobrepõem ao rolar, com navegação lateral.
- Formulário com botões de marcar (cada grupo numa caixa) e destaque claro das opções escolhidas.
- Botões de texto longo quebram em linhas e não são mais cortados no celular.
- Ao concluir, a página abre já no resultado, abaixo da barra fixa do Streamlit.
- Salários padronizados em **média**, com a nota sobre o "salário do meio"; "n=" trocado por "respondentes" em todo o app.
- Textos do painel e das hipóteses reescritos para quem está começando, com a conclusão de cada hipótese calculada dos dados.
- Gráficos ajustados para telas estreitas (rótulos quebrados em linhas, faixas salariais curtas).
- **Origem:** o projeto começou como um dashboard de salários por senioridade, região e cargo (versão inicial, link na seção 1) e evoluiu para o recomendador de carreira com diagnóstico e entrevista por IA.
- **Baixar meu diagnóstico em PDF** no topo do resultado: o arquivo segue a profissão selecionada no diagnóstico e inclui a análise personalizada.

## 14. Autoria

- Bacco Pires

## 15. Fontes e créditos

- Dados: State of Data Brazil 2025-2026, Data Hackers (Kaggle)
- Divulgação dos microdados: Data Hackers News
- Relatório: State of Data Brazil 2025/2026, Data Hackers + Bain & Company
- Mapa dos estados: GeoJSON do repositório `click_that_hood`

Os direitos sobre a pesquisa e seus dados pertencem aos seus autores (Data Hackers e Bain & Company). Este projeto é uma análise independente, feita para fins educacionais.
