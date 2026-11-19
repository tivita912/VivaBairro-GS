"""Normalização conservadora do texto destinado ao leitor em português brasileiro."""
from dataclasses import dataclass
from datetime import date
import re
from typing import Protocol
import unicodedata

from .errors import ComponentUnavailable


@dataclass(frozen=True)
class SpeechText:
    text: str
    warnings: tuple[str, ...] = ()


class SpeechAdapter(Protocol):
    def adapt(self, text: str) -> SpeechText:
        """Preserva o sentido e avisos; normaliza marcação, siglas, datas e números."""
        ...


class UnconfiguredSpeechAdapter:
    def adapt(self, text: str) -> SpeechText:
        raise ComponentUnavailable("A adaptação para fala ainda não está integrada.")


class VerbatimSpeechAdapter:
    """Modo explícito para clientes que já enviam um texto preparado."""

    def adapt(self, text: str) -> SpeechText:
        from .conversation import checked_text
        return SpeechText(checked_text(text))


UNITS = "zero um dois três quatro cinco seis sete oito nove dez onze doze treze catorze quinze dezesseis dezessete dezoito dezenove".split()
TENS = "vinte trinta quarenta cinquenta sessenta setenta oitenta noventa".split()
HUNDREDS = "cento duzentos trezentos quatrocentos quinhentos seiscentos setecentos oitocentos novecentos".split()
MONTHS = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split()
ACRONYMS = {"SUS": "Sistema Único de Saúde", "UBS": "Unidade Básica de Saúde",
            "UPA": "Unidade de Pronto Atendimento", "CEP": "cê é pê", "CPF": "cê pê efe",
            "CNPJ": "cê ene pê jota", "ODS": "ó dê esse", "LGPD": "ele gê pê dê", "ONU": "Organização das Nações Unidas"}
NUMERIC = re.compile(r"(?<![\w/])(?:R\$[ \t]*)?[+−-]?\d+(?:[.,:/-]\d+)*(?:\s*%)?(?!\w)")
IDENTIFIER = re.compile(
    r"\b(?:protocolo|código|identificador|processo|cep|cpf|cnpj|telefone|disque|ligue)"
    r"(?:[ \t]+(?:n[º°o]\.?|número))?[ \t:]+(?:[A-Z]+[-/]?)?\d[\w./-]*\b", re.IGNORECASE)
URL = re.compile(r"https?://[^\s<>\[\]()]+", re.IGNORECASE)


def integer(value: int) -> str:
    if value < 20:
        return UNITS[value]
    if value < 100:
        tens, remainder = divmod(value, 10)
        return TENS[tens - 2] + (f" e {integer(remainder)}" if remainder else "")
    if value == 100:
        return "cem"
    if value < 1000:
        hundreds, remainder = divmod(value, 100)
        return HUNDREDS[hundreds - 1] + (f" e {integer(remainder)}" if remainder else "")
    scale, singular, plural = ((1000000, "milhão", "milhões") if value >= 1000000 else (1000, "mil", "mil"))
    quotient, remainder = divmod(value, scale)
    prefix = singular if quotient == 1 and scale == 1000 else f"{integer(quotient)} {singular if quotient == 1 else plural}"
    join = " e " if remainder < 100 or remainder % 100 == 0 else " "
    return prefix + (join + integer(remainder) if remainder else "")


def pronounce_number(token: str) -> str | None:
    if match := re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})|(\d{4})-(\d{2})-(\d{2})", token):
        parts = match.groups()
        day, month, year = map(int, parts[:3] if parts[0] else parts[3:][::-1])
        try:
            date(year, month, day)
        except ValueError:
            return None
        return f"{'primeiro' if day == 1 else integer(day)} de {MONTHS[month - 1]} de {integer(year)}"
    if match := re.fullmatch(r"(\d{1,2}):(\d{2})", token):
        hour, minute = map(int, match.groups())
        if hour > 23 or minute > 59:
            return None
        hours = "uma hora" if hour == 1 else "duas horas" if hour == 2 else f"{integer(hour)} horas"
        return hours + (f" e {integer(minute)}" if minute else "")
    if match := re.fullmatch(r"(R\$\s*)?([+−-])?(0|[1-9]\d{0,8})(?:,(\d{1,4}))?(\s*%)?", token):
        currency, sign, whole, decimals, percent = match.groups()
        sign_text = {"+": "mais ", "-": "menos ", "−": "menos "}.get(sign, "")
        if currency:
            if percent or (decimals and len(decimals) > 2):
                return None
            cents = int((decimals or "").ljust(2, "0"))
            money = f"{integer(int(whole))} {'real' if whole == '1' else 'reais'}"
            return sign_text + money + (f" e {integer(cents)} {'centavo' if cents == 1 else 'centavos'}" if cents else "")
        fraction = " vírgula " + " ".join(UNITS[int(digit)] for digit in decimals) if decimals else ""
        return sign_text + integer(int(whole)) + fraction + (" por cento" if percent else "")
    return None


