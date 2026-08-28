#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o manifest.json das Boas Praticas a partir dos arquivos de dados/boas_praticas/.

Fonte de verdade: os arquivos de imagem publicados na pasta.
Saida: manifest.json na RAIZ do repositorio (mesma pasta do index.html), no formato
lido por bpNormalize()/renderBoasPraticas() do index.html:

  {
    "versao": "2026-08-28-a1b2c3",
    "gerado_em": "2026-08-28T18:40:00Z",
    "pasta": "dados/boas_praticas",
    "total": 3,
    "hash": "<sha256 do conteudo da pasta>",
    "boas_praticas": [
      {"ordem": 1, "arquivo": "dados/boas_praticas/01-conferencia-de-nf.webp",
       "titulo": "Conferencia de NF", "desc": "", "bytes": 91234}
    ]
  }

Regras de nome de arquivo (as mesmas que o painel administrativo usa ao baixar):
  NN-titulo.webp  ->  ordem = NN, titulo = "Titulo" (hifens/underscores viram espacos)
Arquivos sem NN entram no fim, em ordem alfabetica.

Legendas opcionais: dados/boas_praticas/legendas.json
  {"01-conferencia-de-nf.webp": {"titulo": "Conferencia de NF", "desc": "Texto..."}}
  ou  {"01-conferencia-de-nf.webp": "Texto..."}

Idempotente: se o conteudo da pasta nao mudou (mesmo hash), o manifest NAO e reescrito,
para o workflow nao gerar commit vazio.
Sem dependencias externas (stdlib apenas).
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_REL = "dados/boas_praticas"
PASTA = os.path.join(RAIZ, *PASTA_REL.split("/"))
SAIDA = os.path.join(RAIZ, "manifest.json")
EXTENSOES = {".webp", ".jpg", ".jpeg", ".png", ".gif", ".avif"}
IGNORAR = {"legendas.json", ".gitkeep", "readme.md", "README.md"}


MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "em", "no", "na", "nos", "nas",
              "para", "por", "com", "sem", "a", "o", "as", "os", "ao", "aos"}
SIGLAS = {"nf", "nfe", "nfse", "ncm", "cfop", "ipi", "icms", "cst", "sap", "mm", "pr",
          "xml", "xlsx", "csv", "pdf", "erp", "ti", "sku", "un", "ean", "cnpj", "epi"}


def titulo_de(nome):
    base = os.path.splitext(nome)[0]
    base = re.sub(r"^\s*\d+\s*[-_.]\s*", "", base)
    base = re.sub(r"[-_]+", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    if not base:
        return nome
    palavras = []
    for i, w in enumerate(base.split(" ")):
        b = w.lower()
        if b in SIGLAS:
            palavras.append(b.upper())
        elif i > 0 and b in MINUSCULAS:
            palavras.append(b)
        else:
            palavras.append(b[0].upper() + b[1:])
    return " ".join(palavras)


def ordem_de(nome, i):
    m = re.match(r"\s*(\d+)", nome)
    return int(m.group(1)) if m else 1000 + i


def ler_legendas():
    caminho = os.path.join(PASTA, "legendas.json")
    if not os.path.isfile(caminho):
        return {}
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except Exception as e:
        print("aviso: legendas.json ignorado (%s)" % e)
        return {}


def main():
    if not os.path.isdir(PASTA):
        print("pasta %s inexistente — nada a indexar" % PASTA_REL)
        return 0

    legendas = ler_legendas()
    nomes = sorted(
        n for n in os.listdir(PASTA)
        if n not in IGNORAR
        and not n.startswith(".")
        and os.path.isfile(os.path.join(PASTA, n))
        and os.path.splitext(n)[1].lower() in EXTENSOES
    )

    itens = []
    for i, nome in enumerate(nomes):
        tamanho = os.path.getsize(os.path.join(PASTA, nome))
        meta = legendas.get(nome, {})
        if isinstance(meta, str):
            meta = {"desc": meta}
        itens.append({
            "ordem": ordem_de(nome, i),
            "arquivo": PASTA_REL + "/" + nome,
            "titulo": meta.get("titulo") or titulo_de(nome),
            "desc": meta.get("desc") or meta.get("descricao") or "",
            "bytes": tamanho,
        })

    itens.sort(key=lambda it: (it["ordem"], it["arquivo"]))

    h = hashlib.sha256()
    for it in itens:
        h.update(("%s|%d|%s|%s\n" % (it["arquivo"], it["bytes"], it["titulo"], it["desc"])).encode("utf-8"))
    digest = h.hexdigest()

    if os.path.isfile(SAIDA):
        try:
            with open(SAIDA, encoding="utf-8") as f:
                atual = json.load(f)
            if atual.get("hash") == digest:
                print("manifest.json ja esta atualizado (%d itens) — nada a fazer" % len(itens))
                return 0
        except Exception:
            pass

    agora = datetime.now(timezone.utc)
    manifest = {
        "versao": "%s-%s" % (agora.strftime("%Y-%m-%d"), digest[:6]),
        "gerado_em": agora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pasta": PASTA_REL,
        "total": len(itens),
        "hash": digest,
        "boas_praticas": itens,
    }
    with open(SAIDA, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("manifest.json gerado: %d itens, versao %s" % (len(itens), manifest["versao"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
