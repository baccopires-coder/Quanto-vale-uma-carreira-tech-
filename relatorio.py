"""Relatório em PDF do diagnóstico ("Quanto vale uma carreira tech?").

Só formata resultados que o motor.py já calculou (e o texto da análise); não calcula nada novo.
Usa apenas reportlab: os gráficos são desenhados direto no PDF, sem depender de kaleido/Chrome.
"""
import io
import math
import re
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

import motor

PROJETO = "Quanto vale uma carreira tech?"
FONTE_DADOS = "State of Data Brasil 2025-2026 (Data Hackers + Bain & Company)"

ROXO = colors.HexColor("#7C3AED")
ROXO_CLARO = colors.HexColor("#F3EEFF")
TEAL = colors.HexColor("#0F9F8F")
AMBAR = colors.HexColor("#D98E04")
TEXTO = colors.HexColor("#1F2937")
CINZA = colors.HexColor("#6B7280")
LINHA = colors.HexColor("#E5E7EB")

LARGURA = A4[0] - 36 * mm  # largura útil (margens de 18 mm)

_BASE = dict(fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=TEXTO)
EST = {
    "corpo": ParagraphStyle("corpo", **_BASE, spaceAfter=5),
    "peq": ParagraphStyle("peq", **{**_BASE, "fontSize": 8, "leading": 10.5, "textColor": CINZA}),
    "cel": ParagraphStyle("cel", **{**_BASE, "fontSize": 8.5, "leading": 11}),
    "cel_b": ParagraphStyle("cel_b", **{**_BASE, "fontName": "Helvetica-Bold", "fontSize": 8.5, "leading": 11}),
    "cab": ParagraphStyle("cab", **{**_BASE, "fontName": "Helvetica-Bold", "fontSize": 8, "leading": 10, "textColor": colors.white}),
    "h1": ParagraphStyle("h1", **{**_BASE, "fontName": "Helvetica-Bold", "fontSize": 13, "leading": 16, "textColor": ROXO},
                         spaceBefore=14, spaceAfter=6, keepWithNext=True),
    "h2": ParagraphStyle("h2", **{**_BASE, "fontName": "Helvetica-Bold", "fontSize": 10.5, "leading": 14},
                         spaceBefore=8, spaceAfter=3, keepWithNext=True),
    "titulo": ParagraphStyle("titulo", **{**_BASE, "fontName": "Helvetica-Bold", "fontSize": 20, "leading": 24, "textColor": colors.white}),
    "sub": ParagraphStyle("sub", **{**_BASE, "fontSize": 10, "leading": 14, "textColor": colors.HexColor("#E9DDFF")}),
    "data": ParagraphStyle("data", **{**_BASE, "fontSize": 8.5, "textColor": colors.HexColor("#E9DDFF")}, alignment=2),
}


# ----------------------------------------------------------------------
# Utilitários de texto
# ----------------------------------------------------------------------

def _limpo(txt) -> str:
    """A fonte padrão do PDF (Helvetica) cobre o português, mas não emojis: o que ficar de fora é descartado."""
    return str(txt).replace("\u00a0", " ").encode("cp1252", "ignore").decode("cp1252")


def _t(txt) -> str:
    return escape(_limpo(txt))


def _moeda(v) -> str:
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def _sal_ok(v) -> bool:
    return v is not None and v == v and v > 0


