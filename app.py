import html as _html
import colorsys
import re
import json
import unicodedata
import urllib.request

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ia
import motor
import relatorio
from motor import MIN_N, ORDEM_EXP, ORDEM_NIVEL

st.set_page_config(page_title="Quanto vale uma carreira tech?", page_icon="📊", layout="wide")

# ----------------------------------------------------------------------
# Paleta: fundo azul-petróleo escuro, com teal, violeta e âmbar como acentos (sem brilho/glow)
# ----------------------------------------------------------------------
BG = "#151B2D"
AZUL, AZUL_CLARO, ROXO, ROXO_ESCURO = "#5B9BF6", "#8DB8F8", "#9A7CF2", "#6247C9"
AMBAR, TEAL, ROSA = "#F2A93B", "#35D0BA", "#F28DB8"


def hexhsl(h, s=60, l=62):
    """Cor em HSL (matiz 0-360, saturação e luminosidade em %) devolvida como #rrggbb."""
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, l / 100, s / 100)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def deslize(base_h, j, n, amplitude=28):
    """Matiz do item j de n: a família do grupo com um deslize suave de matiz ao longo da lista."""
    return base_h + ((j / (n - 1) - 0.5) * amplitude if n > 1 else 0)


def rampa(n, h0=262, h1=150, s=56, l=63):
    """Sequência ordenada (baixo -> alto) com transição contínua de matiz, para categorias com ordem."""
    return [hexhsl(h0 + (h1 - h0) * (i / (n - 1) if n > 1 else 0), s, l) for i in range(n)]


# A ideia da página inteira: cada FAMÍLIA de cor identifica um grupo e aparece igual em botões, cartões e gráficos;
# dentro do grupo o tom desliza suavemente. Cores fixas de significado: teal = você, âmbar = o que falta/alvo.
ESCALA = [[0.0, hexhsl(218, 48, 34)], [0.5, hexhsl(196, 52, 46)], [1.0, hexhsl(168, 58, 60)]]  # azul -> teal
CORES_CAT = [hexhsl(h, 58, 64) for h in (212, 172, 255, 38, 350, 140, 300)] + ["#94A3B8"]
PAR = [AZUL, ROXO]  # Brasil x sua região
TOP_AREAS = 5  # quantas áreas priorizar nas telas que seguem o perfil da pessoa

# Grupos de tecnologias (formulário, lacunas, H3), na ordem de motor.BLOCOS
MATIZES = [172, 212, 255, 38, 140, 280, 305]
MATIZ_CAT = dict(zip(motor.BLOCOS.values(), MATIZES))
MATIZ_EIXO = {eixo: MATIZ_CAT[cat] for cat, eixo in motor.ROTULO_EIXO.items()}
MATIZ_EIXO.update({"Experiência": 195, "Senioridade": 285})

# Grupos de profissões (cartões do ranking, gráficos por profissão)
MATIZ_GRUPO = {
    "Análise/BI e Negócios": 38,
    "Engenharia e Arquitetura de Dados": 212,
    "Ciência de Dados, ML/IA e Pesquisa": 255,
    "Engenharia de Software e Outras": 172,
    "Produto e Suporte": 345,
    "Gestão e Liderança": 140,
}
GRUPO_COR = {g: hexhsl(h, 58, 64) for g, h in MATIZ_GRUPO.items()}


def _matiz_cargos():
    por_grupo = {}
    for cargo in motor.CARGOS:
        por_grupo.setdefault(motor.GRUPO[cargo], []).append(cargo)
    return {
        cargo: deslize(MATIZ_GRUPO[g], j, len(cs))
        for g, cs in por_grupo.items()
        for j, cargo in enumerate(cs)
    }


MATIZ_CARGO = _matiz_cargos()
COR_CARGO = {c: hexhsl(h, 58, 64) for c, h in MATIZ_CARGO.items()}
COR_NIVEL = dict(zip(ORDEM_NIVEL, rampa(len(ORDEM_NIVEL))))

ROTULO_CONTRATO = {
    "Empreendedor ou Empregado (CNPJ)": "PJ / CNPJ",
    "Empregado (CLT)": "CLT",
    "Servidor Público": "Servidor público",
    "Freelancer": "Freelancer",
}

