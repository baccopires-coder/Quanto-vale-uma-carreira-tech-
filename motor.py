from dataclasses import dataclass
from pathlib import Path
import re
import pandas as pd

PASTA = Path(__file__).parent
MIN_N = 20
URL_GEOJSON = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
TIPO_FAIXA = "de R$ 25.001/mês a R$ 3000/mês"
PONTO_MEDIO = {
    "Menos de R$ 1.000/mês": 500,
    "de R$ 1.001/mês a R$ 2.000/mês": 1500,
    "de R$ 2.001/mês a R$ 3.000/mês": 2500,
    "de R$ 3.001/mês a R$ 4.000/mês": 3500,
    "de R$ 4.001/mês a R$ 6.000/mês": 5000,
    "de R$ 6.001/mês a R$ 8.000/mês": 7000,
    "de R$ 8.001/mês a R$ 12.000/mês": 10000,
    "de R$ 12.001/mês a R$ 16.000/mês": 14000,
    "de R$ 16.001/mês a R$ 20.000/mês": 18000,
    "de R$ 20.001/mês a R$ 25.000/mês": 22500,
    "de R$ 25.001/mês a R$ 30.000/mês": 27500,
    "de R$ 30.001/mês a R$ 40.000/mês": 35000,
    "Acima de R$ 40.001/mês": 45000,
}
ORDEM_FAIXAS = list(PONTO_MEDIO)
ORDEM_NIVEL = ["Júnior", "Pleno", "Sênior", "Especialista/Staff+", "Gestão/Liderança"]
ORDEM_EXP = ["Menos de 1 ano", "de 1 a 2 anos", "de 3 a 4 anos", "de 5 a 6 anos", "de 7 a 10 anos", "Mais de 10 anos"]
REGIOES = ["Norte", "Nordeste", "Centro-oeste", "Sudeste", "Sul"]
PORTE = {
    "de 1 a 5": "Micro (1–10)", "de 6 a 10": "Micro (1–10)",
    "de 11 a 50": "Pequena (11–50)", "de 51 a 100": "Média (51–100)",
    "de 101 a 500": "Grande (100+)", "de 501 a 1.000": "Grande (100+)",
    "de 1.001 a 3.000": "Grande (100+)", "Acima de 3.000": "Grande (100+)",
}
ORDEM_PORTE = ["Micro (1–10)", "Pequena (11–50)", "Média (51–100)", "Grande (100+)"]
VINCULOS = ["Empregado (CLT)", "Empreendedor ou Empregado (CNPJ)", "Servidor Público", "Freelancer"]

CARGOS = {
    "Analista de Dados": "Analista de Dados/Data Analyst",
    "Analista de BI": "Analista de BI/BI Analyst",
    "Analista de Negócios": "Analista de Negócios/Business Analyst",
    "Analytics Engineer": "Analytics Engineer",
    "Engenheiro de Dados": "Engenheiro de Dados/Data Engineer/Data Architect",
    "Arquiteto de Dados": "Arquiteto de Dados/Data Architect",
    "Cientista de Dados": "Cientista de Dados/Data Scientist",
    "Engenheiro de ML/IA": "Engenheiro de Machine Learning/ML Engineer/AI Engineer",
    "Desenvolvedor / Eng. de Software": "Desenvolvedor/ Engenheiro de Software/ Analista de Sistemas",
    "Product Manager (PM / DPM / PO)": "Data Product Manager/ Product Manager (PM/APM/DPM/GPM/PO)",
    "Analista de Suporte / Técnico": "Analista de Suporte/Analista Técnico",
    "Outras Engenharias (não dev)": "Outras Engenharias (não inclui dev)",
    "Professor / Pesquisador": "Professor/Pesquisador",
    "Estatístico": "Estatístico",
    "Outras Profissões de Dados/Tech": "Outra Opção",
    "Tech Lead / Team Leader": "Team Leader/Tech Leader",
    "Supervisor / Coordenador": "Supervisor/Coordenador",
    "Gerente / Head": "Gerente/Head",
    "Diretor / VP": "Diretor/VP",
    "Sócio / C-Level (CTO/CDO/CIO/CEO)": "Sócio ou C-level (CEO, CDO, CIO, CTO etc)",
}