def _inline(s: str) -> str:
    s = _t(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
    s = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<i>\1</i>", s)
    return s


def _markdown(texto: str) -> list:
    """Converte o markdown simples da análise (títulos, listas, negrito, itálico) em parágrafos do PDF."""
    fluxo = []
    for linha in str(texto).splitlines():
        if not linha.strip() or re.fullmatch(r"\s*[-*_]{3,}\s*", linha):
            continue
        m = re.match(r"^\s*(#{1,6})\s+(.*)", linha)
        if m:
            fluxo.append(Paragraph(_inline(m.group(2)), EST["h2"]))
            continue
        m = re.match(r"^\s*[-*\u2022]\s+(.*)", linha)
        if m:
            fluxo.append(Paragraph(_inline(m.group(1)), ParagraphStyle(
                "li", parent=EST["corpo"], leftIndent=14, bulletIndent=3, spaceAfter=3), bulletText="\u2022"))
            continue
        m = re.match(r"^\s*(\d+)[.)]\s+(.*)", linha)
        if m:
            fluxo.append(Paragraph(_inline(m.group(2)), ParagraphStyle(
                "num", parent=EST["corpo"], leftIndent=16, bulletIndent=2, spaceAfter=3), bulletText=f"{m.group(1)}."))
            continue
        fluxo.append(Paragraph(_inline(linha), EST["corpo"]))
    return fluxo


# ----------------------------------------------------------------------
# Gráficos (desenhados com reportlab.graphics)
# ----------------------------------------------------------------------

def _legenda(d, itens, y, largura):
    """Legenda centralizada: lista de (rótulo, cor, traço pontilhado?)."""
    tamanhos = [18 + 5 + stringWidth(r, "Helvetica", 8) for r, _, _ in itens]
    total = sum(tamanhos) + 18 * (len(itens) - 1)
    x = (largura - total) / 2
    for (rotulo, cor, tracejado), tam in zip(itens, tamanhos):
        d.add(Line(x, y + 3, x + 18, y + 3, strokeColor=cor, strokeWidth=2.4, strokeDashArray=[3, 2] if tracejado else None))
        d.add(String(x + 23, y, rotulo, fontName="Helvetica", fontSize=8, fillColor=TEXTO))
        x += tam + 18


def _radar(dg) -> Drawing:
    largura, altura, raio = LARGURA, 272, 100
    d = Drawing(largura, altura)
    cx, cy = largura / 2, 42 + raio
    eixos = [str(e) for e in dg["eixo"]]
    n = len(eixos)

    def ponto(i, v, extra=0.0):
        ang = math.pi / 2 - 2 * math.pi * i / n
        r = raio * max(0.0, min(float(v), 100.0)) / 100 + extra
        return cx + r * math.cos(ang), cy + r * math.sin(ang)

    for nivel in (25, 50, 75, 100):
        pts = [c for i in range(n) for c in ponto(i, nivel)]
        d.add(Polygon(pts, fillColor=None, strokeColor=LINHA, strokeWidth=0.7))
    for i in range(n):
        x, y = ponto(i, 100)
        d.add(Line(cx, cy, x, y, strokeColor=LINHA, strokeWidth=0.7))
    for nivel in (50, 100):
        d.add(String(cx + 2, cy + raio * nivel / 100 + 1, f"{nivel}%", fontName="Helvetica", fontSize=6, fillColor=CINZA))

    def serie(coluna, cor, tracejado=None, preenchimento=None, espessura=1.6):
        pts = [c for i, v in enumerate(dg[coluna]) for c in ponto(i, v)]
        d.add(Polygon(pts, fillColor=preenchimento, strokeColor=cor, strokeWidth=espessura, strokeDashArray=tracejado))

    serie("comunidade", CINZA, tracejado=[4, 3], espessura=1.2)
    serie("alvo", AMBAR, tracejado=[2, 2], espessura=1.8)
    serie("voce", TEAL, preenchimento=colors.Color(TEAL.red, TEAL.green, TEAL.blue, alpha=0.22), espessura=2.2)

    for i, nome in enumerate(eixos):
        x, y = ponto(i, 100, extra=9)
        ang = math.pi / 2 - 2 * math.pi * i / n
        cos, sen = math.cos(ang), math.sin(ang)
        ancora = "start" if cos > 0.3 else "end" if cos < -0.3 else "middle"
        y += 2 if sen > 0.3 else -8 if sen < -0.3 else -3
        d.add(String(x, y, _limpo(nome), textAnchor=ancora, fontName="Helvetica", fontSize=8, fillColor=TEXTO))

    _legenda(d, [("Você", TEAL, False), ("Perfil típico da profissão", AMBAR, True), ("Média da pesquisa", CINZA, True)], 6, largura)
    return d


def _barra(fracao, largura=78, altura=10) -> Drawing:
    d = Drawing(largura, altura)
    d.add(Rect(0, 2, largura, 6, fillColor=LINHA, strokeColor=None))
    d.add(Rect(0, 2, max(largura * max(min(fracao, 1.0), 0.0), 1.5), 6, fillColor=ROXO, strokeColor=None))
    return d


def _grafico_niveis(t, regiao):
    br, rg = t["nivel_br"], t["nivel_reg"]
    if br.empty:
        return None
    niveis = [str(x) for x in br["senioridade"]]
    series, nomes = [[float(v) for v in br["media"]]], ["Brasil"]
    if not rg.empty:
        por_nivel = {str(r.senioridade): float(r.media) for r in rg.itertuples()}
        series.append([por_nivel.get(n, 0.0) for n in niveis])
        nomes.append(regiao)

    altura = 190
    d = Drawing(LARGURA, altura)
    c = VerticalBarChart()
    c.x, c.y, c.width, c.height = 48, 34, LARGURA - 60, 122
    c.data = series
    c.categoryAxis.categoryNames = [_limpo(n) for n in niveis]
    c.categoryAxis.labels.fontName = "Helvetica"
    c.categoryAxis.labels.fontSize = 7.5
    c.categoryAxis.strokeColor = LINHA
    c.valueAxis.valueMin = 0
    c.valueAxis.labels.fontName = "Helvetica"
    c.valueAxis.labels.fontSize = 7
    c.valueAxis.labelTextFormat = lambda v: f"R$ {v / 1000:.0f} mil"
    c.valueAxis.strokeColor = LINHA
    c.valueAxis.gridStrokeColor = LINHA
    c.valueAxis.visibleGrid = True
    c.groupSpacing = 14
    c.barSpacing = 2
    c.barLabelFormat = lambda v: "" if not v else f"{v / 1000:.1f}".replace(".", ",") + " mil"
    c.barLabels.nudge = 6
    c.barLabels.fontName = "Helvetica"
    c.barLabels.fontSize = 6.5
    c.barLabels.fillColor = TEXTO
    for i, cor in enumerate((ROXO, TEAL)[: len(series)]):
        c.bars[i].fillColor = cor
        c.bars[i].strokeColor = None
    d.add(c)
    _legenda(d, [(nome, cor, False) for nome, cor in zip(nomes, (ROXO, TEAL))], altura - 14, LARGURA)
    return d


# ----------------------------------------------------------------------
# Blocos do documento
# ----------------------------------------------------------------------

def _tabela(linhas, larguras, extra=None, cabecalho=True):
    t = Table(linhas, colWidths=larguras, repeatRows=1 if cabecalho else 0)
    estilo = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINHA),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if cabecalho:
        estilo += [("BACKGROUND", (0, 0), (-1, 0), ROXO)]
    t.setStyle(TableStyle(estilo + (extra or [])))
    return t


