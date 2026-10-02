import re
import unicodedata

import pandas as pd


def normalizar_texto(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )
    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def limpar_valor(valor):
    if valor is None or pd.isna(valor):
        return ""

    return str(valor).strip()
