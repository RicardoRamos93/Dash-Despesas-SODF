#!/usr/bin/env python3
"""
Atualiza os dados do dashboard da Secretaria de Obras (UO 22101) e da
NOVACAP (UO 22201) a partir do arquivo de despesas baixado do Portal de
Dados Abertos do GDF (dados.df.gov.br).

Uso:
    python atualizar_dados.py caminho/para/despesas_2026.zip

O arquivo pode ter qualquer extensão (o portal às vezes entrega .csv que na
verdade é .zip). Os JSONs são gravados na pasta data/ ao lado deste script.

Dependência: pandas  (pip install pandas)
"""
import json
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

UOS = {"22101": "Secretaria de Obras", "22201": "NOVACAP"}
AMBAS = "SODF + NOVACAP"
SAIDA = Path(__file__).resolve().parent / "data"


def ler_tabela(zf: zipfile.ZipFile, padrao: str) -> tuple[pd.DataFrame, str]:
    """Lê uma tabela do SIGGO: latin-1, campos entre aspas separados por ¨."""
    nomes = [n for n in zf.namelist() if re.search(padrao, n.split("/")[-1], re.I)]
    if not nomes:
        sys.exit(f"Tabela '{padrao}' não encontrada no arquivo. Conteúdo: {zf.namelist()}")
    nome = nomes[0]
    texto = zf.read(nome).decode("latin-1")
    linhas = [l for l in texto.split("\r\n") if l.strip()]

    def campos(l: str) -> list[str]:
        l = l.strip()
        l = l[1:] if l.startswith('"') else l
        l = l[:-1] if l.endswith('"') else l
        return [c.strip() for c in l.split('"¨"')]

    cab = campos(linhas[0])
    dados = [c for c in map(campos, linhas[1:]) if len(c) == len(cab)]
    descartadas = len(linhas) - 1 - len(dados)
    if descartadas:
        print(f"  aviso: {descartadas} linha(s) com formato inesperado em {nome}")
    info = zf.getinfo(nome)
    data_arquivo = date(*info.date_time[:3]).isoformat()
    print(f"  {nome}: {len(dados):,} linhas (arquivo de {data_arquivo})")
    return pd.DataFrame(dados, columns=cab), data_arquivo


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
                         errors="coerce").fillna(0.0)


def cap(s: pd.Series) -> pd.Series:
    return s.str.strip().str.rstrip(".").str.capitalize()