def _cab(*textos):
    return [Paragraph(_t(x), EST["cab"]) for x in textos]


def _capa(agora):
    cel = [[Paragraph(_t(PROJETO), EST["titulo"]), ""],
           [Paragraph("Seu diagnóstico de carreira em tecnologia e dados", EST["sub"]),
            Paragraph(f"Gerado em {agora:%d/%m/%Y}", EST["data"])]]
    t = Table(cel, colWidths=[LARGURA * 0.72, LARGURA * 0.28])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ROXO), ("SPAN", (0, 0), (1, 0)),
        ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, 0), 14), ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 0), ("BOTTOMPADDING", (0, 1), (-1, 1), 14),
        ("VALIGN", (0, 1), (-1, 1), "BOTTOM"),
    ]))
    return t


def _perfil(perfil):
    fatos = [("Experiência", perfil["experiencia"]), ("Nível", perfil["nivel"]),
             ("Região", perfil["regiao"]), ("Interesse", perfil["interesse"])]
    if perfil.get("interesse_secundario", "Nenhum") != "Nenhum":
        fatos.append(("Em segundo lugar", perfil["interesse_secundario"]))
    celulas = [[Paragraph(f'<font color="#6B7280" size="7.5">{_t(k.upper())}</font><br/><b>{_t(v)}</b>', EST["cel"])
                for k, v in fatos]]
    t = Table(celulas, colWidths=[LARGURA / len(fatos)] * len(fatos))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ROXO_CLARO), ("BOX", (0, 0), (-1, -1), 0.5, LINHA),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    habs = perfil.get("habilidades") or []
    bloco = [t, Spacer(1, 6)]
    if habs:
        bloco.append(Paragraph(f"<b>Tecnologias e práticas que você usa ({len(habs)}):</b> " + _t(", ".join(habs)) + ".", EST["corpo"]))
    else:
        bloco.append(Paragraph("Nenhuma tecnologia foi informada; o ranking usou interesse, experiência e nível.", EST["corpo"]))
    return bloco