def pronounce_url(url: str) -> str:
    symbols = {".": "ponto", ":": "dois pontos", "/": "barra", "-": "hífen", "_": "sublinhado", "?": "interrogação",
               "&": "e comercial", "=": "igual", "#": "cerquilha", "%": "por cento", "+": "mais", "@": "arroba"}
    spoken = re.sub(r"[^\w]|_|\d", lambda m: f" {symbols.get(m[0], UNITS[int(m[0])] if m[0].isdecimal() else m[0])} ", url)
    return " ".join(spoken.split())


class PortugueseSpeechAdapter:
    def adapt(self, text: str) -> SpeechText:
        from .conversation import checked_text

        text = checked_text(text)
        warnings = {}
        protected = []

        def preserve(value):
            protected.append(value)
            return chr(0xF0000 + len(protected) - 1)

        def link(match):
            value = match[0].rstrip(".,;:!?")
            return preserve(pronounce_url(value)) + match[0][len(value):]

        def number(match):
            spoken = pronounce_number(match[0])
            if spoken is None:
                warnings["Formas numéricas ambíguas ou inválidas foram preservadas."] = None
                return match[0]
            return spoken

        text = re.sub(r"(?ms)^\s*```[^\n]*\n(.*?)^\s*```", lambda m: preserve(m[1].strip()), text)
        text = re.sub(r"`([^`\n]+)`", lambda m: preserve(m[1]), text)
        text = re.sub(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", r"\1. Link: \2", text)
        text = URL.sub(link, text)
        text = IDENTIFIER.sub(lambda m: preserve(m[0]), text)
        text = re.sub(r"\b[A-Za-z]{1,12}-\d[\w./-]*\b", lambda m: preserve(m[0]), text)
        text = re.sub(r"(?m)^[ \t]*(?:#{1,6}\s+|>\s*|[-*+]\s+|\d+\.\s+)", "", text)
        text = re.sub(r"(?m)^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-*:?\s*$", "", text)
        text = re.sub(r"(\*\*|__|~~|\*|_)(?=\S)([^\n]+?)(?<=\S)\1", r"\2", text)
        text = re.sub(r"[\t ]*\|[\t ]*", ", ", text)
        text = re.sub(r"[0-9#*]\ufe0f?\u20e3", " ", text)
        text = "".join(" " if 0x1F000 <= ord(c) <= 0x1FAFF or
                       (unicodedata.category(c) == "So" and 0x2600 <= ord(c) <= 0x27BF) or
                       c in "\ufe0e\ufe0f\u200d\u20e3" else c for c in text)
        text = NUMERIC.sub(number, text)
        text = re.sub(r"\b(?:%s)\b" % "|".join(ACRONYMS), lambda m: ACRONYMS[m[0]], text)
        text = re.sub(r"[;]+\s*", ". ", text)
        text = re.sub(r"([.!?])\1+", r"\1", text)
        text = re.sub(r"(?<=[\w)\U000F0000-\U000F0FFF])\s*\n+\s*(?=\w)", ". ", text)
        text = re.sub(r"\s+", " ", text).strip(" ,")
        text = re.sub(r"[\U000F0000-\U000F0FFF]", lambda m: protected[ord(m[0]) - 0xF0000]
                      if ord(m[0]) - 0xF0000 < len(protected) else m[0], text)
        sentences = re.split(r"(?<=[.!?]) +", text)
        for i, sentence in enumerate(sentences):
            if len(sentence.split()) > 28:
                sentences[i] = re.sub(r",\s+(além disso|em seguida|por fim|depois disso)\b",
                                      lambda m: ". " + m[1].capitalize(), sentence, flags=re.IGNORECASE)
        if any(len(s.split()) > 28 for s in re.split(r"(?<=[.!?]) +", " ".join(sentences))):
            warnings["Trechos longos sem pausa segura foram preservados."] = None
        return SpeechText(checked_text(" ".join(sentences)), tuple(warnings))