CARGOS_GESTAO = {
    "Tech Lead / Team Leader", "Supervisor / Coordenador", "Gerente / Head",
    "Diretor / VP", "Sócio / C-Level (CTO/CDO/CIO/CEO)",
}

GRUPO = {
    "Analista de Dados": "Análise/BI e Negócios", "Analista de BI": "Análise/BI e Negócios",
    "Analista de Negócios": "Análise/BI e Negócios",
    "Product Manager (PM / DPM / PO)": "Produto e Suporte",
    "Analista de Suporte / Técnico": "Produto e Suporte",
    "Analytics Engineer": "Engenharia e Arquitetura de Dados",
    "Engenheiro de Dados": "Engenharia e Arquitetura de Dados",
    "Arquiteto de Dados": "Engenharia e Arquitetura de Dados",
    "Desenvolvedor / Eng. de Software": "Engenharia de Software e Outras",
    "Outras Engenharias (não dev)": "Engenharia de Software e Outras",
    "Outras Profissões de Dados/Tech": "Engenharia de Software e Outras",
    "Cientista de Dados": "Ciência de Dados, ML/IA e Pesquisa",
    "Engenheiro de ML/IA": "Ciência de Dados, ML/IA e Pesquisa",
    "Estatístico": "Ciência de Dados, ML/IA e Pesquisa",
    "Professor / Pesquisador": "Ciência de Dados, ML/IA e Pesquisa",
    "Tech Lead / Team Leader": "Gestão e Liderança", "Supervisor / Coordenador": "Gestão e Liderança",
    "Gerente / Head": "Gestão e Liderança", "Diretor / VP": "Gestão e Liderança",
    "Sócio / C-Level (CTO/CDO/CIO/CEO)": "Gestão e Liderança",
}

COLUNAS = {
    "1.g_vive_no_brasil": "vive_brasil",
    "1.i.2_regiao_onde_mora": "regiao",
    "2.a_situação_de_trabalho": "contrato",
    "2.c_numero_de_funcionarios": "tamanho_empresa",
    "2.e_cargo_como_gestor": "cargo_gestor",
    "2.f_cargo_atual": "cargo_tecnico",
    "2.g_nivel": "senioridade",
    "2.h_faixa_salarial": "faixa_salarial",
    "2.i_tempo_de_experiencia_em_dados": "experiencia",
    "2.q_modelo_de_trabalho_atual": "modelo_trabalho",
}

BLOCOS = {
    "4.c.": "Linguagens", "4.d.": "Bancos de dados", "4.e.": "Nuvem",
    "4.g.": "BI e visualização", "4.b.": "Fontes e tipos de dados",
    "4.i.": "IA generativa na empresa", "4.j.": "IA generativa (produtividade)",
}

EXCLUIR = ("Não utilizo nenhuma", "Não uso soluções", "não é prioridade", "Não sei opinar")

def _rotulo_coluna(col: str) -> str:
    sem_prefixo = re.sub(r"^\d+\.[a-z]\.\d+[_\s]+", "", col).strip()
    if sem_prefixo.startswith("Fazemos todas as análises utilizando apenas Excel"):
        return "Excel / Planilhas Google (análise principal)"
    if sem_prefixo.startswith("Servidores On Premise"):
        return "Servidores On-Premise"
    return sem_prefixo

@dataclass
class Base:
    df: pd.DataFrame
    categorias: dict
    freq: pd.DataFrame
    freq_geral: pd.Series
    n_hab: pd.Series
    n_total: pd.Series

    @property
    def habilidades(self):
        return [h for hs in self.categorias.values() for h in hs]

    @property
    def todas_profissoes(self):
        return list(self.n_total.index)