def _ranking(top, salarios):
    maximo = max(float(top["adequacao"].max()), 1e-9)
    linhas = [_cab("#", "Profissão", "Afinidade", "", "Salário médio (Brasil)", "Respondentes")]
    for pos, r in enumerate(top.itertuples(), start=1):
        sal = salarios.get(r.cargo)
        aviso = '<br/><font color="#B45309" size="7">poucos respondentes: leia com cautela</font>' if r.amostra_reduzida else ""
        linhas.append([
            Paragraph(f"<b>{pos}</b>", EST["cel"]),
            Paragraph(f"<b>{_t(r.cargo)}</b><br/><font color=\"#6B7280\" size=\"7.5\">{_t(r.grupo)}</font>", EST["cel"]),
            _barra(r.adequacao / maximo),
            Paragraph(f"<b>{r.adequacao:.0%}</b>", EST["cel"]),
            Paragraph(f"{_moeda(sal)}/mês" if _sal_ok(sal) else "Sem dado salarial", EST["cel"]),
            Paragraph(f"{int(r.n_total)}{aviso}", EST["cel"]),
        ])
    larg = [20, 168, 84, 34, 92, LARGURA - 398]
    return _tabela(linhas, larg, extra=[("BACKGROUND", (0, 1), (-1, 1), ROXO_CLARO)])


def _lacunas(dg):
    d = dg.assign(lacuna=dg["alvo"] - dg["voce"]).sort_values("lacuna", ascending=False)
    falta, fortes = d[d["lacuna"] > 1], d[d["lacuna"] <= 1]["eixo"].tolist()
    bloco = []
    if not falta.empty:
        linhas = [_cab("Área de conhecimento", "Você", "Alvo", "O que falta / referência")]
        for r in falta.itertuples():
            linhas.append([Paragraph(f"<b>{_t(r.eixo)}</b>", EST["cel"]), Paragraph(f"{r.voce:.0f}%", EST["cel"]),
                           Paragraph(f"{r.alvo:.0f}%", EST["cel"]), Paragraph(_t(r.falta), EST["cel"])])
        bloco.append(_tabela(linhas, [105, 38, 38, LARGURA - 181]))
    else:
        bloco.append(Paragraph("Você já está no nível do perfil típico desta profissão nos eixos avaliados.", EST["corpo"]))
    if fortes and not falta.empty:
        bloco += [Spacer(1, 5), Paragraph("<b>Já no nível da profissão:</b> " + _t(", ".join(fortes)) + ".", EST["corpo"])]
    return bloco