UF_REGIAO = {
    **dict.fromkeys(["AC", "AP", "AM", "PA", "RO", "RR", "TO"], "Norte"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Nordeste"),
    **dict.fromkeys(["DF", "GO", "MT", "MS"], "Centro-oeste"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Sudeste"),
    **dict.fromkeys(["PR", "RS", "SC"], "Sul"),
}

# Filtros do painel geral: uma família por filtro
FILTROS = [
    ("Região", "regiao", motor.REGIOES, None),
    ("Senioridade", "senioridade", ORDEM_NIVEL, None),
    ("Tipo de contrato", "contrato", None, lambda o: ROTULO_CONTRATO.get(o, o)),
    ("Porte da empresa", "tamanho_empresa", motor.ORDEM_PORTE, None),
]
MATIZ_FILTRO = {"regiao": 172, "senioridade": 255, "contrato": 38, "tamanho_empresa": 212}

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Figtree:wght@400;500;600&display=swap');
.stApp { background: __BG__; }
/* texto corrido em cinza-azulado suave (não branco puro) e destaques um tom acima */
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li { color: #C9D1E8; }
[data-testid="stMarkdownContainer"] strong { color: #E6EBF8; }
[data-testid="stCaptionContainer"] p { color: #9FB0D6; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 { color: #E6EBF8; }
.st-key-resultado { scroll-margin-top: 4.5rem; }
.ok { background: hsla(172,45%,50%,.09); border: 1px solid hsla(172,50%,62%,.32); border-radius: 12px;
  padding: 12px 16px; color: #C9D1E8; font-size: .95rem; line-height: 1.5; margin-top: 2px; }
.ok b { color: hsl(172,60%,80%); }
html, body, .stApp, [data-testid="stMarkdownContainer"], .stApp button, .stApp input, .stApp textarea, .stApp label {
  font-family: 'Figtree', system-ui, sans-serif; -webkit-text-size-adjust: 100%; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 { font-family: 'Fraunces', Georgia, serif; font-weight: 600;
  letter-spacing: -.01em; }
[data-testid="stMain"] { scroll-behavior: smooth; }
[data-testid="stMainBlockContainer"] { max-width: 100% !important; padding: 0 !important; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { gap: 0 !important; }
.st-key-secao_1, .st-key-secao_2, .st-key-secao_3 {
  position: relative; min-height: 100vh; min-height: 100svh; padding: 3.5rem max(clamp(1rem, 5vw, 5rem), calc((100% - 1040px) / 2)) 4rem; }
.st-key-secao_1 { background: __BG__; }
.st-key-secao_2 { background: hsl(226,27%,14.5%); border-top: 1px solid rgba(255,255,255,.1); box-shadow: 0 -20px 50px rgba(0,0,0,.4); }
.st-key-secao_3 { background: hsl(206,27%,13.5%); border-top: 1px solid rgba(255,255,255,.1); box-shadow: 0 -20px 50px rgba(0,0,0,.4); }
.st-key-secao_1::after, .st-key-secao_2::after { content: ""; position: absolute; inset: 0;
  background: #080B15; opacity: var(--dim, 0); pointer-events: none; z-index: 50; }

.kicker { font-size: .98rem; color: #9FB0D6; margin: 0 0 .6rem 0; }
h1.titulo { font-family: 'Fraunces', Georgia, serif; font-weight: 600; font-size: clamp(1.9rem, 5.4vw, 3.2rem);
  line-height: 1.1; color: #E6EBF8; margin: 0 0 .4rem 0; padding: 0; }
h1.titulo span.sub { display: block; font-family: 'Figtree', sans-serif; font-size: clamp(1rem, 2.6vw, 1.15rem);
  font-weight: 400; color: #B4C0E4; margin-top: .9rem; max-width: 60ch; line-height: 1.55; }
h2.secao { font-family: 'Fraunces', Georgia, serif; font-weight: 600; font-size: clamp(1.5rem, 4vw, 2.2rem);
  margin: 0 0 .4rem 0; padding: 0; line-height: 1.15; color: #E6EBF8; }
p.secao-sub { color: #B4C0E4; margin: 0 0 1.4rem 0; max-width: 70ch; line-height: 1.55; }

.ct { font-family: 'Fraunces', Georgia, serif; font-weight: 600; font-size: 1.1rem; color: #E6EBF8;
  margin: 1.3rem 0 .2rem 0; line-height: 1.25; }

[data-testid="stMetric"] { background: #1C2238; border: 1px solid rgba(255,255,255,.09);
  border-radius: 12px; padding: 14px 18px; min-height: 108px; overflow: hidden; }
[data-testid="stMetricLabel"] p { font-size: .9rem; color: #9FB0D6; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { font-family: 'Fraunces', Georgia, serif;
  font-weight: 600; white-space: normal !important; overflow: visible !important; line-height: 1.2 !important;
  overflow-wrap: anywhere !important; }
.st-key-kpi_1 [data-testid="stMetric"] { background: hsla(255,45%,60%,.10); border-color: hsla(255,55%,72%,.35); }
.st-key-kpi_2 [data-testid="stMetric"] { background: hsla(172,45%,50%,.09); border-color: hsla(172,50%,62%,.35); }
.st-key-kpi_3 [data-testid="stMetric"] { background: hsla(212,50%,55%,.09); border-color: hsla(212,55%,66%,.35); }
.st-key-kpi_4 [data-testid="stMetric"] { background: hsla(38,60%,52%,.09); border-color: hsla(38,70%,62%,.35); }
[data-testid="stSidebar"] { background: #181E33; border-right: 1px solid rgba(255,255,255,.07); }

button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"],
button[data-testid="stBaseButton-secondary"], button[data-testid="stFormSubmitButton"] { border-radius: 999px !important; }
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: hsla(172,55%,58%,.16) !important; border: 1px solid hsla(172,60%,62%,.6) !important;
  min-height: 3.4rem; transition: background .15s, border-color .15s; }
button[data-testid="stBaseButton-primary"] p, button[data-testid="stBaseButton-primaryFormSubmit"] p {
  color: hsl(172,60%,84%) !important; font-weight: 600; font-size: 1.05rem; }
button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
  background: hsl(172,62%,64%) !important; border-color: hsl(172,62%,64%) !important; }
button[data-testid="stBaseButton-primary"]:hover p, button[data-testid="stBaseButton-primaryFormSubmit"]:hover p {
  color: __BG__ !important; }

[data-testid="stButtonGroup"] { flex-wrap: wrap !important; gap: .5rem !important; }
[data-testid="stButtonGroup"] > div { flex-wrap: wrap !important; }
button[data-testid^="stBaseButton-pills"], button[data-variant="pills"] { border-radius: 999px !important; white-space: normal !important;
  min-height: 38px; height: auto !important; max-width: 100%; overflow: visible !important; line-height: 1.3;
  font-size: .92rem; padding: 8px 16px !important; color: #D5DCF0; background: var(--pbg, rgba(255,255,255,.04));
  border: 1px solid var(--pbd, rgba(255,255,255,.16)) !important;
  transition: background .15s, border-color .15s, filter .15s; }
button[data-variant="pills"] p, button[data-testid^="stBaseButton-pills"] p { white-space: normal !important; overflow: visible !important;
  text-align: center; text-wrap: balance; margin: 0; }
[data-testid="stButtonGroup"], [data-testid="stButtonGroup"] > div { height: auto !important; max-width: 100%; }
@media (hover: hover) { button[data-variant="pills"]:hover, button[data-testid^="stBaseButton-pills"]:hover { filter: brightness(1.35); } }
button[data-variant="pills"], button[data-testid^="stBaseButton-pills"] { -webkit-tap-highlight-color: transparent; }
button[data-variant="pills"]:focus:not(:focus-visible) { outline: none; box-shadow: none; }
button[data-variant="pills"]:is([data-testid="stBaseButton-pillsActive"], [data-selected="true"], [aria-pressed="true"], [aria-checked="true"]), button[data-testid="stBaseButton-pillsActive"] {
  background: var(--psel, __TEAL__) !important; border-color: var(--psel, __TEAL__) !important; font-weight: 600; }
button[data-variant="pills"]:is([data-testid="stBaseButton-pillsActive"], [data-selected="true"], [aria-pressed="true"], [aria-checked="true"]) p, button[data-testid="stBaseButton-pillsActive"] p { color: __BG__ !important; }
span[data-baseweb="tag"] { background-color: __ROXO_ESCURO__ !important; }
.st-key-painel_filtros { background: #1C2238; border-radius: 12px; padding: .5rem .8rem; }

.dica { border: 1px solid rgba(242,169,59,.3); background: rgba(242,169,59,.08); padding: .75rem 1rem;
  border-radius: 10px; color: #F3E3BF; font-size: .95rem; margin: 0 0 .8rem 0; line-height: 1.5; }
.grupo { font-weight: 600; font-size: 1rem; color: #CFD8F2; margin: 1.5rem 0 .55rem 0; }
.pergunta { font-size: .95rem; font-weight: 500; color: #B4C0E4; margin: .9rem 0 .4rem 0; }
[class*="st-key-grupo_"][data-testid="stVerticalBlock"], [class*="st-key-grupo_"] > [data-testid="stVerticalBlock"] {
  flex-direction: row !important; flex-wrap: wrap !important; gap: .5rem !important; }
[class*="st-key-grupo_"] [data-testid="stElementContainer"] { width: auto !important; flex: 0 1 auto !important; max-width: 100%; }
[class*="st-key-grupo_"] [data-testid="stButtonGroup"] { flex-wrap: nowrap !important; }

.rk-lista { display: flex; flex-direction: column; gap: 10px; margin: .6rem 0 1rem 0; }
.rk { display: grid; grid-template-columns: 2.4rem 1fr auto; gap: 16px; align-items: center;
  background: var(--t, #1C2238); border: 1px solid var(--b, rgba(255,255,255,.09)); border-radius: 12px; padding: 16px 20px; }
.rk.topo { border-color: var(--c, __TEAL__); }
.rk .pos { font-family: 'Fraunces', Georgia, serif; font-size: 1.8rem; font-weight: 600; color: var(--c, #7F8DB5); text-align: center; }
.rk .nome { font-weight: 600; font-size: 1.1rem; color: #E6EBF8; line-height: 1.25; }
.rk .meta { color: #9FB0D6; font-size: .88rem; margin-top: 2px; }
.rk .barra { height: 6px; border-radius: 999px; background: rgba(255,255,255,.09); margin-top: 10px; overflow: hidden; }
.rk .barra i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--c2, __AZUL__), var(--c, __TEAL__)); }
.rk .fim { text-align: right; min-width: 11rem; }
.rk .pct { font-family: 'Fraunces', Georgia, serif; font-size: 2rem; font-weight: 600; color: #E6EBF8; line-height: 1; }
.rk .sal { color: #9FB0D6; font-size: .84rem; margin-top: 4px; line-height: 1.35; }
.rk .sal + .sal { margin-top: 0; }

.gap { background: var(--t, #1C2238); border: 1px solid var(--b, rgba(255,255,255,.09)); border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; }
.gap .t { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; align-items: baseline; }
.gap .t b { color: #E6EBF8; font-size: 1.05rem; font-family: 'Fraunces', Georgia, serif; font-weight: 600; }
.gap .v { color: __TEAL__; font-weight: 600; font-size: .92rem; }
.gap .a { color: __AMBAR__; font-weight: 600; margin-left: 12px; font-size: .92rem; }
.gap .bar { position: relative; height: 6px; border-radius: 999px; background: rgba(255,255,255,.1); margin: 12px 0 10px; }
.gap .bar i { position: absolute; left: 0; top: 0; bottom: 0; background: __TEAL__; border-radius: 999px; }
.gap .bar u { position: absolute; top: -4px; bottom: -4px; width: 3px; border-radius: 2px; background: __AMBAR__; }
.gap p { margin: 0; color: #B4C0E4; font-size: .92rem; line-height: 1.45; }

#carreira-nav { position: fixed; right: 18px; top: 50%; transform: translateY(-50%); z-index: 99999;
  display: flex; flex-direction: column; gap: 14px; padding: 12px 8px; border-radius: 999px;
  background: rgba(28,34,56,.92); border: 1px solid rgba(255,255,255,.14); box-shadow: 0 6px 24px rgba(0,0,0,.35); }
#carreira-nav button { width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--c, #9FB0D6);
  background: transparent; padding: 0; cursor: pointer; position: relative; transition: transform .2s, background .2s; }
#carreira-nav button.on { background: var(--c, __TEAL__); transform: scale(1.3); }
#carreira-nav button:nth-child(1) { --c: hsl(172,62%,60%); }
#carreira-nav button:nth-child(2) { --c: hsl(212,80%,70%); }
#carreira-nav button:nth-child(3) { --c: hsl(255,75%,76%); }
#carreira-nav button::before { content: attr(data-nome); position: absolute; right: 24px; top: 50%;
  transform: translateY(-50%); white-space: nowrap; background: #1C2238; border: 1px solid rgba(255,255,255,.14);
  color: #CBD3EA; padding: 5px 12px; border-radius: 8px; font-size: 13px; opacity: 0; pointer-events: none; transition: opacity .15s; }
#carreira-nav button:hover::before { opacity: 1; }

/* texto corrido mais confortável */
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li { line-height: 1.62; }
.st-key-analise { max-width: 74ch; }
.st-key-analise [data-testid="stMarkdownContainer"] h3 { margin-top: 1.5rem; font-size: 1.3rem; }
.st-key-analise [data-testid="stMarkdownContainer"] strong { color: #E6EBF8; }

/* campos, avisos, expansores e conversa seguem a mesma linguagem: cantos suaves e bordas discretas */
[data-baseweb="select"] > div { border-radius: 10px !important; background: #1C2238 !important;
  border-color: rgba(255,255,255,.14) !important; }
[data-testid="stExpander"] { border: 1px solid rgba(255,255,255,.1) !important; border-radius: 12px !important; background: #192033; }
[data-testid="stAlert"] { border-radius: 10px; }
[data-testid="stChatMessage"] { border-radius: 14px; padding: 14px 16px; background: hsla(172,40%,50%,.06);
  border: 1px solid hsla(172,45%,60%,.16); }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background: hsla(255,40%,60%,.08);
  border-color: hsla(255,45%,70%,.2); }

/* cada grupo de botões do formulário vive num painel com o tom da sua família */
[class*="st-key-caixa_"] { border-radius: 14px; padding: 16px 20px 20px !important; margin-bottom: 14px; gap: .5rem !important; }
[class*="st-key-caixa_"] .grupo { margin: 0 0 .5rem 0; font-size: 1.02rem; }
.st-key-caixa_momento { background: hsla(285,35%,60%,.06); border: 1px solid hsla(285,40%,72%,.18); }
.st-key-caixa_momento .grupo { color: hsl(285,55%,82%); }

/* diagramação: cabeçalhos centralizados, linhas de texto equilibradas, sem ícones de link nos títulos */
[data-testid="stHeaderActionElements"] { display: none !important; }
.hero { text-align: center; max-width: 780px; margin: 0 auto 2.4rem auto; }
.hero .kicker { margin: 0 0 .8rem 0; }
.hero h1.titulo { margin: 0 0 1rem 0; text-wrap: balance; }
.hero .hero-sub { font-size: clamp(1rem, 2.6vw, 1.15rem); line-height: 1.6; color: #B4C0E4; margin: 0 auto; max-width: 62ch; text-wrap: balance; }
h2.secao { text-align: center; text-wrap: balance; }
p.secao-sub { text-align: center; margin: 0 auto 2rem auto; text-wrap: balance; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li { text-wrap: pretty; }
.ct, .stApp h3, .stApp h4 { text-wrap: balance; }

/* resumo do perfil */
.perfil { background: #1C2238; border: 1px solid rgba(255,255,255,.09); border-radius: 12px; padding: 18px 22px; }
.perfil-fatos { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px 24px; }
.perfil-fatos span { display: block; font-size: .82rem; color: #9FB0D6; margin-bottom: 2px; }
.perfil-fatos b { font-weight: 600; color: #E6EBF8; font-size: 1rem; line-height: 1.35; }
.perfil-rotulo { font-size: .82rem; color: #9FB0D6; margin: 18px 0 8px 0; padding-top: 16px; border-top: 1px solid rgba(255,255,255,.08); }
.perfil-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.perfil-tags i { font-style: normal; font-size: .84rem; padding: 3px 11px; border-radius: 999px; color: #D5DCF0;
  border: 1px solid rgba(255,255,255,.14); background: rgba(255,255,255,.05); }

/* rodapé "Sobre os dados" */
.st-key-rodape { position: relative; z-index: 4; background: hsl(226,25%,10.5%); border-top: 1px solid rgba(255,255,255,.1);
  padding: 3rem max(clamp(1rem, 5vw, 5rem), calc((100% - 1040px) / 2)) 3.4rem; }
.sobre h2.secao { font-size: clamp(1.3rem, 3vw, 1.7rem); margin-bottom: 1.6rem; }
.sobre-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.sobre-item { background: #1C2238; border: 1px solid rgba(255,255,255,.09); border-radius: 12px; padding: 16px 18px; }
.sobre-item .t { font-family: 'Fraunces', Georgia, serif; font-weight: 600; font-size: 1.02rem; color: #E6EBF8; margin-bottom: 6px; }
.sobre-item.largo { grid-column: 1 / -1; }
.sobre-item.largo p { max-width: 70ch; margin: 0 auto; }
.sobre-item p { margin: 0; font-size: .9rem; line-height: 1.55; color: #B4C0E4; }
@media (max-width: 1100px) { .sobre-grid { grid-template-columns: repeat(3, 1fr); } }

/* respiro e centralização: topo livre do cabeçalho do Streamlit, textos arejados, botões e títulos no eixo central */
.st-key-secao_1 { padding-top: 6.5rem; }
.st-key-secao_2, .st-key-secao_3 { padding-top: 5rem; }
.hero { max-width: 760px; margin: 0 auto 3.2rem auto; }
.hero .kicker { margin: 0 0 1rem 0; letter-spacing: .01em; }
.hero h1.titulo { margin: 0 0 1.5rem 0; line-height: 1.15; }
.hero .hero-sub { font-size: clamp(1.02rem, 2.4vw, 1.2rem); line-height: 1.75; max-width: 56ch; }
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li { line-height: 1.72; }
p.secao-sub { line-height: 1.7; max-width: 62ch; margin-bottom: 2.4rem; }
h2.secao { margin-bottom: .8rem; }
.grupo, .pergunta { text-align: center; }
[class*="st-key-caixa_"] { padding: 24px 28px 28px !important; margin-bottom: 20px; }
[class*="st-key-grupo_"][data-testid="stVerticalBlock"], [class*="st-key-grupo_"] > [data-testid="stVerticalBlock"] {
  justify-content: center !important; gap: .6rem !important; }
[data-testid="stButtonGroup"] { display: flex !important; justify-content: center; }
[data-testid="stButtonGroup"] > div { display: flex !important; flex-wrap: wrap !important; justify-content: center !important; gap: .6rem !important; }
[class*="st-key-caixa_mom_"] { align-items: center; }
.st-key-painel_filtros { padding: .9rem 1.2rem 1.3rem; }
.ct { text-align: center; margin-top: 1.7rem; }
.st-key-resultado [data-testid="stHeading"] { margin-top: 1.8rem; }
.st-key-resultado [data-testid="stHeading"] h2, .st-key-resultado [data-testid="stHeading"] h3 { text-align: center; }
.st-key-analise { margin: 0 auto; }
.perfil-fatos > div, .perfil-rotulo, .sobre-item { text-align: center; }
.perfil-tags { justify-content: center; }
[data-testid="stMetric"] { align-items: center; text-align: center; }
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] { width: 100%; justify-content: center; text-align: center; }

/* indicadores: mesma altura e valores numéricos numa linha só */
[data-testid="stMetric"] { min-height: 132px; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { font-size: clamp(1.45rem, 2.1vw, 1.9rem) !important; }
.st-key-kpi_1 [data-testid="stMetricValue"] *, .st-key-kpi_2 [data-testid="stMetricValue"] *,
.st-key-kpi_3 [data-testid="stMetricValue"] * { white-space: nowrap !important; }

html, body { background-color: #151B2D !important; }
.achado { border-left: 3px solid hsl(172,55%,58%); background: hsla(172,45%,50%,.07); border-radius: 0 10px 10px 0;
  padding: .85rem 1.1rem; color: #D5DCF0; font-size: 1rem; line-height: 1.65; margin: .3rem 0 1.2rem 0; }
.achado b { color: #E6EBF8; font-weight: 600; }

/* o fim de cada camada precisa continuar alcançável: a próxima só começa a cobrir depois de um respiro */
.st-key-secao_1, .st-key-secao_2 { padding-bottom: clamp(7rem, 38vh, 22rem); }

/* abertura: selo, título com acento, frase curta e três números em destaque */
.abertura { text-align: center; max-width: 820px; margin: 0 auto 2.4rem auto; }
.abertura .eyebrow { display: inline-flex; align-items: center; gap: .55rem; font-size: .88rem; color: hsl(172,45%,80%);
  border: 1px solid hsla(172,50%,62%,.35); background: hsla(172,45%,50%,.08); border-radius: 999px; padding: .4rem 1rem; margin-bottom: 1.6rem; }
.abertura .eyebrow i { width: 7px; height: 7px; border-radius: 50%; background: hsl(172,62%,60%); flex: none; }
.abertura h1.titulo { font-size: clamp(2.3rem, 6.4vw, 3.9rem); line-height: 1.08; margin: 0 0 1.3rem 0; text-wrap: balance; }
.abertura h1.titulo .acento { color: hsl(172,60%,72%); }
.abertura .hero-sub { font-size: clamp(1.02rem, 2.3vw, 1.2rem); line-height: 1.7; color: #B4C0E4; max-width: 50ch;
  margin: 0 auto 2rem auto; text-wrap: balance; }
.abertura .stats { display: grid; grid-template-columns: repeat(3, 1fr); max-width: 560px; margin: 0 auto;
  border: 1px solid rgba(255,255,255,.1); border-radius: 14px; background: #1C2238; }
.abertura .stats > div { padding: 16px 10px; }
.abertura .stats > div + div { border-left: 1px solid rgba(255,255,255,.09); }
.abertura .stats b { display: block; font-family: 'Fraunces', Georgia, serif; font-weight: 600; font-size: clamp(1.5rem, 4vw, 2rem);
  color: #E6EBF8; line-height: 1.1; }
.abertura .stats span { display: block; font-size: .84rem; color: #9FB0D6; margin-top: 4px; line-height: 1.3; }
div.como { text-align: center; color: #9FB0D6; font-size: .95rem; margin: 0 auto 1.2rem auto; max-width: 52ch; line-height: 1.55; text-wrap: balance; }
.etapa { display: flex; align-items: center; justify-content: center; gap: .7rem; font-family: 'Fraunces', Georgia, serif;
  font-weight: 600; font-size: clamp(1.15rem, 3vw, 1.4rem); color: #E6EBF8; margin: 2.4rem 0 1.1rem 0; }
.etapa b { width: 2rem; height: 2rem; border-radius: 50%; display: grid; place-items: center; font-family: 'Figtree', sans-serif;
  font-size: .95rem; font-weight: 600; background: hsla(172,55%,58%,.16); border: 1px solid hsla(172,60%,62%,.6); color: hsl(172,60%,84%); flex: none; }
.etapa.primeira { margin-top: .4rem; }

@media (max-width: 768px) {
  .st-key-rodape { padding: 2rem 1rem 2.4rem; }
  .sobre-grid { grid-template-columns: 1fr; }
  .hero { margin-bottom: 1.6rem; }
  .abertura { margin-bottom: 1.4rem; }
  .abertura .eyebrow { font-size: .8rem; padding: .35rem .85rem; margin-bottom: 1.2rem; }
  .abertura .hero-sub { margin-bottom: 1.4rem; }
  .abertura .stats > div { padding: 12px 4px; }
  .abertura .stats span { font-size: .76rem; }
  .etapa { margin: 1.8rem 0 .9rem 0; }
  [class*="st-key-caixa_"] { padding: 12px 12px 14px !important; }
  #carreira-nav { display: none !important; }
  .st-key-secao_1, .st-key-secao_2, .st-key-secao_3 { min-height: 0; padding: 1.6rem 1rem 2.6rem; box-shadow: none; }
  .st-key-secao_1::after, .st-key-secao_2::after { display: none; }
  [data-testid="stHorizontalBlock"] { gap: .8rem !important; }
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) { flex-wrap: wrap !important; gap: .6rem !important; }
  [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > div { min-width: calc(50% - .4rem) !important;
    flex: 1 1 calc(50% - .4rem) !important; }
  [data-testid="stMetric"] { min-height: 0; padding: 10px 12px; }
  [data-testid="stMetricValue"], [data-testid="stMetricValue"] * { font-size: 1.35rem !important; }
  [data-testid="stMetricLabel"] p { font-size: .8rem; }
  button[data-testid^="stBaseButton-pills"], button[data-variant="pills"] { min-height: 42px; font-size: .9rem; }
  button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"],
  button[data-testid="stBaseButton-secondary"] { min-height: 3rem; }
  .gap { padding: 12px 14px; }
  .ct { font-size: 1.02rem; margin-top: 1rem; }
  .rk { grid-template-columns: 1.8rem 1fr; gap: 10px 12px; padding: 14px; }
  .rk .fim { grid-column: 2; text-align: left; min-width: 0; }
  .rk .pct { font-size: 1.6rem; }
  [data-testid="stPlotlyChart"] { margin-left: -.35rem; margin-right: -.35rem; }
}
@media (max-width: 768px) { .st-key-secao_1 { padding-top: 5.2rem; } .st-key-secao_2, .st-key-secao_3 { padding-top: 3rem; }
  [class*="st-key-caixa_"] { padding: 16px 14px 18px !important; } }
@media (prefers-reduced-motion: reduce) { [data-testid="stMain"] { scroll-behavior: auto; } }
/* radar: duas versões do mesmo gráfico (tamanhos diferentes), cada uma aparece só no seu tipo de tela; o corte é o mesmo em que as colunas do Streamlit empilham */
.st-key-radar_cel { display: none; }
@media (max-width: 640px) {
  .st-key-radar_pc { display: none; }
  .st-key-radar_cel { display: block; margin-left: -.6rem; margin-right: -.6rem; }
}
"""

for _k, _v in {"__TEAL__": TEAL, "__AMBAR__": AMBAR, "__ROXO_ESCURO__": ROXO_ESCURO, "__AZUL__": AZUL, "__BG__": BG}.items():
    _CSS = _CSS.replace(_k, _v)
st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)

_JS_EMPILHAR = """
<script>
(function () {
  var doc = document;
  try { if (window.frameElement && window.parent && window.parent.document) doc = window.parent.document; } catch (e) {}
  var win = doc.defaultView || window;
  if (win.__carreira && win.__carreira.stop) win.__carreira.stop();

  var IDS = ["secao_1", "secao_2", "secao_3"];
  var NOMES = ["Descobrir minha área", "Painel geral", "Hipóteses do projeto"];
  var reduz = win.matchMedia && win.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var estado = { timer: null, alvoScroll: null, nav: null };

  function achar() {
    var s = IDS.map(function (i) { return doc.querySelector(".st-key-" + i); });
    if (s.some(function (x) { return !x; })) return null;
    var p = s[0].parentElement;
    while (p && !(p.contains(s[1]) && p.contains(s[2]))) p = p.parentElement;
    if (!p) return null;
    var ns = s.map(function (x) { var n = x; while (n.parentElement !== p) n = n.parentElement; return n; });
    var sc = p;
    while (sc && sc !== doc.body && sc !== doc.documentElement) {
      var o = win.getComputedStyle(sc).overflowY;
      if (o === "auto" || o === "scroll") break;
      sc = sc.parentElement;
    }
    var janela = !sc || sc === doc.body || sc === doc.documentElement;
    return { s: s, ns: ns, p: p, sc: janela ? doc.scrollingElement : sc, janela: janela };
  }
  function topoViewport(g) { return g.janela ? 0 : g.sc.getBoundingClientRect().top; }
  function altura(g) { return g.janela ? win.innerHeight : g.sc.clientHeight; }

  function layout() {
    var g = achar(); if (!g) return null;
    var vh = altura(g), celular = win.innerWidth <= 768;
    g.ns.forEach(function (n, i) {
      if (celular) {
        n.style.position = "relative"; n.style.top = "auto";
      } else if (i < g.ns.length - 1) {
        n.style.position = "sticky";
        n.style.top = Math.min(0, vh - n.offsetHeight) + "px";
      }
      n.style.zIndex = String(i + 1);
    });
    return g;
  }
  function alvos(g) {
    var base = g.p.getBoundingClientRect().top - topoViewport(g) + g.sc.scrollTop;
    var out = [], acc = base;
    g.ns.forEach(function (n) { out.push(acc); acc += n.offsetHeight; });
    return out;
  }
  function aoRolar() {
    var g = achar(); if (!g) return;
    var vh = altura(g), topo = topoViewport(g);
    for (var i = 0; i < g.s.length - 1; i++) {
      var r = g.ns[i + 1].getBoundingClientRect().top - topo;
      var prog = Math.max(0, Math.min(1, 1 - r / vh));
      g.s[i].style.setProperty("--dim", (reduz || win.innerWidth <= 768) ? "0" : (prog * 0.6).toFixed(3));
    }
    if (estado.nav) {
      var al = alvos(g), ativo = 0;
      al.forEach(function (t, i) { if (g.sc.scrollTop >= t - vh * 0.4) ativo = i; });
      Array.prototype.forEach.call(estado.nav.children, function (b, i) { b.classList.toggle("on", i === ativo); });
    }
  }
  function criarNav() {
    var antigo = doc.getElementById("carreira-nav"); if (antigo) antigo.remove();
    var nav = doc.createElement("div"); nav.id = "carreira-nav";
    NOMES.forEach(function (nome, i) {
      var b = doc.createElement("button"); b.type = "button";
      b.setAttribute("data-nome", nome); b.setAttribute("aria-label", nome);
      b.onclick = function () {
        var g = achar(); if (!g) return;
        g.sc.scrollTo({ top: alvos(g)[i], behavior: reduz ? "auto" : "smooth" });
      };
      nav.appendChild(b);
    });
    doc.body.appendChild(nav); estado.nav = nav;
  }
  function ligar() {
    var g = layout(); if (!g) return;
    var alvo = g.janela ? win : g.sc;
    if (estado.alvoScroll === alvo) return;
    if (estado.alvoScroll) estado.alvoScroll.removeEventListener("scroll", aoRolar);
    alvo.addEventListener("scroll", aoRolar, { passive: true });
    estado.alvoScroll = alvo; aoRolar();
  }
  criarNav(); ligar();
  estado.timer = win.setInterval(function () { ligar(); layout(); aoRolar(); }, 500);
  win.addEventListener("resize", layout);
  win.__carreira = { stop: function () {
    win.clearInterval(estado.timer);
    if (estado.alvoScroll) estado.alvoScroll.removeEventListener("scroll", aoRolar);
    win.removeEventListener("resize", layout);
    var n = doc.getElementById("carreira-nav"); if (n) n.remove();
  } };
})();
</script>
"""



def instalar_empilhamento():
    try:
        st.html(_JS_EMPILHAR, unsafe_allow_javascript=True)
    except TypeError:
        import streamlit.components.v1 as components
        components.html(_JS_EMPILHAR, height=0)


def rolar_para(seletor, folga=76):
    """Leva a página até um elemento (ao entrar no resultado ou ao refazer a entrevista).

    A barra fixa do Streamlit cobre os primeiros 60 px da tela, então o elemento para um pouco abaixo dela (folga).
    A posição é medida com as camadas empilhadas desligadas por um instante: enquanto uma camada está "grudada",
    ela se desloca e a medida normal erraria o destino."""
    ss_ = st.session_state
    ss_["rolar_n"] = ss_.get("rolar_n", 0) + 1
    js = """<script>
(function () {
  var doc = document;
  try { if (window.frameElement && window.parent && window.parent.document) doc = window.parent.document; } catch (e) {}
  var win = doc.defaultView || window;
  var FOLGA = __FOLGA__, cancelado = false, tentativas = 0;
  function achar() { return doc.querySelector("__SEL__"); }
  function rolante(el) {
    var n = el.parentElement;
    while (n && n !== doc.body && n !== doc.documentElement) {
      var o = win.getComputedStyle(n).overflowY;
      if ((o === "auto" || o === "scroll") && n.scrollHeight > n.clientHeight) return n;
      n = n.parentElement;
    }
    return doc.scrollingElement;
  }
  function posicaoNatural(el, sc) {
    var presos = [], n = el.parentElement;
    while (n && n !== doc.body) {
      if (win.getComputedStyle(n).position === "sticky") presos.push([n, n.style.position, n.style.top]);
      n = n.parentElement;
    }
    presos.forEach(function (p) { p[0].style.position = "relative"; p[0].style.top = "auto"; });
    var topo = el.getBoundingClientRect().top;
    presos.forEach(function (p) { p[0].style.position = p[1]; p[0].style.top = p[2]; });
    var base = (sc === doc.scrollingElement) ? 0 : sc.getBoundingClientRect().top;
    return topo - base + sc.scrollTop;
  }
  function alinhar() {
    var el = achar(); if (!el) return false;
    var sc = rolante(el);
    var y = Math.max(0, Math.round(posicaoNatural(el, sc) - FOLGA));
    if (Math.abs(sc.scrollTop - y) > 3) {
      var antigo = sc.style.scrollBehavior;
      sc.style.scrollBehavior = "auto";   // salto direto: não anima com o scroll suave do CSS
      sc.scrollTop = y;
      sc.style.scrollBehavior = antigo;
    }
    return true;
  }
  function parar() { cancelado = true; }
  ["wheel", "touchmove", "keydown", "mousedown"].forEach(function (ev) { win.addEventListener(ev, parar, { once: true, passive: true }); });
  function primeira() {
    if (cancelado) return;
    if (!alinhar()) { if (tentativas++ < 40) win.setTimeout(primeira, 100); return; }
    // o layout ainda pode mudar enquanto a página termina de carregar: confere de novo algumas vezes
    [300, 700, 1300, 2200, 3500].forEach(function (t) { win.setTimeout(function () { if (!cancelado) alinhar(); }, t); });
  }
  primeira();
})();
</script><!-- __N__ -->""".replace("__SEL__", seletor).replace("__FOLGA__", str(folga)).replace("__N__", str(ss_["rolar_n"]))
    try:
        st.html(js, unsafe_allow_javascript=True)
    except TypeError:
        import streamlit.components.v1 as components
        components.html(js, height=0)


def subir_ao_topo(destino="resultado"):
    """Reposiciona a página ao concluir ("resultado": começo de "Seu perfil") ou ao refazer ("topo": início da página).

    Zera a rolagem dos contêineres rolantes (para desfazer as camadas "grudadas") e, no caso do resultado, mede onde
    começa "Seu perfil" e rola até lá, repetindo por alguns segundos porque o resultado ainda está sendo montado.
    Dispara no INÍCIO da execução. Se a pessoa rolar por conta própria depois de ~1 s, a repetição para.
    Roda num iframe (components.html), que executa scripts em qualquer versão do Streamlit; só cai para st.html
    se isso falhar. O script acha o documento do app subindo pelos iframes (no Cloud o app está dentro de um)."""
    ss_ = st.session_state
    ss_["rolar_n"] = ss_.get("rolar_n", 0) + 1
    js = """<script>
(function () {
  var DESTINO = "__D__", ID = __N__;
  function docApp() {
    var w = window;
    for (var i = 0; i < 5; i++) {
      try {
        var d = w.document;
        if (d.querySelector('[data-testid="stMain"]') || d.querySelector('.st-key-secao_1')) return d;
        if (w.parent === w) break;
        w = w.parent;
      } catch (e) { break; }
    }
    return document;
  }
  var doc = docApp(), win = doc.defaultView || window, t0 = Date.now(), parado = false;
  var SEL = ['[data-testid="stMain"]', '.stMain', 'section.main', '[data-testid="stAppViewContainer"]', '.stAppViewContainer'];
  function direto(e, y) {
    var b = e.style.scrollBehavior;
    e.style.scrollBehavior = "auto";   // salto direto, sem o scroll suave do CSS
    e.scrollTop = y;
    e.style.scrollBehavior = b;
  }
  function zerar() {
    var els = [doc.scrollingElement, doc.documentElement, doc.body];
    SEL.forEach(function (s) { var e = doc.querySelector(s); if (e) els.push(e); });
    var a = doc.querySelector('.st-key-secao_1'), n = a && a.parentElement;
    while (n && n !== doc.documentElement) { els.push(n); n = n.parentElement; }
    els.forEach(function (e) { if (e && e.scrollTop > 0) direto(e, 0); });
    try { win.scrollTo(0, 0); } catch (e) {}
  }
  function rolante(el) {
    var n = el.parentElement;
    while (n && n !== doc.documentElement) {
      var oy = win.getComputedStyle(n).overflowY;
      if ((oy === "auto" || oy === "scroll") && n.scrollHeight > n.clientHeight) return n;
      n = n.parentElement;
    }
    return doc.querySelector('[data-testid="stMain"]') || doc.scrollingElement;
  }
  function ir() {
    if (DESTINO !== "resultado") { zerar(); return true; }
    var el = doc.querySelector('.st-key-resultado');
    if (!el) return false;               // o resultado ainda não foi desenhado: tenta de novo no próximo ciclo
    var sc = rolante(el);
    direto(sc, 0);                        // sem camadas grudadas, a posição medida é a posição natural
    var base = (sc === doc.scrollingElement || sc === doc.documentElement) ? 0 : sc.getBoundingClientRect().top;
    direto(sc, Math.max(0, Math.round(el.getBoundingClientRect().top - base - 76)));  // 76 px: abaixo da barra fixa
    return true;
  }
  ["wheel", "touchmove", "keydown"].forEach(function (ev) {
    win.addEventListener(ev, function () { if (Date.now() - t0 > 1000) parado = true; }, { passive: true });
  });
  [0, 100, 250, 500, 900, 1400, 2000, 3000, 4500, 6500, 9000].forEach(function (ms) {
    win.setTimeout(function () { if (!parado && !ir() && ms >= 6500) zerar(); }, ms);
  });
})();
</script>""".replace("__D__", destino).replace("__N__", str(ss_["rolar_n"]))
    try:
        import streamlit.components.v1 as components
        components.html(js, height=0)
    except Exception:
        st.html(js, unsafe_allow_javascript=True)


@st.cache_resource
def get_base_v2():
    return motor.carregar_base()


@st.cache_resource
def get_geojson():
    local = motor.PASTA / "dados" / "brasil_estados.geojson"
    if local.exists():
        return json.loads(local.read_text(encoding="utf-8"))
    with urllib.request.urlopen(motor.URL_GEOJSON, timeout=15) as r:
        return json.load(r)


def moeda(v):
    return "R$ " + f"{v:,.0f}".replace(",", ".")


FONTE = "Figtree, system-ui, sans-serif"
CFG = {"displayModeBar": False}


def titulo_grafico(texto):
    st.markdown(f'<div class="ct">{_html.escape(texto)}</div>', unsafe_allow_html=True)


def _quebra_rotulo(texto, n, max_linhas=2):
    """Quebra um rótulo em linhas de até ~n caracteres (também depois de '/'), no máximo max_linhas.
    O texto completo continua no hover, porque só o rótulo do eixo é encurtado."""
    texto = str(texto)
    if len(texto) <= n:
        return texto
    if len(texto) > n * max_linhas:
        texto = texto[: n * max_linhas - 1].rstrip() + "…"
    texto = texto.replace("/", "/ ")
    linhas, atual = [], ""
    for p in texto.split():
        if atual and len(atual) + 1 + len(p) > n:
            linhas.append(atual)
            atual = p
        else:
            atual = f"{atual} {p}".strip()
    linhas.append(atual)
    estourou = len(linhas) > max_linhas
    linhas = linhas[:max_linhas]
    if estourou and not linhas[-1].endswith("…"):
        linhas[-1] += "…"  # avisa que o rótulo foi encurtado (o texto completo está no hover)
    return "<br>".join(linhas)


def _faixa_curta(txt):
    """'de R$ 4.001/mês a R$ 6.000/mês' -> '4–6k'."""
    nums = [int(n.replace(".", "")) for n in re.findall(r"\d[\d.]*\d|\d", txt)]
    if txt.startswith("Menos"):
        return f"< {nums[0] // 1000}k"
    if txt.startswith("Acima"):
        return f"> {nums[0] // 1000}k"
    return f"{round(nums[0] / 1000)}–{nums[1] // 1000}k"


def _exp_curta(txt):
    """Rótulo curto de experiência para telas estreitas: 'Menos de 1 ano' -> '< 1'; 'de 3 a 4 anos' -> '3–4'; 'Mais de 10 anos' -> '10+'.
    Devolve None quando o texto não é uma faixa de experiência (aí o rótulo segue a quebra normal)."""
    t = str(txt)
    nums = re.findall(r"\d+", t)
    if not nums or "ano" not in t:
        return None
    if t.startswith("Menos"):
        return f"< {nums[0]}"
    if t.startswith("Mais"):
        return f"{nums[0]}+"
    if len(nums) >= 2:
        return f"{nums[0]}–{nums[1]}"
    return None


# Rótulos do eixo X abreviados só no eixo (o texto completo continua no hover): evitam a sobreposição em telas estreitas.
_ABREV_X = {
    "Especialista/Staff+": "Espec.<br>Staff+",
    "Gestão/Liderança": "Gestão/<br>Líder.",
}


def _quebrar_titulo_eixo(fig):
    """Títulos de eixo longos não quebram sozinhos no Plotly e saem cortados no celular: quebramos em linhas curtas."""
    for nome, n in (("xaxis", 30), ("yaxis", 24)):
        eixo = getattr(fig.layout, nome)
        texto = eixo.title.text if eixo.title is not None else None
        if texto and "<br>" not in texto and len(texto) > n:
            eixo.title.text = quebra_hover(texto, n)


def _ajustar_rotulos(fig):
    """Eixos categóricos: rótulos quebrados em linhas curtas, sem rotação, para caber em telas estreitas."""
    barras_horizontais = any(tr.type == "bar" and getattr(tr, "orientation", None) == "h" for tr in fig.data)
    if barras_horizontais:  # eixo dos valores (%, R$): poucos números e sem texto girado, para não se misturarem
        fig.update_xaxes(tickangle=0, nticks=4)
    _quebrar_titulo_eixo(fig)
    for eixo_dado, eixo_fig, largura in (("x", fig.update_xaxes, 11), ("y", fig.update_yaxes, 28)):
        cats = []
        for tr in fig.data:
            if tr.type not in ("bar", "scatter"):
                continue
            horizontal = getattr(tr, "orientation", None) == "h"
            if (eixo_dado == "y") != horizontal:
                continue
            valores = getattr(tr, eixo_dado, None)
            if valores is None:
                continue
            for v in valores:
                if isinstance(v, str) and v not in cats:
                    cats.append(v)
        if not cats or len(cats) > 8 and eixo_dado == "x":
            continue
        textos = [_quebra_rotulo(c, largura, max_linhas=2 if eixo_dado == "x" else 3) for c in cats]
        if eixo_dado == "x":
            textos = [_ABREV_X.get(c, t) for c, t in zip(cats, textos)]
            curtos = [_exp_curta(c) for c in cats]
            if all(c is not None for c in curtos):  # eixo de tempo de experiência: rótulos curtos não se misturam no celular
                textos = curtos
        kw = dict(tickmode="array", tickvals=cats, ticktext=textos)
        if eixo_dado == "x":
            kw["tickangle"] = 0
        eixo_fig(**kw)
        if eixo_dado == "y" and max(len(c) for c in cats) > 40:  # rótulos muito longos: mais altura por barra
            linhas = max(t.count("<br>") + 1 for t in textos)
            por_barra = 40 if linhas <= 2 else 56
            fig.update_layout(height=max(fig.layout.height or 0, len(cats) * por_barra + 70))


def estilizar(fig):
    fig.update_layout(
        title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CBD3EA", family=FONTE, size=13),
        margin=dict(l=8, r=8, t=16, b=8),
        coloraxis_showscale=False,
        dragmode=False,
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, title_text=""),
    )
    fig.update_layout(
        bargap=0.28,
        hoverlabel=dict(bgcolor="#1C2238", bordercolor="rgba(255,255,255,.2)", font=dict(family=FONTE, color="#E6EBF8", size=13)),
    )
    eixo = dict(gridcolor="rgba(255,255,255,.06)", zeroline=False, automargin=True, tickfont=dict(color="#B4C0E4"),
                title_font=dict(color="#9FB0D6", size=12))
    fig.update_xaxes(**eixo)
    fig.update_yaxes(**eixo)
    _ajustar_rotulos(fig)
    try:  # cantos arredondados nas barras (plotly 5.19+); em versões antigas simplesmente não se aplica
        fig.update_traces(marker_cornerradius=5, selector=dict(type="bar"))
    except Exception:
        pass
    return fig


# ----------------------------------------------------------------------
# Textos do hover: frases completas em vez de "campo=valor" (e sem o corte "..." do texto automático do Plotly)
# ----------------------------------------------------------------------

def resp(n):
    n = int(n)
    return f"{n} respondente" if n == 1 else f"{n} respondentes"


def _minuscula(txt):
    """'Menos de 1 ano' -> 'menos de 1 ano'; 'Textos/Documentos' -> 'textos/documentos'; 'NoSQL' e siglas ficam como estão."""
    return re.sub(r"(^|/)([A-ZÁÉÍÓÚÂÊÔÃÕÇ])(?=[a-záéíóúâêôãõç])", lambda m: m.group(1) + m.group(2).lower(), str(txt))


def quebra_hover(txt, n=46):
    """Quebra a frase em linhas de ~n caracteres (o hover do Plotly não quebra sozinho)."""
    linhas, atual = [], ""
    for p in str(txt).split():
        if atual and len(atual) + 1 + len(p) > n:
            linhas.append(atual)
            atual = p
        else:
            atual = f"{atual} {p}".strip()
    linhas.append(atual)
    return "<br>".join(linhas)


# Itens de IA generativa são afirmações da pesquisa (1ª pessoa): aqui viram predicados na 3ª pessoa.
PREDICADO_IA = {
    "Uso soluções gratuitas de AI Generativa com foco em produtividade":
        "usam soluções gratuitas de IA generativa para ganhar produtividade",
    "Uso e pago pelas soluções de AI Generativa com foco em produtividade":
        "usam e pagam por soluções de IA generativa para ganhar produtividade",
    "A empresa que trabalho paga pelas soluções de AI Generativa com foco em produtividade":
        "trabalham numa empresa que paga por soluções de IA generativa para ganhar produtividade",
    "Uso soluções do tipo Copilot": "usam soluções do tipo Copilot",
    "Colaboradores usando AI generativa de forma independente e descentralizada":
        "dizem que, na empresa, as pessoas usam IA generativa de forma independente e descentralizada",
    "Direcionamento centralizado do uso de AI generativa":
        "dizem que a empresa direciona de forma centralizada o uso de IA generativa",
    "Desenvolvedores utilizando Copilots": "dizem que, na empresa, desenvolvedores usam Copilots",
    "AI Generativa e LLMs para melhorar produtos externos para os clientes finais":
        "dizem que a empresa usa IA generativa e LLMs para melhorar produtos para os clientes finais",
    "AI Generativa e LLMs para melhorar produtos internos para os colaboradores":
        "dizem que a empresa usa IA generativa e LLMs para melhorar produtos internos, para os colaboradores",
    "IA Generativa e LLMs como principal frente do negócio":
        "dizem que IA generativa e LLMs são a principal frente do negócio da empresa",
}


def frase_tec(item, categoria, pct, quem):
    """'91% dos respondentes técnicos usam Python.' / '31% dos respondentes técnicos trabalham numa empresa que paga…'"""
    if item in PREDICADO_IA:
        pred = PREDICADO_IA[item]
    elif categoria == "Fontes e tipos de dados":
        pred = f"trabalham com {_minuscula(item)}"
    elif categoria and categoria.startswith("IA generativa"):
        pred = f"indicam: \u201c{item}\u201d"
    else:
        pred = f"usam {item}"
    return f"{pct:.0%} {quem} {pred}."


def ondeq(onde):
    return "No Brasil" if onde == "Brasil" else f"Na região {onde}"


def mostrar(fig, titulo):
    titulo_grafico(titulo)
    st.plotly_chart(estilizar(fig), width="stretch", config=CFG)


try:
    base = get_base_v2()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

sec1 = st.container(key="secao_1")
sec2 = st.container(key="secao_2")
sec3 = st.container(key="secao_3")
rodape = st.container(key="rodape")  # "Sobre os dados": fica depois de tudo, na horizontal
with rodape:
    st.markdown(
        '<div class="sobre"><h2 class="secao">Sobre os dados</h2><div class="sobre-grid">'
        '<div class="sobre-item"><div class="t">Fonte</div><p>Pesquisa State of Data Brasil 2025-2026 '
        '(Data Hackers + Bain &amp; Company), com os dados abertos no Kaggle.</p></div>'
        '<div class="sobre-item"><div class="t">Quem está na análise</div><p>Pessoas que vivem no Brasil e '
        'trabalham como CLT, PJ, servidor público ou freelancer.</p></div>'
        f'<div class="sobre-item"><div class="t">O que cobre</div><p>{len(base.todas_profissoes)} profissões '
        f'(técnicas e de gestão) e {len(base.habilidades)} tecnologias e práticas.</p></div>'
        f'<div class="sobre-item"><div class="t">Privacidade</div><p>Mostramos só resultados somados, nunca as respostas '
        f'de cada pessoa. Um resultado só aparece quando pelo menos {MIN_N} respondentes se encaixam nele, para ninguém '
        'ser identificado. Não usamos gênero, cor/raça nem deficiência.</p></div>'
        '<div class="sobre-item"><div class="t">Como ler os salários</div><p>A pesquisa pergunta uma faixa de salário '
        '(por exemplo, de R$ 8.001 a R$ 12.000), então usamos o valor do meio de cada faixa. Os gráficos mostram a '
        '<strong>média</strong>: a soma de todos os salários dividida pelo número de respondentes.</p></div>'
        '<div class="sobre-item largo"><div class="t">Limites</div><p>Responderam pessoas voluntárias, a maioria do Sudeste. '
        'Os dados são do fim de 2025 e do começo de 2026. A pesquisa não pergunta a cidade, então '
        '<strong>não existe dado por capital</strong>, só por região do Brasil.</p></div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
# Instalado aqui (e não no fim do arquivo): assim a navegação existe mesmo que algo mais abaixo interrompa o script.
# O contêiner acima já reservou os lugares das seções, então este elemento fica depois delas.
instalar_empilhamento()


def chat():
    ss = st.session_state
    ss.setdefault("msgs", [{"role": "assistant", "content": ia.SAUDACAO}])
    for m in ss.msgs:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    texto_usuario = st.chat_input("Digite sua resposta…")
    if texto_usuario:
        ss.msgs.append({"role": "user", "content": texto_usuario})
        try:
            with st.spinner("Pensando…"):
                resposta, perfil = ia.proxima(base, ss.msgs)
        except Exception as e:
            ss.msgs.pop()
            st.error(f"Não consegui falar com a IA ({type(e).__name__}). Tente de novo ou use o formulário.")
            return
        if resposta:
            ss.msgs.append({"role": "assistant", "content": resposta})
        if perfil:
            ss.perfil = perfil
            ss.rolar = "resultado"
        st.rerun()


def opcoes_filtro(coluna, ordem=None):
    existentes = set(base.df[coluna].dropna().unique())
    return [o for o in ordem if o in existentes] if ordem else sorted(existentes)


# Botão marcado: o Streamlit novo usa data-selected / aria-pressed / aria-checked; o antigo, data-testid=...pillsActive
SEL_ATIVO = ':is([data-testid="stBaseButton-pillsActive"], [data-selected="true"], [aria-pressed="true"], [aria-checked="true"])'


def _css_grupo(prefixo, n, matiz):
    regras = []
    for j in range(n):
        h = round(deslize(matiz, j, n))
        s = f".st-key-{prefixo}_{j}"
        regras.append(
            f"{s} button {{ background: hsla({h},55%,58%,.14) !important; border-color: hsla({h},60%,62%,.55) !important; }}"
            f"{s} button{SEL_ATIVO} {{ background: hsl({h},62%,64%) !important; "
            f"border-color: hsl({h},62%,64%) !important; }}"
        )
    return regras


def css_botoes(base):
    """Cor de cada botão: família por grupo e deslize suave de matiz ao longo da ordem em que aparecem."""
    regras = []
    for i, (cat, hs) in enumerate(base.categorias.items()):
        h = MATIZ_CAT.get(cat, 200)
        regras += _css_grupo(f"t_{i}", len(hs), h)
        regras.append(
            f".st-key-caixa_{i} {{ background: hsla({h},40%,52%,.06); border: 1px solid hsla({h},45%,64%,.18); }}"
            f".st-key-caixa_{i} .grupo {{ color: hsl({h},60%,80%); }}"
        )
    for _, coluna, ordem, _ in FILTROS:
        regras += _css_grupo(f"flt_{coluna}", len(opcoes_filtro(coluna, ordem)), MATIZ_FILTRO[coluna])
    # "Seu momento": um matiz por pergunta, deslizando de leve do violeta ao orquídea
    for k, _, h in MOMENTO:
        regras.append(
            f".st-key-caixa_mom_{k} {{ background: hsla({h},40%,52%,.06); border: 1px solid hsla({h},45%,64%,.18); }}"
            f".st-key-caixa_mom_{k} .grupo {{ color: hsl({h},60%,80%); }}"
        )
        regras.append(
            f".st-key-mom_{k} button {{ background: hsla({h},55%,62%,.14) !important; border-color: hsla({h},60%,70%,.5) !important; }}"
            f".st-key-mom_{k} button{SEL_ATIVO} {{ background: hsl({h},58%,72%) !important; "
            f"border-color: hsl({h},58%,72%) !important; }}"
        )
    return "\n".join(regras)


def botoes(prefixo, opcoes, rotulos=None):
    """Um botão (pill) por opção, cada um com chave própria para poder receber a sua cor. Devolve as marcadas."""
    marcadas = []
    for j, o in enumerate(opcoes):
        marcadas += st.pills(
            o, [o], selection_mode="multi", key=f"{prefixo}_{j}", label_visibility="collapsed", format_func=rotulos or str
        ) or []
    return marcadas


def _chave_alfa(txt):
    """Ordena sem diferenciar maiúsculas e acentos (Álgebra antes de Banco)."""
    return unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower()


MOMENTO = [
    ("exp", "Experiência na área", 268),
    ("nivel", "Nível atual", 282),
    ("reg", "Região do Brasil onde você mora", 296),
    ("int", "O que mais gosta de fazer", 310),
    ("int2", "E em segundo lugar, se houver (opcional)", 324),
]


def _momento(chave, titulo, opcoes):
    """Pergunta de escolha única, na mesma caixa e diagramação dos grupos de tecnologias."""
    with st.container(key=f"caixa_mom_{chave}"):
        st.markdown(f'<div class="grupo">{_html.escape(titulo)}</div>', unsafe_allow_html=True)
        return st.pills(titulo, opcoes, selection_mode="single", key=f"mom_{chave}", label_visibility="collapsed")


def formulario():
    st.markdown(
        '<div class="como">Toque nos botões para marcar e toque de novo para desmarcar. '
        "Pode deixar qualquer grupo em branco.</div>",
        unsafe_allow_html=True,
    )
    with st.form("form_perfil", border=False):
        st.markdown('<div class="etapa primeira"><b>1</b>Suas tecnologias</div>', unsafe_allow_html=True)
        escolhidas = []
        for i, (cat, hs) in enumerate(base.categorias.items()):
            with st.container(key=f"caixa_{i}"):
                st.markdown(f'<div class="grupo">{_html.escape(cat)}</div>', unsafe_allow_html=True)
                with st.container(key=f"grupo_{i}"):
                    escolhidas += botoes(f"t_{i}", sorted(hs, key=_chave_alfa))
        st.markdown('<div class="etapa"><b>2</b>Seu momento</div>', unsafe_allow_html=True)
        exp = _momento("exp", "Experiência na área", ["Nenhuma"] + ORDEM_EXP) or "Nenhuma"
        nivel = _momento("nivel", "Nível atual", ia.NIVEIS) or "Ainda não atuo na área"
        regiao = _momento("reg", "Região do Brasil onde você mora", motor.REGIOES) or "Não informado"
        interesse = _momento("int", "O que mais gosta de fazer", list(motor.INTERESSES)) or "Sem preferência"
        interesse2 = _momento("int2", "E em segundo lugar, se houver (opcional)", motor.INTERESSES_2[1:]) or "Nenhum"
        st.caption(
            "Se marcar \"Ainda não atuo na área\" em Nível, o tempo de experiência é desconsiderado. "
            "A segunda área pesa menos que a principal na recomendação."
        )
        confirmar = st.session_state.get("avisar_vazio", False)
        if confirmar:
            st.warning("Você não marcou nenhuma tecnologia. Sem elas, a recomendação usa só nível, experiência e interesse. "
                       "Marque as que você usa ou toque de novo para ver o resultado mesmo assim.")
        if st.form_submit_button("Ver resultado mesmo assim" if confirmar else "Concluir e ver minha recomendação",
                                 type="primary", width="stretch"):
            if not escolhidas and not confirmar:
                st.session_state.avisar_vazio = True  # evita o envio sem querer: pede uma segunda confirmação
                st.rerun()
            st.session_state.pop("avisar_vazio", None)
            st.session_state.perfil = ia.validar_perfil(
                dict(habilidades=escolhidas, experiencia=exp, nivel=nivel, regiao=regiao, interesse=interesse,
                     interesse_secundario=interesse2), base
            )
            st.session_state.rolar = "resultado"
            st.rerun()


def comparativo(br, rg, col, ordem, titulo, regiao, linha=False, cargo=None):
    partes = [br.assign(Onde="Brasil")]
    if not rg.empty:
        partes.append(rg.assign(Onde=regiao))
    d = pd.concat(partes)
    d[col] = d[col].astype(str)
    if d.empty:
        st.info(f"Ainda não há respondentes suficientes (mínimo de {MIN_N}) para mostrar este recorte.")
        return
    prof = f"quem atua como {cargo}" if cargo else "quem atua na área"

    def _frase(r):
        v = str(r[col])
        quem = f"{prof} no nível {v}" if col == "senioridade" else f"{prof} e tem {_minuscula(v)} de experiência"
        return quebra_hover(f"{ondeq(r['Onde'])}, {quem} ganha, em média, {moeda(r['media'])} por mês ({resp(r['n'])}).")

    d["hover"] = d.apply(_frase, axis=1)
    kw = dict(
        x=col,
        y="media",
        color="Onde",
        custom_data=["hover"],
        category_orders={col: ordem},
        color_discrete_sequence=PAR,
        labels={"media": "Salário médio (R$/mês)", col: ""},
    )
    fig = px.line(d, markers=True, **kw) if linha else px.bar(d, barmode="group", **kw)
    fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
    if linha:
        fig.update_traces(line=dict(width=4), marker=dict(size=10))
    mostrar(fig, titulo)
    if regiao in motor.REGIOES and rg.empty:
        st.caption(f"Na sua região ({regiao}) há menos de {MIN_N} respondentes neste recorte, por isso mostramos só o Brasil.")


def _quebra(texto, n=11):
    texto = texto.replace("(produtividade)", "(produti-<br>vidade)")  # palavra longa: parte ao meio para o rótulo ocupar menos largura
    linhas, atual = [], ""
    for p in texto.split():
        if atual and len(atual) + 1 + len(p) > n:
            linhas.append(atual)
            atual = p
        else:
            atual = f"{atual} {p}".strip()
    linhas.append(atual)
    return "<br>".join(linhas)


def radar(dg, cargo, compacto=False):
    """compacto=True: versão para celular (menos margem, para o círculo ocupar quase toda a largura); False: computador."""
    eixos = list(dg["eixo"]) + [dg["eixo"].iloc[0]]
    rotulos = [_quebra(e, 11 if compacto else 14) for e in eixos]

    def serie(col, nome, cor, dash, width, fill=None, quem="você"):
        v = list(dg[col]) + [dg[col].iloc[0]]
        return go.Scatterpolar(
            r=v,
            theta=rotulos,
            customdata=[quebra_hover(f"Em {e}, {quem} está em {v:.0f}%.", 40) for e, v in zip(eixos, v)],
            name=nome,
            mode="lines+markers",
            fill="toself" if fill else None,
            fillcolor=fill,
            line=dict(color=cor, width=width, dash=dash),
            marker=dict(size=6),
            hovertemplate="%{customdata}<extra></extra>",
        )

    fig = go.Figure([
        serie("comunidade", "Média da pesquisa", "#E5E7EB", "dash", 2, quem="a média de todos os respondentes"),
        serie("alvo", "Perfil típico da profissão", AMBAR, "dot", 3, quem="o profissional típico da profissão"),
        serie("voce", "Você", TEAL, "solid", 4, fill="rgba(53,208,186,.2)", quem="você"),
    ])
    fig = estilizar(fig)
    fig.update_layout(
        margin=dict(l=62, r=64, t=26, b=64) if compacto else dict(l=78, r=78, t=36, b=70),
        height=340 if compacto else 500,
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center", yanchor="top"),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                range=[0, 100],
                tickvals=[25, 50, 75, 100],
                ticksuffix="%",
                angle=67.5,  # entre os eixos "Nuvem" e "Bancos de dados": os números não ficam por cima de uma linha do radar
                tickangle=0,  # números na horizontal
                gridcolor="rgba(255,255,255,.22)",
                linecolor="rgba(255,255,255,.22)",
                tickfont=dict(size=11 if compacto else 12, color="#F1F5FF"),
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,.14)",
                linecolor="rgba(255,255,255,.14)",
                tickfont=dict(size=10 if compacto else 12, color="#CBD3EA"),
            ),
        ),
    )
    return fig


def lacunas_html(dg):
    d = dg.assign(lacuna=dg["alvo"] - dg["voce"]).sort_values("lacuna", ascending=False)
    falta = d[d["lacuna"] > 1]
    partes = []
    for r in falta.itertuples():
        partes.append(
            f'<div class="gap" style="--t:hsla({MATIZ_EIXO.get(r.eixo, 220)},40%,50%,.08);--b:hsla({MATIZ_EIXO.get(r.eixo, 220)},45%,64%,.30)">'
            f'<div class="t"><b>{_html.escape(r.eixo)}</b>'
            f'<span><span class="v">Você {r.voce:.0f}%</span><span class="a">Alvo {r.alvo:.0f}%</span></span></div>'
            f'<div class="bar"><i style="width:{min(r.voce, 100):.0f}%"></i><u style="left:{min(r.alvo, 100):.0f}%"></u></div>'
            f'<p>{_html.escape(r.falta)}</p></div>'
        )
    fortes = d[d["lacuna"] <= 1]["eixo"].tolist()
    return "".join(partes), fortes


def _estilo_cargo(cargo):
    h = MATIZ_CARGO.get(cargo, 220)
    return (
        f"--c:{hexhsl(h, 60, 66)};--c2:{hexhsl(h, 50, 40)};"
        f"--t:hsla({h:.0f},45%,55%,.08);--b:hsla({h:.0f},50%,64%,.30)"
    )


def cartoes_ranking(top, salarios):
    maximo = max(float(top.adequacao.max()), 1e-9)
    itens = []
    for pos, r in enumerate(top.itertuples(), start=1):
        sal = salarios.get(r.cargo)
        sal_txt = f"Salário médio: {moeda(sal)}/mês" if sal == sal and sal else "Sem dado salarial"
        n_txt = f"{r.n_total} respondentes" + (" (poucos respondentes: leia com cautela)" if r.amostra_reduzida else "")
        itens.append(
            f'<div class="rk{" topo" if pos == 1 else ""}" style="{_estilo_cargo(r.cargo)}">'
            f'<div class="pos">{pos}</div>'
            f'<div class="corpo"><div class="nome">{_html.escape(r.cargo)}</div>'
            f'<div class="meta">{_html.escape(r.grupo)}</div>'
            f'<div class="barra"><i style="width:{r.adequacao / maximo * 100:.0f}%"></i></div></div>'
            f'<div class="fim"><div class="pct">{r.adequacao:.0%}</div>'
            f'<div class="sal">{sal_txt}</div><div class="sal">{n_txt}</div></div></div>'
        )
    return '<div class="rk-lista">' + "".join(itens) + "</div>"


def perfil_html(perfil):
    matiz = {h: MATIZ_CAT.get(cat, 200) for cat, hs in base.categorias.items() for h in hs}
    marcadas = set(perfil["habilidades"])
    ordenadas = [h for hs in base.categorias.values() for h in sorted(hs, key=_chave_alfa) if h in marcadas]
    fatos = [("Experiência", perfil["experiencia"]), ("Nível", perfil["nivel"]),
             ("Região", perfil["regiao"]), ("Interesse", perfil["interesse"])]
    if perfil.get("interesse_secundario", "Nenhum") != "Nenhum":
        fatos.append(("Em segundo lugar", perfil["interesse_secundario"]))
    fatos_html = "".join(f"<div><span>{_html.escape(k)}</span><b>{_html.escape(str(v))}</b></div>" for k, v in fatos)
    bloco = ""
    if ordenadas:
        tags = "".join(
            f'<i style="background:hsla({matiz[h]},55%,58%,.14);border-color:hsla({matiz[h]},60%,62%,.45)">{_html.escape(h)}</i>'
            for h in ordenadas
        )
        bloco = f'<div class="perfil-rotulo">Tecnologias e práticas ({len(ordenadas)})</div><div class="perfil-tags">{tags}</div>'
    return f'<div class="perfil"><div class="perfil-fatos">{fatos_html}</div>{bloco}</div>'


def _slug(txt):
    sem_acento = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-") or "diagnostico"


def botao_pdf(perfil, top, salarios, cargo, dg, tabelas, analise):
    """Botão de download do diagnóstico em PDF (profissão escolhida no seletor + análise + tabelas)."""
    try:
        pdf = relatorio.gerar_pdf(
            perfil, top, salarios, cargo, dg, tabelas,
            motor.habilidades_cargo(base, cargo, perfil["habilidades"]), analise, int(base.n_total.get(cargo, 0)),
        )
    except Exception as e:  # o PDF é um extra: se falhar, o resto da página continua funcionando
        st.caption(f"Não foi possível gerar o PDF agora ({type(e).__name__}).")
        return
    st.markdown(
        "<style>"
        ".st-key-slot_pdf{margin:.4rem 0 1.6rem}"
        ".st-key-slot_pdf button{min-height:3.5rem;font-size:1.08rem;font-weight:700;border:0;"
        "background:linear-gradient(135deg,#8B5CF6,#6D44D8);box-shadow:0 6px 22px rgba(139,92,246,.38)}"
        ".st-key-slot_pdf button:hover{filter:brightness(1.12)}"
        ".st-key-slot_pdf [data-testid=stCaptionContainer]{text-align:center}"
        "</style>",
        unsafe_allow_html=True,
    )
    st.download_button(
        "Baixe seu diagnóstico em PDF",
        data=pdf,
        file_name=f"diagnostico-carreira-tech-{_slug(cargo)}.pdf",
        mime="application/pdf",
        icon=":material/download:",
        type="primary",
        width="stretch",
        key="baixar_pdf",
        on_click="ignore",  # o clique só baixa o arquivo: não reexecuta o app nem mexe na rolagem
    )
    st.caption(f"Leva seu perfil, as áreas com mais afinidade, a análise e o diagnóstico de **{cargo}** (a profissão "
               "selecionada no diagnóstico, lá em cima). Escolheu outra? Baixe de novo.")


def resultado(perfil):
    ss = st.session_state
    rk = motor.ranking(
        base,
        perfil["habilidades"],
        interesse=perfil["interesse"],
        experiencia=perfil["experiencia"],
        nivel=perfil["nivel"],
        interesse2=perfil.get("interesse_secundario", "Nenhum"),
    )
    reg = perfil["regiao"]
    st.subheader("Seu perfil")
    st.markdown(perfil_html(perfil), unsafe_allow_html=True)
    if not perfil["habilidades"]:
        st.warning("Sem habilidades informadas, o ranking usa interesse, experiência e nível. Refaça para um resultado mais completo.")
    if rk.empty:
        st.error("Ainda não há respondentes suficientes para fazer uma recomendação com esse perfil.")
        return

    top = motor.principais(rk, perfil["interesse"], perfil["nivel"], k=TOP_AREAS,
                           interesse2=perfil.get("interesse_secundario", "Nenhum"))
    salarios = motor.panorama_todas_profissoes(base).set_index("cargo")["media_brasil"].to_dict()

    st.subheader(
        f"As {len(top)} áreas que mais combinam com você",
        help="A barra compara as áreas entre si. Nas profissões técnicas, a afinidade considera as tecnologias e "
        "práticas que você usa e o que você gosta de fazer. Nos cargos de gestão e liderança, que não respondem à "
        "parte técnica da pesquisa, ela considera seu interesse, seu nível e sua experiência.",
    )
    st.markdown(cartoes_ranking(top, salarios), unsafe_allow_html=True)
    outras = rk[~rk.cargo.isin(top.cargo)]
    with st.expander(f"Ver as outras {len(outras)} profissões da pesquisa"):
        st.dataframe(
            outras.assign(Afinidade=(outras.adequacao * 100).round().astype(int).astype(str) + "%")[["cargo", "grupo", "Afinidade", "n_total"]]
            .rename(columns={"cargo": "Profissão", "grupo": "Grupo", "n_total": "Respondentes"}),
            hide_index=True,
            width="stretch",
        )

    st.subheader(
        "Diagnóstico: onde você está e onde quer chegar",
        help="Cada ponta do gráfico é uma área de conhecimento. Em tecnologias, 100% significa usar todas as que "
        "costumam ser usadas na profissão. A linha verde é você, a pontilhada âmbar é o profissional típico da "
        "profissão escolhida e a tracejada cinza é a média de todos os respondentes.",
    )
    mais = st.toggle("Incluir as outras profissões na lista", key="cargo_mais")
    opcoes = list(top.cargo) + ([c for c in rk.cargo if c not in set(top.cargo)] if mais else [])
    if st.session_state.get("cargo_sel") not in opcoes:
        st.session_state["cargo_sel"] = opcoes[0]
    cargo = st.selectbox(
        "Profissão que você quer explorar",
        opcoes,
        key="cargo_sel",
        help="Começa pela área com mais afinidade. Ative a opção acima para comparar com qualquer uma das profissões da base.",
    )
    if cargo in motor.CARGOS_GESTAO:
        st.info(
            f"**{cargo}** é um cargo de gestão ou liderança. Na pesquisa, quem ocupa esses cargos não responde à parte "
            "técnica (tecnologias e ferramentas), por isso abaixo você vê só os comparativos de experiência e salário."
        )
    elif base.n_total.get(cargo, 0) < MIN_N:
        st.warning(f"A base tem poucos respondentes de **{cargo}** (só {base.n_total.get(cargo, 0)}; o mínimo para uma leitura confiável é {MIN_N}). Veja os resultados como uma pista, não como regra.")

    dg = motor.diagnostico(base, perfil, cargo)
    gr, gl = st.columns([3, 2], gap="large")
    with gr:
        titulo_grafico(f"Você x {cargo}")
        with st.container(key="radar_pc"):
            st.plotly_chart(radar(dg, cargo), width="stretch", config=CFG, key="radar_g_pc")
        with st.container(key="radar_cel"):
            st.plotly_chart(radar(dg, cargo, compacto=True), width="stretch", config=CFG, key="radar_g_cel")
    with gl:
        st.markdown("##### Todas as lacunas identificadas")
        html_lac, fortes = lacunas_html(dg)
        if html_lac:
            st.markdown(html_lac, unsafe_allow_html=True)
        else:
            st.success("Você já está no nível do perfil típico desta profissão nos eixos avaliados.")
        if fortes and html_lac:
            st.markdown(
                '<div class="ok"><b>Já no nível da profissão:</b> ' + _html.escape(", ".join(fortes)) + ".</div>",
                unsafe_allow_html=True,
            )

    st.subheader("Análise personalizada")
    sm = motor.sumario(base, perfil, top)
    chave = json.dumps(perfil, sort_keys=True)
    if ss.get("analise_chave") != chave:
        with st.spinner("Preparando a análise das suas áreas…"):
            ss.analise = ia.explicar(sm) if ia.disponivel() else ia.explicar_local(sm)
        ss.analise_chave = chave
    with st.container(key="analise"):
        st.markdown(ss.analise.replace("$", "\\$"))  # sem isso, dois "R$" na mesma frase viram fórmula (texto verde)

    st.subheader("Explore a profissão escolhida")
    t = motor.tabelas_cargo(base, cargo, reg)
    g1, g2 = st.columns(2)
    with g1:
        hab = motor.habilidades_cargo(base, cargo, perfil["habilidades"])
        if hab.empty:
            st.info("Este cargo de gestão não tem dados técnicos na pesquisa.")
        else:
            hab["Situação"] = hab["tem"].map({True: "Você já usa", False: "Para desenvolver"})
            cat_de = {h: c for c, hs in base.categorias.items() for h in hs}
            hab["hover"] = [
                quebra_hover(frase_tec(r.habilidade, cat_de.get(r.habilidade), r.pct, f"dos respondentes de {cargo}"))
                + ("<br><i>Você já usa.</i>" if r.tem else "<br><i>Para desenvolver.</i>")
                for r in hab.itertuples()
            ]
            fig = px.bar(
                hab.sort_values("pct"),
                x="pct",
                y="habilidade",
                orientation="h",
                color="Situação",
                color_discrete_map={"Você já usa": TEAL, "Para desenvolver": AMBAR},
                category_orders={"Situação": ["Você já usa", "Para desenvolver"]},
                custom_data=["hover"],
                labels={"pct": "% dos respondentes da profissão que usam", "habilidade": ""},
            )
            fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
            fig.update_xaxes(tickformat=".0%")
            fig.update_layout(height=max(420, len(hab) * 24))
            mostrar(fig, f"Tecnologias e práticas usadas em: {cargo}")
    with g2:
        comparativo(t["nivel_br"], t["nivel_reg"], "senioridade", ORDEM_NIVEL, "Salário médio por nível de carreira", reg,
                    cargo=cargo)
    g3, g4 = st.columns(2)
    with g3:
        comparativo(
            t["exp_br"], t["exp_reg"], "experiencia", ORDEM_EXP, "Salário médio por tempo de experiência", reg, linha=True,
            cargo=cargo,
        )
    with g4:
        r = t["regioes"]
        if r.empty:
            st.info(f"Nenhuma região do Brasil tem {MIN_N} respondentes ou mais para esta profissão.")
        else:
            r = r.assign(hover=[
                quebra_hover(f"Na região {x.regiao}, quem atua como {cargo} ganha, em média, {moeda(x.media)} por mês ({resp(x.n)}).")
                for x in r.itertuples()
            ])
            fig = px.bar(
                r,
                x="regiao",
                y="media",
                color="media",
                color_continuous_scale=ESCALA,
                custom_data=["hover"],
                labels={"media": "Salário médio (R$/mês)", "regiao": ""},
            )
            fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
            mostrar(fig, "Salário médio por região do Brasil")
    with st.expander("Ver os valores por nível de carreira"):
        x = t["nivel_br"].copy()
        x["faixa"] = x.apply(lambda r: f"{moeda(r.p25)} a {moeda(r.p75)}", axis=1)
        x = x[["senioridade", "n", "media", "faixa"]].rename(
            columns={"senioridade": "Nível", "n": "Respondentes", "media": "Salário médio",
                     "faixa": "Faixa que reúne metade dos respondentes"}
        )
        st.dataframe(x.style.format({"Salário médio": moeda}), hide_index=True)
        st.caption("A última coluna mostra entre quais valores está o salário da metade \"do meio\" dos respondentes, "
                   "sem contar os 25% que ganham menos nem os 25% que ganham mais.")

    with st.container(key="slot_pdf"):  # espaço livre no fim do resultado, antes do Painel geral
        st.subheader("Leve seu diagnóstico")
        botao_pdf(perfil, top, salarios, cargo, dg, t, ss.analise)


st.markdown(f"<style>{css_botoes(base)}</style>", unsafe_allow_html=True)

with sec1:
    n_resp = f"{len(base.df):,}".replace(",", ".")
    if st.session_state.get("perfil") is not None:
        instrucao = "Veja abaixo as áreas que mais combinam com o seu perfil e o que o mercado paga em cada uma."
    elif ia.disponivel():
        instrucao = "Conte, na conversa ou no formulário, o que você domina e descubra as áreas em que mais se encaixa."
    else:
        instrucao = "Marque as tecnologias que você domina e descubra as áreas em que mais se encaixa e quanto o mercado paga."
    st.markdown(
        '<div class="abertura"><div class="eyebrow"><i></i>Com base no State of Data Brasil 2025-2026</div>'
        '<h1 class="titulo">Quanto vale uma <span class="acento">carreira tech</span>?</h1>'
        f'<p class="hero-sub">{instrucao}</p>'
        f'<div class="stats"><div><b>{n_resp}</b><span>respostas de profissionais</span></div>'
        f'<div><b>{len(base.todas_profissoes)}</b><span>profissões</span></div>'
        f'<div><b>{len(base.habilidades)}</b><span>tecnologias e práticas</span></div></div></div>',
        unsafe_allow_html=True,
    )
    ss = st.session_state
    ss.setdefault("perfil", None)
    destino = ss.pop("rolar", None)
    if destino:
        subir_ao_topo("topo" if destino == "topo" else "resultado")  # dispara antes de montar o resultado
    if ss.perfil is None:
        if ia.disponivel():
            modo = st.radio("Como prefere responder?", ["Entrevista com IA", "Formulário rápido"], horizontal=True)
        else:
            modo = "Formulário rápido"  # sem chave da API, o formulário é a única opção (sem aviso para o usuário)
        if modo == "Entrevista com IA":
            chat()
        else:
            formulario()
    else:
        if st.button("Refazer entrevista"):
            for k in ("perfil", "msgs", "analise", "analise_chave", "cargo_sel", "cargo_mais", "avisar_vazio"):
                ss.pop(k, None)
            ss.rolar = "topo"
            st.rerun()
        with st.container(key="resultado"):
            resultado(ss.perfil)


# ----------------------------------------------------------------------
# SEÇÃO 2 — Painel geral
# ----------------------------------------------------------------------

def limpar_filtros():
    for _, coluna, ordem, _ in FILTROS:
        for j in range(len(opcoes_filtro(coluna, ordem))):
            st.session_state[f"flt_{coluna}_{j}"] = []


def filtro(col_ui, rotulo, coluna, ordem=None, rotulos=None):
    opcoes = opcoes_filtro(coluna, ordem)
    col_ui.markdown(f'<div class="grupo">{_html.escape(rotulo)}</div>', unsafe_allow_html=True)
    with col_ui.container(key=f"grupo_flt_{coluna}"):
        sel = botoes(f"flt_{coluna}", opcoes, rotulos)
    return sel if sel else opcoes


with sec2:
    st.markdown(
        '<h2 class="secao">Painel geral</h2>'
        '<p class="secao-sub">Aqui está o retrato de todos os respondentes da pesquisa. Como a pesquisa pergunta uma faixa '
        "de salário por mês, usamos o valor do meio de cada faixa para calcular as médias. Use os filtros para olhar só um "
        "grupo; sem nada marcado, todos entram.</p>",
        unsafe_allow_html=True,
    )

    with st.container(border=True, key="painel_filtros"):
        topo, limpar = st.columns([5, 1], vertical_alignment="center")
        topo.markdown("**Filtros**")
        limpar.button("Limpar filtros", on_click=limpar_filtros, width="stretch")
        c_esq, c_dir = st.columns(2, gap="large")
        sel = {}
        for i, (rotulo, coluna, ordem, rotulos) in enumerate(FILTROS):
            sel[coluna] = filtro(c_esq if i < 2 else c_dir, rotulo, coluna, ordem, rotulos)

    d = base.df[
        base.df.regiao.isin(sel["regiao"])
        & base.df.senioridade.isin(sel["senioridade"])
        & base.df.contrato.isin(sel["contrato"])
        & base.df.tamanho_empresa.isin(sel["tamanho_empresa"])
    ]

    k1, k2, k3, k4 = st.columns(4)
    if d.empty:
        st.warning("Nenhum respondente se encaixa nesses filtros. Desmarque algum para ver os resultados.")
    elif len(d) < MIN_N:
        st.warning(f"Com esses filtros há menos de {MIN_N} respondentes, então não mostramos resultados. Desmarque algum filtro para ampliar.")
    else:
        with k1.container(key="kpi_1"):
            st.metric("Respondentes analisados", f"{len(d):,}".replace(",", "."),
                      help=f"{len(d) / len(base.df):.1%} de todos os respondentes da base.")
        with k2.container(key="kpi_2"):
            st.metric("Salário médio", moeda(d.salario.mean()),
                      help="A soma de todos os salários dividida pelo número de respondentes.")
        with k3.container(key="kpi_3"):
            st.metric("Salário do meio (mediana)", moeda(d.salario.median()),
                      help="Se colocássemos todos os respondentes em fila, do menor para o maior salário, este é o salário "
                           "de quem está no meio: metade ganha menos e metade ganha mais.")
        with k4.container(key="kpi_4"):
            st.metric("Profissão mais comum", d.cargo.mode()[0], help="A profissão com mais respondentes nesta seleção.")
        st.caption(
            "Os gráficos usam a média, que é o escopo do projeto. O salário do meio aparece só aqui, como referência: "
            "se ele for bem menor que a média, poucos salários muito altos estão puxando a média para cima."
        )

        a, b = st.columns(2)
        with a:
            pc = motor.resumo(d, "cargo").sort_values("media")
            pc["hover"] = [
                quebra_hover(f"Nesta seleção, quem atua como {x.cargo} ganha, em média, {moeda(x.media)} por mês ({resp(x.n)}).")
                for x in pc.itertuples()
            ]
            fig = px.bar(
                pc,
                x="media",
                y="cargo",
                orientation="h",
                color="cargo",
                color_discrete_map=COR_CARGO,
                custom_data=["hover"],
                labels={"media": "Salário médio (R$/mês)", "cargo": ""},
            )
            fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
            fig.update_layout(height=max(420, len(pc) * 30), showlegend=False)
            mostrar(fig, f"Salário médio por profissão (só profissões com {MIN_N} respondentes ou mais)")
        with b:
            fx = d.faixa_salarial.value_counts().reindex(motor.ORDEM_FAIXAS, fill_value=0).reset_index()
            fx.columns = ["faixa", "quantidade"]
            total_fx = int(fx.quantidade.sum()) or 1
            fx["hover"] = [
                quebra_hover(f"Ganham {_minuscula(x.faixa)}: {resp(x.quantidade)} ({x.quantidade / total_fx:.0%} da seleção).")
                for x in fx.itertuples()
            ]
            fx["faixa"] = fx.faixa.map(_faixa_curta)
            fig = px.bar(
                fx,
                x="faixa",
                y="quantidade",
                color="faixa",
                color_discrete_sequence=rampa(len(fx)),
                custom_data=["hover"],
                labels={"faixa": "Faixa salarial (R$/mês)", "quantidade": "Respondentes"},
            )
            fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
            fig.update_xaxes(tickangle=-45, tickfont=dict(size=11))
            fig.update_layout(showlegend=False)
            mostrar(fig, "Quantos respondentes há em cada faixa de salário (R$ por mês)")

        with st.expander(f"Ver a tabela das {len(base.todas_profissoes)} profissões (inclui as que têm menos de {MIN_N} respondentes)"):
            pan = motor.panorama_todas_profissoes(base).copy()
            pan["faixa"] = pan.apply(lambda r: f"{moeda(r.p25_brasil)} a {moeda(r.p75_brasil)}", axis=1)
            pan_exib = pan[["cargo", "grupo", "n_brasil", "media_brasil", "faixa"]].rename(
                columns={"cargo": "Profissão", "grupo": "Grupo", "n_brasil": "Respondentes", "media_brasil": "Salário médio",
                         "faixa": "Faixa que reúne metade dos respondentes"}
            )
            st.dataframe(pan_exib.style.format({"Salário médio": moeda}), hide_index=True, width="stretch")
            st.caption(f"Profissões com menos de {MIN_N} respondentes aparecem aqui, mas os valores são só uma pista.")

        c, e = st.columns(2)
        with c:
            mt = d.modelo_trabalho.value_counts().reset_index()
            mt.columns = ["modelo", "quantidade"]
            total_mt = int(mt.quantidade.sum()) or 1
            mt["hover"] = [
                quebra_hover(f"Trabalham no modelo {x.modelo}: {resp(x.quantidade)} ({x.quantidade / total_mt:.0%} da seleção).")
                for x in mt.itertuples()
            ]
            fig = px.pie(mt, names="modelo", values="quantidade", hole=0.55, color_discrete_sequence=CORES_CAT,
                         custom_data=["hover"])
            fig.update_traces(
                hovertemplate="%{customdata[0]}<extra></extra>",
                textinfo="percent",
                textfont=dict(color=BG, size=14),
                marker=dict(line=dict(color=BG, width=2)),
            )
            fig = estilizar(fig)
            fig.update_layout(legend=dict(orientation="h", y=-0.05, yanchor="top", x=0), margin=dict(b=50))
            titulo_grafico("Proporção por modelo de trabalho")
            st.plotly_chart(fig, width="stretch", config=CFG)
        with e:
            try:
                gj = get_geojson()
                pr = motor.resumo(d, "regiao").set_index("regiao")
                ufs = [u for u in UF_REGIAO if UF_REGIAO[u] in pr.index]
                fig = go.Figure(
                    go.Choropleth(
                        geojson=gj,
                        locations=list(UF_REGIAO),
                        z=[0] * len(UF_REGIAO),
                        featureidkey="properties.sigla",
                        showscale=False,
                        hoverinfo="skip",
                        colorscale=[[0, "#252C46"], [1, "#252C46"]],
                        marker_line_color=BG,
                        marker_line_width=0.8,
                    )
                )
                if ufs:
                    fig.add_trace(
                        go.Choropleth(
                            geojson=gj,
                            locations=ufs,
                            featureidkey="properties.sigla",
                            colorscale=ESCALA,
                            z=[pr.loc[UF_REGIAO[u], "media"] for u in ufs],
                            text=[UF_REGIAO[u] for u in ufs],
                            customdata=[[quebra_hover(
                                f"Na região {UF_REGIAO[u]}, quem está nesta seleção ganha, em média, "
                                f"{moeda(pr.loc[UF_REGIAO[u], 'media'])} por mês ({resp(pr.loc[UF_REGIAO[u], 'n'])}).")]
                                for u in ufs],
                            hovertemplate="%{customdata[0]}<extra></extra>",
                            marker_line_color=BG,
                            marker_line_width=0.8,
                            colorbar=dict(
                                title=dict(text="R$/mês"), orientation="h", thickness=10, len=0.8, y=-0.02, yanchor="top"
                            ),
                        )
                    )
                fig.update_geos(fitbounds="geojson", visible=False, bgcolor="rgba(0,0,0,0)")
                fig = estilizar(fig)
                fig.update_layout(height=420, margin=dict(b=56))
                titulo_grafico("Salário médio por região do Brasil")
                st.plotly_chart(fig, width="stretch", config=CFG)
                st.caption(
                    "Cada estado mostra a média da sua região do Brasil (a pesquisa não tem dado por estado). "
                    f"Cinza: região com menos de {MIN_N} respondentes."
                )
            except Exception:
                st.info("Não foi possível carregar o mapa (GeoJSON indisponível).")

        h, i = st.columns(2)
        with h:
            pn = motor.resumo(d, "senioridade").pipe(motor._ordenar, "senioridade", ORDEM_NIVEL)
            pn["hover"] = [
                quebra_hover(f"Nesta seleção, quem está no nível {x.senioridade} ganha, em média, {moeda(x.media)} por mês ({resp(x.n)}).")
                for x in pn.itertuples()
            ]
            fig = px.bar(
                pn,
                x="senioridade",
                y="media",
                color="senioridade",
                color_discrete_map=COR_NIVEL,
                custom_data=["hover"],
                labels={"senioridade": "", "media": "Salário médio (R$/mês)"},
            )
            fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
            fig.update_layout(showlegend=False)
            mostrar(fig, "Salário médio por senioridade")
        with i:
            pe = motor.resumo(d, "experiencia").pipe(motor._ordenar, "experiencia", ORDEM_EXP)
            pe["hover"] = [
                quebra_hover(f"Nesta seleção, quem tem {_minuscula(x.experiencia)} de experiência em dados ganha, em média, "
                             f"{moeda(x.media)} por mês ({resp(x.n)}).")
                for x in pe.itertuples()
            ]
            fig = px.line(
                pe,
                x="experiencia",
                y="media",
                markers=True,
                custom_data=["hover"],
                labels={"experiencia": "Experiência em dados (anos)", "media": "Salário médio (R$/mês)"},
            )
            fig.update_traces(line=dict(color=TEAL, width=4), marker=dict(size=11, color=AMBAR),
                              hovertemplate="%{customdata[0]}<extra></extra>")
            mostrar(fig, "Salário médio por tempo de experiência")

    st.caption("Para proteger a privacidade (LGPD), mostramos só resultados somados, nunca as respostas de cada pessoa.")


# ----------------------------------------------------------------------
# SEÇÃO 3 — Hipóteses do pré-projeto (análise exploratória)
# ----------------------------------------------------------------------
with sec3:
    df = base.df
    st.markdown(
        '<h2 class="secao">Hipóteses do projeto</h2>'
        '<p class="secao-sub">Uma hipótese é uma pergunta que queremos testar com os dados. Aqui olhamos três delas, '
        "juntando todas as profissões. É uma primeira leitura das respostas da pesquisa: ela mostra o que aparece nos "
        "dados, mas não prova que uma coisa causa a outra.</p>",
        unsafe_allow_html=True,
    )

    # ---- H1
    st.markdown("#### H1. O que pesa mais no salário: o nível de carreira ou o lugar onde a pessoa mora?")
    st.caption("Quanto maior a barra, mais aquele fator ajuda a entender por que umas pessoas ganham mais que outras.")
    fatores = [("Senioridade", "senioridade"), ("Profissão", "cargo"), ("Experiência em dados", "experiencia"),
               ("Região do Brasil", "regiao"), ("Porte da empresa", "tamanho_empresa")]
    e2 = pd.DataFrame({"Fator": [f for f, _ in fatores], "pct": [motor.eta2(df, c) for _, c in fatores]})
    fig = px.bar(
        e2.sort_values("pct"),
        x="pct",
        y="Fator",
        orientation="h",
        color="pct",
        color_continuous_scale=ESCALA,
        labels={"pct": "Parte das diferenças de salário que o fator explica", "Fator": ""},
    )
    fig.update_xaxes(tickformat=".0%")
    fig.update_traces(hovertemplate="%{y} explica %{x:.1%} das diferenças<br>de salário entre os respondentes.<extra></extra>")
    fig.update_layout(separators=",.")  # vírgula decimal no tooltip ("31,6%")
    mostrar(fig, "Quanto cada fator explica das diferenças de salário")
    p_sen = float(e2.loc[e2.Fator == "Senioridade", "pct"].iloc[0])
    p_reg = float(e2.loc[e2.Fator == "Região do Brasil", "pct"].iloc[0])
    peso = "muito mais" if p_sen > 2 * p_reg else ("mais" if p_sen > p_reg else "menos")
    st.markdown(
        f'<div class="achado"><b>O que os dados mostram:</b> a senioridade explica cerca de {p_sen:.0%} das diferenças '
        f"de salário entre os respondentes, e a região do Brasil explica {p_reg:.0%}. Nesta base, o nível de carreira "
        f"pesa <b>{peso}</b> no salário do que a região onde a pessoa mora.</div>",
        unsafe_allow_html=True,
    )
    with st.expander("O que significa \"explicar\"? (detalhe técnico)"):
        st.markdown(
            "Cada barra é uma medida chamada **η²** (eta ao quadrado). Ela vai de 0% a 100%: 0% quer dizer que o fator "
            "não ajuda em nada a entender as diferenças de salário, e 100% quer dizer que ele explica tudo. Os fatores "
            "não somam 100% porque se misturam: quem tem mais experiência costuma ter mais senioridade, por exemplo."
        )

    # ---- H2
    st.markdown("#### H2. Em cada nível de carreira, qual grupo de profissões ganha mais?")
    st.caption("Cada cor é um grupo de profissões. Toque ou passe o mouse numa barra para ver o salário médio e quantos "
               "respondentes ela representa.")
    hg = motor.resumo(df, ["grupo", "senioridade"], min_n=MIN_N)
    if hg.empty:
        st.info(f"Ainda não há respondentes suficientes (mínimo de {MIN_N}) para mostrar esta comparação.")
    else:
        hg = hg.assign(hover=[
            quebra_hover(f"No nível {x.senioridade}, o grupo {x.grupo} ganha, em média, {moeda(x.media)} por mês ({resp(x.n)}).")
            for x in hg.itertuples()
        ])
        fig = px.bar(
            hg,
            x="senioridade",
            y="media",
            color="grupo",
            barmode="group",
            category_orders={"senioridade": ORDEM_NIVEL},
            color_discrete_map=GRUPO_COR,
            custom_data=["hover"],
            labels={"media": "Salário médio (R$/mês)", "senioridade": ""},
        )
        fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
        mostrar(fig, "Salário médio por grupo de profissões e nível de carreira")
        sr = hg[hg["senioridade"] == "Sênior"].sort_values("media")
        if len(sr) >= 2:
            alto, baixo = sr.iloc[-1], sr.iloc[0]
            st.markdown(
                f'<div class="achado"><b>O que os dados mostram:</b> entre as pessoas de nível Sênior, o grupo '
                f"<b>{_html.escape(str(alto.grupo))}</b> tem a maior média ({moeda(alto.media)}) e o grupo "
                f"<b>{_html.escape(str(baixo.grupo))}</b> tem a menor ({moeda(baixo.media)}). A comparação só inclui "
                f"grupos com pelo menos {MIN_N} respondentes naquele nível.</div>",
                unsafe_allow_html=True,
            )

    # ---- H3
    st.markdown("#### H3. Quais tecnologias os profissionais mais usam?")
    st.caption("Conta só quem respondeu à parte técnica da pesquisa. Cargos de gestão não respondem a ela.")
    freq_df = base.freq_geral.reset_index()
    freq_df.columns = ["tecnologia", "pct_uso"]
    freq_df["categoria"] = freq_df["tecnologia"].map({h: cat for cat, hs in base.categorias.items() for h in hs})
    top_tec = freq_df.sort_values("pct_uso", ascending=False).head(20).sort_values("pct_uso").copy()
    top_tec["hover"] = [
        quebra_hover(frase_tec(x.tecnologia, x.categoria, x.pct_uso, "dos respondentes técnicos")) + f"<br><i>Tipo: {x.categoria}</i>"
        for x in top_tec.itertuples()
    ]
    fig = px.bar(
        top_tec,
        x="pct_uso",
        y="tecnologia",
        color="categoria",
        orientation="h",
        color_discrete_map={c: hexhsl(h, 58, 64) for c, h in MATIZ_CAT.items()},
        custom_data=["hover"],
        labels={"pct_uso": "% dos respondentes que usam", "tecnologia": "", "categoria": "Tipo"},
    )
    fig.update_traces(hovertemplate="%{customdata[0]}<extra></extra>")
    fig.update_xaxes(tickformat=".0%")
    fig.update_layout(height=max(460, len(top_tec) * 24))
    mostrar(fig, "As 20 tecnologias e práticas mais usadas")
    t1, t2 = freq_df.sort_values("pct_uso", ascending=False).head(2).itertuples()
    st.markdown(
        f'<div class="achado"><b>O que os dados mostram:</b> a mais usada é <b>{_html.escape(str(t1.tecnologia))}</b>, '
        f"presente no dia a dia de {t1.pct_uso:.0%} dos respondentes técnicos, seguida de "
        f"<b>{_html.escape(str(t2.tecnologia))}</b> ({t2.pct_uso:.0%}).</div>",
        unsafe_allow_html=True,
    )

    with st.expander("Ver todas as tecnologias e práticas da base"):
        st.dataframe(
            freq_df.sort_values("pct_uso", ascending=False).assign(
                pct_formatado=lambda x: (x["pct_uso"] * 100).map("{:.1f}%".format)
            )[["categoria", "tecnologia", "pct_formatado"]].rename(
                columns={"categoria": "Tipo", "tecnologia": "Tecnologia ou prática", "pct_formatado": "% que usa"}
            ),
            hide_index=True,
            width="stretch",
        )