def carregar_base() -> Base:
    csv = next((PASTA / "dados").glob("*.csv"), None)
    if csv is None:
        csv = next(PASTA.glob("*.csv"), None)
    if csv is None:
        raise FileNotFoundError("Coloque o CSV do State of Data dentro da pasta 'dados/' ou na raiz do projeto.")
    cab = pd.read_csv(csv, nrows=0).columns
    cols_hab = [c for c in cab if c.startswith(tuple(BLOCOS)) and not any(x in c for x in EXCLUIR)]
    rot = {c: _rotulo_coluna(c) for c in cols_hab}
    cat_de = {rot[c]: BLOCOS[c[:4]] for c in cols_hab}
    assert len(set(rot.values())) == len(rot), "rótulos de habilidade duplicados"
    df = pd.read_csv(csv, usecols=list(COLUNAS) + cols_hab, low_memory=False).rename(columns={**COLUNAS, **rot})
    df = df[(df["vive_brasil"] == 1) & df["contrato"].isin(VINCULOS)].copy()
    df["cargo_bruto"] = df["cargo_tecnico"].fillna(df["cargo_gestor"])
    df = df.dropna(subset=["faixa_salarial", "cargo_bruto", "regiao"])
    df = df[df["cargo_bruto"].isin(CARGOS.values())].copy()
    df["cargo"] = df["cargo_bruto"].map({v: k for k, v in CARGOS.items()})
    df["grupo"] = df["cargo"].map(GRUPO)
    df["senioridade"] = df["senioridade"].fillna("Gestão/Liderança")
    df["faixa_salarial"] = df["faixa_salarial"].replace({TIPO_FAIXA: "de R$ 25.001/mês a R$ 30.000/mês"})
    df["salario"] = df["faixa_salarial"].map(PONTO_MEDIO)
    df = df.dropna(subset=["salario"])
    df["tamanho_empresa"] = df["tamanho_empresa"].replace({"de 501 a 100": "de 501 a 1.000"}).map(PORTE)
    df["modelo_trabalho"] = (
        df["modelo_trabalho"].fillna("Não informado")
        .str.replace("Modelo ", "", regex=False)
        .str.replace(r"\s*\(.*\)", "", regex=True).str.capitalize()
    )
    habs = list(rot.values())
    df["resp_hab"] = df[habs].notna().any(axis=1)
    df[habs] = df[habs].fillna(0)
    hab = df[df["resp_hab"]]
    categorias = {c: [h for h in habs if cat_de[h] == c] for c in BLOCOS.values()}
    todos_cargos = [c for c in CARGOS.keys() if c in df["cargo"].unique()]
    freq = hab.groupby("cargo")[habs].mean().reindex(todos_cargos).fillna(0.0)
    n_hab = hab.groupby("cargo").size().reindex(todos_cargos).fillna(0).astype(int)
    n_total = df.groupby("cargo").size().reindex(todos_cargos).fillna(0).astype(int)
    return Base(df=df, categorias=categorias, freq=freq, freq_geral=hab[habs].mean(), n_hab=n_hab, n_total=n_total)

INTERESSES = {
    "Análise, BI e Negócios": ["Analista de Dados", "Analista de BI", "Analista de Negócios", "Outras Profissões de Dados/Tech"],
    "Engenharia e Arquitetura de Dados": ["Engenheiro de Dados", "Analytics Engineer", "Arquiteto de Dados"],
    "Ciência de Dados, ML/IA e Estatística": ["Cientista de Dados", "Engenheiro de ML/IA", "Estatístico", "Professor / Pesquisador"],
    "Desenvolvimento de Software e Outras Engenharias": ["Desenvolvedor / Eng. de Software", "Outras Engenharias (não dev)"],
    "Produto e Suporte Técnico": ["Product Manager (PM / DPM / PO)", "Analista de Suporte / Técnico"],
    "Gestão e Liderança": ["Tech Lead / Team Leader", "Supervisor / Coordenador", "Gerente / Head", "Diretor / VP", "Sócio / C-Level (CTO/CDO/CIO/CEO)"],
    "Sem preferência": [],
}