def _diagnostico(cargo, dg, n_cargo):
    bloco = [Paragraph(f"Diagnóstico: você x {_t(cargo)}", EST["h1"])]
    if cargo in motor.CARGOS_GESTAO:
        bloco.append(Paragraph(
            f"<b>{_t(cargo)}</b> é um cargo de gestão ou liderança. Na pesquisa, quem ocupa esses cargos não responde à parte "
            "técnica (tecnologias e ferramentas), por isso o diagnóstico compara só experiência e senioridade.", EST["corpo"]))
    elif n_cargo < motor.MIN_N:
        bloco.append(Paragraph(
            f"A base tem poucos respondentes de <b>{_t(cargo)}</b> (só {n_cargo}; o mínimo para uma leitura confiável é "
            f"{motor.MIN_N}). Veja os resultados como uma pista, não como regra.", EST["corpo"]))
    if dg is None or dg.empty:
        bloco.append(Paragraph("Não há dados suficientes para montar o diagnóstico desta profissão.", EST["corpo"]))
        return bloco
    if len(dg) >= 3:
        bloco.append(_radar(dg))
        bloco.append(Paragraph("Cada ponta é uma área de conhecimento. Em tecnologias, 100% significa usar todas as que costumam "
                               "ser usadas na profissão.", EST["peq"]))
    bloco.append(Paragraph("Lacunas identificadas", EST["h2"]))
    bloco += _lacunas(dg)
    return bloco


def _tecnologias(cargo, hab):
    if hab is None or hab.empty:
        return []
    tem = hab[hab["tem"]]
    falta = hab[~hab["tem"]]

    def lista(df, vazio):
        if df.empty:
            return Paragraph(vazio, EST["cel"])
        return Paragraph("<br/>".join(f"{_t(r.habilidade)} <font color=\"#6B7280\">({r.pct:.0%})</font>" for r in df.itertuples()), EST["cel"])

    linhas = [_cab("Você já usa", "Para desenvolver (mais usadas na profissão)"),
              [lista(tem, "Nenhuma das mais usadas."), lista(falta, "Você já usa todas as mais comuns.")]]
    t = _tabela(linhas, [LARGURA / 2] * 2, extra=[("VALIGN", (0, 1), (-1, 1), "TOP")])
    return [Paragraph(f"Tecnologias mais usadas em {_t(cargo)}", EST["h1"]), t,
            Paragraph("A porcentagem indica quantos respondentes da profissão usam cada tecnologia.", EST["peq"])]


def _salarios(cargo, t, regiao):
    br, rg = t["nivel_br"], t["nivel_reg"]
    bloco = [Paragraph(f"Salários em {_t(cargo)}", EST["h1"])]
    if br.empty:
        bloco.append(Paragraph(f"Nenhum nível de carreira tem {motor.MIN_N} respondentes ou mais para esta profissão.", EST["corpo"]))
        return bloco
    graf = _grafico_niveis(t, regiao)
    if graf is not None:
        bloco.append(Paragraph("Salário médio por nível de carreira (R$/mês)", EST["h2"]))
        bloco.append(graf)
    tem_reg = not rg.empty
    por_reg = {str(r.senioridade): r for r in rg.itertuples()} if tem_reg else {}
    cab = ["Nível", "Respondentes", "Média Brasil", "Metade dos respondentes fica entre"]
    if tem_reg:
        cab.append(f"Média {regiao}")
    linhas = [_cab(*cab)]
    for r in br.itertuples():
        linha = [Paragraph(f"<b>{_t(r.senioridade)}</b>", EST["cel"]), Paragraph(str(int(r.n)), EST["cel"]),
                 Paragraph(_moeda(r.media), EST["cel"]), Paragraph(f"{_moeda(r.p25)} a {_moeda(r.p75)}", EST["cel"])]
        if tem_reg:
            x = por_reg.get(str(r.senioridade))
            linha.append(Paragraph(f"{_moeda(x.media)} ({int(x.n)} resp.)" if x is not None else "sem dado suficiente", EST["cel"]))
        linhas.append(linha)
    larg = [92, 76, 76, 140] + ([LARGURA - 384] if tem_reg else [])
    if not tem_reg:
        larg[-1] = LARGURA - 244
    bloco += [Spacer(1, 4), _tabela(linhas, larg)]
    nota = "A coluna \"Metade dos respondentes fica entre\" mostra entre quais valores está o salário da metade \"do meio\" dos respondentes, sem contar os 25% que ganham menos nem os 25% que ganham mais."
    if regiao in motor.REGIOES and not tem_reg:
        nota += f" Na sua região ({_t(regiao)}) há menos de {motor.MIN_N} respondentes neste recorte, por isso mostramos só o Brasil."
    bloco.append(Paragraph(nota, EST["peq"]))
    return bloco


