import streamlit as st
import pandas as pd
import re
import io
from word2number import w2n

# Função aprimorada para converter números por extenso para algarismos
def converter_numeros_por_extenso(texto):
    unidades = {
        "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "quatro": 4, "cinco": 5,
        "seis": 6, "sete": 7, "oito": 8, "nove": 9
    }
    dezenas = {
        "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
        "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
        "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
        "setenta": 70, "oitenta": 80, "noventa": 90
    }
    centenas = {
        "cem": 100, "cento": 100, "duzentos": 200, "trezentos": 300, "quatrocentos": 400,
        "quinhentos": 500, "seiscentos": 600, "setecentos": 700, "oitocentos": 800,
        "novecentos": 900
    }
    multiplicadores = {
        "mil": 1000, "milhão": 1000000, "milhões": 1000000, "bilhão": 1000000000,
        "bilhões": 1000000000
    }

    tokens = texto.split()
    resultado = []
    buffer = []
    i = 0

    def words_to_number(palavras):
        total = 0
        atual = 0
        for p in palavras:
            if p in unidades:
                atual += unidades[p]
            elif p in dezenas:
                atual += dezenas[p]
            elif p in centenas:
                atual += centenas[p]
            elif p in multiplicadores:
                fator = multiplicadores[p]
                if atual == 0:
                    atual = 1
                total += atual * fator
                atual = 0
            elif p == "e":
                continue  # Ignorar "e" sem alteração
            else:
                return None
        return total + atual

    while i < len(tokens):
        buffer.append(tokens[i])
        numero = words_to_number(buffer)
        if numero is not None:
            j = i + 1
            while j < len(tokens):
                nova_buffer = buffer + [tokens[j]]
                novo_numero = words_to_number(nova_buffer)
                if novo_numero is not None:
                    numero = novo_numero
                    buffer = nova_buffer
                    i = j
                    j += 1
                else:
                    break
            resultado.append(str(numero))
            buffer = []
        else:
            if len(buffer) > 1:
                resultado.extend(buffer[:-1])
                buffer = buffer[-1:]
            else:
                resultado.append(buffer[0])
                buffer = []
        i += 1

    resultado.extend(buffer)
    return " ".join(resultado)

def replace_full_word(text, term, replacement):
    return re.sub(rf"\b{re.escape(term)}\b", replacement, text, flags=re.IGNORECASE)

def replace_with_pattern(text, pattern, replacement):
    return re.sub(pattern, replacement, text, flags=re.IGNORECASE)

def gerar_corpus(df_textos, df_compostos, df_siglas):
    dict_compostos = {
        str(row["Palavra composta"]).lower(): str(row["Palavra normalizada"]).lower()
        for _, row in df_compostos.iterrows()
        if pd.notna(row["Palavra composta"]) and pd.notna(row["Palavra normalizada"])
    }

    dict_siglas = {
        str(row["Sigla"]).lower(): str(row["Significado"])
        for _, row in df_siglas.iterrows()
        if pd.notna(row["Sigla"]) and pd.notna(row["Significado"])
    }

    caracteres_especiais = {
        "-": "Hífen",
        ";": "Ponto e vírgula",
        '"': "Aspas duplas",
        "'": "Aspas simples",
        "…": "Reticências",
        "–": "Travessão",
        "(": "Parêntese esquerdo",
        ")": "Parêntese direito",
        "/": "Barra",
        "%": "Porcentagem"
    }
    contagem_caracteres = {k: 0 for k in caracteres_especiais}

    total_textos = 0
    total_siglas = 0
    total_compostos = 0
    total_remocoes = 0

    corpus_final = ""

    for _, row in df_textos.iterrows():
        texto = str(row.get("textos selecionados", ""))
        id_val = row.get("id", "")
        if not texto.strip():
            continue

        texto_corrigido = texto.lower()
        texto_corrigido = converter_numeros_por_extenso(texto_corrigido)  # Converte os números por extenso
        total_textos += 1

        # Substituição das siglas (corrigido o padrão de regex para parênteses)
        for sigla, significado in dict_siglas.items():
            # Substitui siglas no formato "(SIGLA)"
            texto_corrigido = replace_with_pattern(texto_corrigido, rf"\({sigla}\)", f"({significado})")
            texto_corrigido = replace_full_word(texto_corrigido, sigla, significado)
            total_siglas += 1

        for termo, substituto in dict_compostos.items():
            if termo in texto_corrigido:
                texto_corrigido = replace_full_word(texto_corrigido, termo, substituto)
                total_compostos += 1

        for char in caracteres_especiais:
            count = texto_corrigido.count(char)
            if count:
                texto_corrigido = texto_corrigido.replace(char, "_" if char == "/" else "")
                contagem_caracteres[char] += count
                total_remocoes += count

        texto_corrigido = re.sub(r"\s+", " ", texto_corrigido.strip())

        metadata = f"**** *ID_{id_val}"
        for col in row.index:
            if col.lower() not in ["id", "textos selecionados"]:
                metadata += f" *{col.replace(' ', '_')}_{str(row[col]).replace(' ', '_')}"

        corpus_final += f"{metadata}\n{texto_corrigido}\n"

    estatisticas = f"Textos processados: {total_textos}\n"
    estatisticas += f"Siglas removidas/substituídas: {total_siglas}\n"
    estatisticas += f"Palavras compostas substituídas: {total_compostos}\n"
    estatisticas += f"Caracteres especiais removidos: {total_remocoes}\n"
    for char, nome in caracteres_especiais.items():
        if contagem_caracteres[char] > 0:
            estatisticas += f" - {nome} ({char}) : {contagem_caracteres[char]}\n"

    return corpus_final, estatisticas

# Interface
st.set_page_config(layout="wide")
st.title("Gerador de corpus textual para IRaMuTeQ")

st.markdown("""
### 📌 Instruções para uso da planilha

Envie um arquivo do Excel **.xlsx** com a estrutura correta para que o corpus possa ser gerado automaticamente.

Sua planilha deve conter **três abas (planilhas internas)** com os seguintes nomes e finalidades:

1. **`textos_selecionados`** – onde ficam os textos a serem processados.  
2. **`dic_palavras_compostas`** – dicionário de expressões compostas.  
3. **`dic_siglas`** – dicionário de siglas.
""")

with open("gerar_corpus_