def ranking(base: Base, hab_usuario, interesse="Sem preferência", nivel=None, experiencia=None, top_k=12) -> pd.DataFrame:
    meu = [h for h in hab_usuario if h in base.habilidades]
    u = pd.Series(0.0, index=base.freq.columns)
    u[meu] = 1.0
    eh_lider = nivel in ("Sênior", "Especialista/Staff+", "Gestão/Liderança") or experiencia in ("de 5 a 6 anos", "de 7 a 10 anos", "Mais de 10 anos")
    linhas = []
    for cargo in base.todas_profissoes:
        n_tot = int(base.n_total[cargo])
        n_h = int(base.n_hab[cargo])
        bonus = 1.0 if cargo in INTERESSES.get(interesse, []) else 0.0
        if cargo in CARGOS_GESTAO:
            # Gestão só pontua alto se a pessoa demonstra querer esse caminho (interesse ou nível atual).
            # Antes, qualquer perfil sênior pontuava ~36% em todos os cargos de gestão e engolia o topo do ranking.
            quer_gestao = bonus > 0 or nivel == "Gestão/Liderança"
            base_lider = 0.55 if eh_lider else 0.15
            adequacao = 0.65 * base_lider + 0.35 * bonus if quer_gestao else 0.10
            cobertura = 0.0
        else:
            f = base.freq.loc[cargo]
            tipicas = f[f >= 0.20].nlargest(top_k)
            cobertura = float(tipicas[tipicas.index.isin(meu)].sum() / tipicas.sum()) if len(tipicas) else 0.0
            d = f - base.freq_geral
            cos = float(u @ f / ((u @ u) ** 0.5 * (f @ f) ** 0.5 + 1e-9)) if meu else 0.0
            lift = float(u @ d / (((u @ u) ** 0.5) * ((d @ d) ** 0.5) + 1e-9)) if meu else 0.0
            adequacao = 0.85 * (0.5 * cos + 0.5 * max(lift, 0.0)) + 0.15 * bonus
        linhas.append({
            "cargo": cargo, "grupo": GRUPO.get(cargo, "Outros"), "adequacao": float(adequacao),
            "cobertura": float(cobertura), "n_total": n_tot, "n_hab": n_h, "amostra_reduzida": n_tot < MIN_N,
        })
    return pd.DataFrame(linhas).sort_values("adequacao", ascending=False, kind="stable").reset_index(drop=True)

def principais(rk: pd.DataFrame, interesse="Sem preferência", nivel=None, k=5, max_gestao=2) -> pd.DataFrame:
    """Seleciona as k áreas mais aderentes. Cargos de gestão ficam limitados a max_gestao,
    a menos que a pessoa tenha interesse em liderança ou já esteja em Gestão/Liderança."""
    if interesse == "Gestão e Liderança" or nivel == "Gestão/Liderança":
        return rk.head(k).reset_index(drop=True)
    escolhidos, n_gestao = [], 0
    for idx, r in rk.iterrows():
        if r["cargo"] in CARGOS_GESTAO:
            if n_gestao >= max_gestao:
                continue
            n_gestao += 1
        escolhidos.append(idx)
        if len(escolhidos) == k:
            break
    return rk.loc[escolhidos].reset_index(drop=True)

def habilidades_cargo(base: Base, cargo, hab_usuario, top=15) -> pd.DataFrame:
    if cargo not in base.freq.index or base.n_hab.get(cargo, 0) == 0:
        return pd.DataFrame(columns=["habilidade", "pct", "tem"])
    f = base.freq.loc[cargo]
    f = f[f > 0].nlargest(top)
    return pd.DataFrame({"habilidade": f.index, "pct": f.values, "tem": [h in set(hab_usuario) for h in f.index]})