def salvar(nome: str, df_ou_obj) -> None:
    obj = (json.loads(df_ou_obj.to_json(orient="records", force_ascii=False))
           if isinstance(df_ou_obj, pd.DataFrame) else df_ou_obj)
    (SAIDA / f"{nome}.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arquivo = Path(sys.argv[1])
    if not zipfile.is_zipfile(arquivo):
        sys.exit(f"{arquivo} não é um .zip. Baixe de novo o arquivo de despesas do portal.")

    print(f"Lendo {arquivo.name}...")
    with zipfile.ZipFile(arquivo) as zf:
        p, data_ext = ler_tabela(zf, r"^Despesa_Principal_\d{4}\.csv$")
        e, _ = ler_tabela(zf, r"^Despesa_Empenho_\d{4}\.csv$")

    for c in ["EMPENHADO", "LIQUIDADO", "TOTAL PAGO"]:
        p[c] = num(p[c])
    e["VALOR FINAL"] = num(e["VALOR FINAL"])
    exercicio = int(p["EXERCÍCIO"].iloc[0])

    # A tabela principal não traz a UO: atribui pelo programa de trabalho,
    # que pertence a uma única UO dentro de cada unidade gestora.
    mapa = e.groupby(["CÓDIGO UG", "CÓDIGO PROGRAMA DE TRABALHO"])["CÓDIGO UO"].first()
    p["UO"] = [mapa.get(k) for k in zip(p["CÓDIGO UG"], p["CÓDIGO PROGRAMA DE TRABALHO"])]
    sem_uo = p["UO"].isna() & (p["EMPENHADO"] != 0)
    if sem_uo.any():
        print(f"  aviso: R$ {p.loc[sem_uo, 'EMPENHADO'].sum():,.2f} empenhados sem UO identificada")

    # números das notas de rodapé
    ug_novacap, ug_sodf = "190201", "190101"
    info = {
        "exercicio": exercicio,
        "data_extracao": data_ext,
        "sodf_executado_pela_novacap": round(float(
            p.loc[(p.UO == "22101") & (p["CÓDIGO UG"] == ug_novacap), "EMPENHADO"].sum()), 2),
        "novacap_outras_uos": round(float(
            p.loc[(p["CÓDIGO UG"] == ug_novacap) & ~p.UO.isin(UOS), "EMPENHADO"].sum()), 2),
    }

    p = p[p.UO.isin(UOS)].copy()
    e = e[e["CÓDIGO UO"].isin(UOS)].copy()
    p["unidade"] = p.UO.map(UOS)
    e["unidade"] = e["CÓDIGO UO"].map(UOS)
    p = p.rename(columns={"EMPENHADO": "empenhado", "LIQUIDADO": "liquidado", "TOTAL PAGO": "pago"})
    vals = ["empenhado", "liquidado", "pago"]

    def com_ambas(d: pd.DataFrame) -> pd.DataFrame:
        t = d.copy()
        t["unidade"] = AMBAS
        return pd.concat([t, d])

    pa, ea = com_ambas(p), com_ambas(e)
    r2 = lambda d: d.round({c: 2 for c in vals if c in d})
    inv = pa[pa["GRUPO DE NATUREZA DESPESA"] == "INVESTIMENTOS"].groupby("unidade")

    k = pa.groupby("unidade")[vals].sum().reset_index()
    k["taxa_liquidacao"] = (k.liquidado / k.empenhado).round(4)
    k["taxa_pagamento"] = (k.pago / k.liquidado).round(4)
    k["investimento_liquidado"] = k.unidade.map(inv["liquidado"].sum()).fillna(0).round(2)
    k["investimento_empenhado"] = k.unidade.map(inv["empenhado"].sum()).fillna(0).round(2)
    salvar("kpis", r2(k))

    ea["mes"] = ea["LANCAMENTO"].str[:7]
    m = (ea.groupby(["unidade", "mes"])["VALOR FINAL"].sum().round(2).reset_index()
           .rename(columns={"VALOR FINAL": "empenhado"}))
    salvar("mensal", m)

    pa["acao"] = pa["CÓDIGO AÇÃO"] + " · " + cap(pa["AÇÃO"])
    a = pa.groupby(["unidade", "acao"])[vals].sum().reset_index()
    salvar("por_acao", r2(a.sort_values(["unidade", "empenhado"], ascending=[True, False])
                          .groupby("unidade").head(12)))

    g = pa.groupby(["unidade", "GRUPO DE NATUREZA DESPESA"])[vals].sum().reset_index()
    g = g.rename(columns={"GRUPO DE NATUREZA DESPESA": "grupo"})
    g["grupo"] = cap(g.grupo)
    salvar("por_grupo", r2(g))

    pa["programa_trabalho"] = cap(pa["PROGRAMA DE TRABALHO"])
    pa["codigo_pt"] = pa["CÓDIGO PROGRAMA DE TRABALHO"]
    t = pa.groupby(["unidade", "codigo_pt", "programa_trabalho"])[vals].sum().reset_index()
    t = t.sort_values(["unidade", "empenhado"], ascending=[True, False]).groupby("unidade").head(20)
    t["taxa_liquidacao"] = (t.liquidado / t.empenhado.replace(0, np.nan)).round(4)
    salvar("programas", r2(t))

    # só credores com CNPJ (pessoas físicas ficam de fora)
    pj = pa[pa["CNPJ CPF DO CREDOR"].str.fullmatch(r"\d{14}")]
    c = (pj.groupby(["unidade", "CREDOR"])[["empenhado", "pago"]].sum().reset_index()
           .rename(columns={"CREDOR": "credor"}))
    salvar("credores", r2(c.sort_values(["unidade", "pago"], ascending=[True, False])
                          .groupby("unidade").head(10)))

    salvar("info", info)

    tot = k[k.unidade == AMBAS].iloc[0]
    print(f"\nOK. Exercício {exercicio}, dados até {data_ext}.")
    print(f"SODF + NOVACAP: empenhado R$ {tot.empenhado:,.2f} | liquidado R$ {tot.liquidado:,.2f}")
    print(f"Arquivos gravados em {SAIDA}")


if __name__ == "__main__":
    SAIDA.mkdir(exist_ok=True)
    main()