def _notas():
    itens = [
        "<b>Salário = média.</b> A pesquisa pergunta uma faixa por mês; usamos o valor do meio de cada faixa. Os valores são uma referência, não uma promessa.",
        f"<b>Respondentes.</b> É o número de pessoas por trás de cada resultado. Recortes só aparecem com pelo menos {motor.MIN_N} respondentes.",
        "<b>Afinidade.</b> Compara as tecnologias que você usa com as de cada profissão e considera o seu interesse. É um guia, não uma previsão.",
        "<b>Limites.</b> Participação voluntária, concentrada no Sudeste; dados de fim de 2025 e começo de 2026; a pesquisa não tem cidade, só macrorregião.",
        f"<b>Fonte.</b> {_t(FONTE_DADOS)}, dados abertos no Kaggle. Só resultados somados são usados, nunca respostas individuais.",
    ]
    return [Paragraph("Como ler estes números", EST["h1"])] + [Paragraph(i, EST["corpo"]) for i in itens]


def _rodape(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINHA)
    canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(18 * mm, 10 * mm, _limpo(f"{PROJETO}  |  Fonte: State of Data Brasil 2025-2026"))
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc.page}")
    canvas.restoreState()


# ----------------------------------------------------------------------
# API pública
# ----------------------------------------------------------------------

def gerar_pdf(perfil, top, salarios, cargo, dg, tabelas, hab, analise, n_cargo) -> bytes:
    """Monta o PDF do diagnóstico e devolve os bytes.

    perfil    dict do perfil (habilidades, experiencia, nivel, regiao, interesse)
    top       DataFrame de motor.principais()
    salarios  dict {cargo: salário médio Brasil}
    cargo     profissão escolhida para o diagnóstico
    dg        DataFrame de motor.diagnostico()
    tabelas   dict de motor.tabelas_cargo()
    hab       DataFrame de motor.habilidades_cargo()
    analise   texto em markdown da análise personalizada
    n_cargo   número de respondentes da profissão escolhida
    """
    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=20 * mm,
                          title=f"{PROJETO} - Diagnóstico", author=PROJETO, subject="Diagnóstico de carreira em tecnologia e dados")
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f",
                                                              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)],
                                       onPage=_rodape)])
    historia = [_capa(datetime.now()), Spacer(1, 4), Paragraph("Seu perfil", EST["h1"])]
    historia += _perfil(perfil)
    historia += [Paragraph(f"As {len(top)} áreas que mais combinam com você", EST["h1"]), _ranking(top, salarios),
                 Paragraph("A barra compara as áreas entre si. Nos cargos de gestão e liderança, que não respondem à parte técnica "
                           "da pesquisa, a afinidade considera interesse, nível e experiência.", EST["peq"])]
    historia += _diagnostico(cargo, dg, n_cargo)
    historia += [Paragraph("Análise personalizada", EST["h1"])] + _markdown(analise)
    historia += _tecnologias(cargo, hab)
    historia += _salarios(cargo, tabelas, perfil.get("regiao"))
    historia += [KeepTogether(_notas())]
    doc.build(historia)
    return buf.getvalue()