def resumo(df, por, min_n=MIN_N) -> pd.DataFrame:
    cols = (por if isinstance(por, list) else [por]) + ["n", "mediana", "media", "p25", "p75"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    r = df.groupby(por, observed=False)["salario"].agg(
        n="size", mediana="median", media="mean",
        p25=lambda s: s.quantile(0.25), p75=lambda s: s.quantile(0.75)
    ).reset_index()
    return r[r["n"] >= min_n]

def _ordenar(r, col, ordem):
    if r.empty:
        return r
    r = r.copy()
    r[col] = pd.Categorical(r[col], ordem, ordered=True)
    return r.sort_values(col).reset_index(drop=True)

def panorama_todas_profissoes(base: Base, regiao=None) -> pd.DataFrame:
    df = base.df
    geral = resumo(df, "cargo", min_n=1).rename(columns={
        "n": "n_brasil", "mediana": "mediana_brasil", "media": "media_brasil",
        "p25": "p25_brasil", "p75": "p75_brasil"
    })
    geral["grupo"] = geral["cargo"].map(GRUPO)
    geral["amostra_reduzida"] = geral["n_brasil"] < MIN_N
    if regiao in REGIOES:
        dr = df[df["regiao"] == regiao]
        reg = resumo(dr, "cargo", min_n=1)[["cargo", "n", "mediana"]].rename(columns={"n": "n_regiao", "mediana": "mediana_regiao"})
        geral = geral.merge(reg, on="cargo", how="left")
    else:
        geral["n_regiao"] = 0
        geral["mediana_regiao"] = None
    return geral.sort_values("mediana_brasil", ascending=False).reset_index(drop=True)

def tabelas_cargo(base: Base, cargo, regiao=None, min_n=MIN_N) -> dict:
    d = base.df[base.df["cargo"] == cargo]
    dr = d[d["regiao"] == regiao] if regiao in REGIOES else d.iloc[0:0]
    return {
        "geral_br": resumo(d, "cargo", min_n=1),
        "nivel_br": _ordenar(resumo(d, "senioridade", min_n=min_n), "senioridade", ORDEM_NIVEL),
        "nivel_reg": _ordenar(resumo(dr, "senioridade", min_n=min_n), "senioridade", ORDEM_NIVEL),
        "exp_br": _ordenar(resumo(d, "experiencia", min_n=min_n), "experiencia", ORDEM_EXP),
        "exp_reg": _ordenar(resumo(dr, "experiencia", min_n=min_n), "experiencia", ORDEM_EXP),
        "regioes": resumo(d, "regiao", min_n=min_n),
    }

def eta2(df, col) -> float:
    g = df.groupby(col)["salario"]
    media = df["salario"].mean()
    return float((g.size() * (g.mean() - media) ** 2).sum() / ((df["salario"] - media) ** 2).sum())

def sumario(base: Base, perfil: dict, rk: pd.DataFrame) -> dict:
    # rk já deve vir recortado nas áreas priorizadas (ver principais)
    def tab(t):
        return {str(r[t.columns[0]]): {"mediana": int(r.mediana), "n": int(r.n)} for _, r in t.iterrows()}
    areas = []
    for _, r in rk.iterrows():
        t = tabelas_cargo(base, r.cargo, perfil.get("regiao"), min_n=MIN_N)
        hab = habilidades_cargo(base, r.cargo, perfil["habilidades"], top=10)
        med_geral = int(t["geral_br"]["mediana"].iloc[0]) if not t["geral_br"].empty else None
        areas.append({
            "cargo": r.cargo, "grupo": r.grupo, "adequacao_pct": round(r.adequacao * 100),
            "n_total": int(r.n_total), "amostra_reduzida": bool(r.amostra_reduzida),
            "salario_mediano_geral_brasil": med_geral,
            "habilidades_que_voce_tem": [{"habilidade": h.habilidade, "pct_profissionais": round(h.pct * 100)} for h in hab.itertuples() if h.tem],
            "habilidades_a_desenvolver": [{"habilidade": h.habilidade, "pct_profissionais": round(h.pct * 100)} for h in hab.itertuples() if not h.tem][:6],
            "salario_mediano_por_senioridade_brasil": tab(t["nivel_br"]),
            "salario_mediano_por_senioridade_na_sua_regiao": tab(t["nivel_reg"]),
            "salario_mediano_por_experiencia_brasil": tab(t["exp_br"]),
        })
    return {
        "perfil": perfil, "total_profissoes_na_pesquisa": len(base.todas_profissoes),
        "total_areas_priorizadas": len(areas), "areas": areas,
        "limitacoes": [
            "salário informado em faixas (usamos o ponto médio)",
            "amostra voluntária, concentrada no Sudeste",
            "dados de fim de 2025 / início de 2026",
            f"recortes cruzados exibidos apenas quando n >= {MIN_N}; profissões com n < {MIN_N} aparecem com mediana geral sinalizada",
            "cargos de gestão não respondem ao bloco de ferramentas técnicas no questionário original",
            "a pesquisa não tem cidade: só macrorregião",
        ],
    }

NIVEL_VALOR = {"Júnior": 20, "Pleno": 45, "Sênior": 70, "Especialista/Staff+": 90, "Gestão/Liderança": 100}
ROTULO_EIXO = {
    "Linguagens": "Linguagens", "Bancos de dados": "Bancos de dados", "Nuvem": "Nuvem",
    "BI e visualização": "BI e visualização", "Fontes e tipos de dados": "Fontes de dados",
    "IA generativa (produtividade)": "IA (produtividade)",
}

def _valor_exp(e) -> float:
    return (ORDEM_EXP.index(e) + 1) / len(ORDEM_EXP) * 100 if e in ORDEM_EXP else 0.0

def diagnostico(base: Base, perfil: dict, cargo: str) -> pd.DataFrame:
    meu = set(perfil.get("habilidades", []))
    linhas = []
    if cargo in base.freq.index and base.n_hab.get(cargo, 0) > 0:
        f = base.freq.loc[cargo]
        for cat, eixo_nome in ROTULO_EIXO.items():
            hs = base.categorias.get(cat, [])
            if not hs:
                continue
            fc = f[hs]
            tip = fc[fc >= 0.05].nlargest(8)
            if tip.empty:
                tip = fc[fc > 0].nlargest(3)
            peso = tip.sum()
            if peso <= 0:
                continue
            faltam = tip[~tip.index.isin(meu)].sort_values(ascending=False).head(3)
            linhas.append({
                "eixo": eixo_nome,
                "voce": float(tip[tip.index.isin(meu)].sum() / peso * 100),
                "alvo": float((tip ** 2).sum() / peso * 100),
                "comunidade": float((tip * base.freq_geral[tip.index]).sum() / peso * 100),
                "falta": ", ".join(f"{h} ({v:.0%})" for h, v in faltam.items()),
            })
    d = base.df
    dc = d[d["cargo"] == cargo]
    for eixo, col, conv, voce in [
        ("Experiência", "experiencia", _valor_exp, _valor_exp(perfil.get("experiencia"))),
        ("Senioridade", "senioridade", lambda x: NIVEL_VALOR.get(x, 0.0), NIVEL_VALOR.get(perfil.get("nivel"), 0.0)),
    ]:
        tipico = dc[col].mode()
        linhas.append({
            "eixo": eixo, "voce": float(voce),
            "alvo": float(dc[col].map(conv).mean()) if not dc.empty else 0.0,
            "comunidade": float(d[col].map(conv).mean()),
            "falta": f"Perfil mais comum na profissão: {tipico.iloc[0]}" if len(tipico) else "",
        })
    return pd.DataFrame(linhas)
