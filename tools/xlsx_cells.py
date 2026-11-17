"""Leitor de celulas de um .xlsx, sem carregar a pasta de trabalho inteira.

O i3ET tem 198 guias e mais de 80 MB. Abrir tudo para ler uma guia custa
minutos; aqui se le so o XML da guia pedida, em uma passada. Vem o valor que o
Excel gravou na ultima vez em que calculou (nao se recalcula nada) e, a pedido,
a marca de que a celula tem formula.

Blocos:
    XL1  textos compartilhados (sharedStrings.xml)
    XL2  nome da guia -> arquivo XML
    XL3  grade da guia: {(linha, coluna): valor}
    XL4  conversao entre letras e numeros de coluna, e enderecos
"""

from __future__ import annotations

import html
import re
import zipfile

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


# --------------------------------------------------------------------------
# BLOCO XL4 -- colunas e enderecos
# --------------------------------------------------------------------------
def col2n(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n


def n2col(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def addr(row: int, col: int) -> str:
    return f"{n2col(col)}{row}"


class Workbook:
    """Uma pasta de trabalho aberta para leitura de guias avulsas."""

    def __init__(self, path: str):
        self.path = path
        self.zip = zipfile.ZipFile(path)
        self._sst: list[str] | None = None
        self._sheets: dict[str, str] | None = None

    # ----------------------------------------------------------------------
    # BLOCO XL1 -- textos compartilhados
    #   Le      : xl/sharedStrings.xml
    #   Devolve : a lista de textos, na ordem dos indices usados nas celulas
    # ----------------------------------------------------------------------
    def shared_strings(self) -> list[str]:
        if self._sst is None:
            xml = self.zip.read("xl/sharedStrings.xml").decode("utf-8")
            out = []
            for si in re.finditer(r"<si>(.*?)</si>|<si/>", xml, flags=re.S):
                corpo = si.group(1) or ""
                # <rPh> e a leitura fonetica; nao faz parte do texto.
                corpo = re.sub(r"<rPh.*?</rPh>", "", corpo, flags=re.S)
                partes = re.findall(r"<t[^>]*>(.*?)</t>", corpo, flags=re.S)
                out.append(html.unescape("".join(partes)))
            self._sst = out
        return self._sst

    # ----------------------------------------------------------------------
    # BLOCO XL2 -- nome da guia -> arquivo XML
    #   Le      : xl/workbook.xml e xl/_rels/workbook.xml.rels
    #   Devolve : {nome da guia: caminho dentro do zip}
    # ----------------------------------------------------------------------
    def sheets(self) -> dict[str, str]:
        if self._sheets is None:
            wb = self.zip.read("xl/workbook.xml").decode("utf-8")
            rels = self.zip.read("xl/_rels/workbook.xml.rels").decode("utf-8")
            alvo = {}
            for rel in re.finditer(r"<Relationship ([^>]*)/>", rels):
                a = dict(re.findall(r'(\w+)="([^"]*)"', rel.group(1)))
                alvo[a["Id"]] = a["Target"]
            out = {}
            for sh in re.finditer(r"<sheet ([^>]*)/>", wb):
                a = dict(re.findall(r'([\w:]+)="([^"]*)"', sh.group(1)))
                out[html.unescape(a["name"])] = "xl/" + alvo[a["r:id"]].lstrip("/")
            self._sheets = out
        return self._sheets

    # ----------------------------------------------------------------------
    # BLOCO XL3 -- grade da guia
    #   Le      : o XML da guia
    #   Devolve : {(linha, coluna): valor}; com formulas=True, tambem o
    #             conjunto das celulas que tem formula
    #   Tipos   : numero -> float; texto -> str; logico -> bool; erro -> str
    # ----------------------------------------------------------------------
    def grid(self, sheet: str, *, formulas: bool = False):
        textos = self.shared_strings()
        xml = self.zip.read(self.sheets()[sheet]).decode("utf-8")
        valores: dict[tuple[int, int], object] = {}
        com_formula: set[tuple[int, int]] = set()
        celula = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)', re.S)
        for m in celula.finditer(xml):
            col, lin, attrs, corpo = m.group(1), int(m.group(2)), m.group(3), m.group(4) or ""
            chave = (lin, col2n(col))
            if "<f" in corpo:
                com_formula.add(chave)
            tipo = re.search(r'\bt="(\w+)"', attrs)
            tipo = tipo.group(1) if tipo else "n"
            v = re.search(r"<v[^>]*>(.*?)</v>", corpo, re.S)   # <v xml:space="preserve">
            if tipo == "inlineStr":
                valor = html.unescape("".join(re.findall(r"<t[^>]*>(.*?)</t>", corpo, re.S)))
            elif v is None:
                continue
            elif tipo == "s":
                valor = textos[int(v.group(1))]
            elif tipo in ("str", "e"):
                valor = html.unescape(v.group(1))
            elif tipo == "b":
                valor = v.group(1) == "1"
            else:
                valor = float(v.group(1))
            if valor == "":
                continue
            valores[chave] = valor
        return (valores, com_formula) if formulas else valores
