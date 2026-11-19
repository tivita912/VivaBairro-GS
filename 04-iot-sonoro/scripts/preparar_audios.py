"""Converte WAVs para 16 kHz, mono, PCM16 em trechos de 5 s e confere o padrão."""

import argparse
import sys
import wave
from pathlib import Path

import numpy as np

TAXA_ALVO = 16000
DURACAO_PADRAO = 5.0
LIMITE_SILENCIO_DB = -50.0
LIMITE_ESTOURO = 0.999


def ler_wav(caminho: Path) -> tuple[np.ndarray, int, int, int]:
    """Lê um WAV PCM e devolve (amostras float -1..1 por canal, taxa, canais, bits)."""
    with wave.open(str(caminho), "rb") as arq:
        canais = arq.getnchannels()
        largura = arq.getsampwidth()
        taxa = arq.getframerate()
        bruto = arq.readframes(arq.getnframes())

    if largura == 1:
        dados = (np.frombuffer(bruto, dtype=np.uint8).astype(np.float32) - 128) / 128
    elif largura == 2:
        dados = np.frombuffer(bruto, dtype="<i2").astype(np.float32) / 32768
    elif largura == 3:
        b = np.frombuffer(bruto, dtype=np.uint8).reshape(-1, 3)
        inteiros = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8)
                    | (b[:, 2].astype(np.int32) << 16))
        inteiros = np.where(inteiros >= 1 << 23, inteiros - (1 << 24), inteiros)
        dados = inteiros.astype(np.float32) / (1 << 23)
    elif largura == 4:
        dados = np.frombuffer(bruto, dtype="<i4").astype(np.float32) / (1 << 31)
    else:
        raise ValueError(f"largura de amostra não suportada: {largura} bytes")

    return dados.reshape(-1, canais), taxa, canais, largura * 8


def para_mono(amostras: np.ndarray) -> np.ndarray:
    return amostras.mean(axis=1)


def reamostrar(sinal: np.ndarray, taxa_origem: int, taxa_destino: int) -> np.ndarray:
    """Reamostra com scipy, ou interpolação linear se não houver scipy."""
    if taxa_origem == taxa_destino:
        return sinal
    try:
        from math import gcd

        from scipy.signal import resample_poly

        g = gcd(taxa_origem, taxa_destino)
        return resample_poly(sinal, taxa_destino // g, taxa_origem // g).astype(np.float32)
    except ImportError:
        n_destino = int(round(len(sinal) * taxa_destino / taxa_origem))
        t_origem = np.arange(len(sinal)) / taxa_origem
        t_destino = np.arange(n_destino) / taxa_destino
        return np.interp(t_destino, t_origem, sinal).astype(np.float32)


def salvar_wav_pcm16(caminho: Path, sinal: np.ndarray, taxa: int) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(sinal, -1.0, 1.0)
    pcm = (pcm * 32767).astype("<i2")
    with wave.open(str(caminho), "wb") as arq:
        arq.setnchannels(1)
        arq.setsampwidth(2)
        arq.setframerate(taxa)
        arq.writeframes(pcm.tobytes())


def nivel_db(sinal: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.square(sinal)))) if len(sinal) else 0.0
    return 20 * np.log10(rms) if rms > 0 else -120.0


def cortar(sinal: np.ndarray, taxa: int, duracao: float) -> list[np.ndarray]:
    """Corta em trechos; sobra menor que metade é descartada, maior é completada com silêncio."""
    tamanho = int(duracao * taxa)
    trechos = []
    for inicio in range(0, len(sinal), tamanho):
        trecho = sinal[inicio:inicio + tamanho]
        if len(trecho) < tamanho:
            if len(trecho) < tamanho / 2:
                break
            trecho = np.pad(trecho, (0, tamanho - len(trecho)))
        trechos.append(trecho)
    return trechos


def converter(entrada: Path, saida: Path, rotulo: str, duracao: float, normalizar: bool) -> int:
    arquivos = sorted(entrada.glob("*.wav")) if entrada.is_dir() else [entrada]
    if not arquivos:
        print(f"Nenhum .wav encontrado em {entrada}")
        return 1

    contador = 0
    for arq in arquivos:
        try:
            amostras, taxa, canais, bits = ler_wav(arq)
        except (wave.Error, ValueError) as erro:
            print(f"[PULADO] {arq.name}: {erro}")
            continue

        sinal = reamostrar(para_mono(amostras), taxa, TAXA_ALVO)
        if normalizar:
            pico = float(np.max(np.abs(sinal))) if len(sinal) else 0.0
            if pico > 0:
                sinal = sinal * (0.9 / pico)

        trechos = cortar(sinal, TAXA_ALVO, duracao)
        for trecho in trechos:
            contador += 1
            destino = saida / f"{rotulo}.{contador:03d}.wav"
            salvar_wav_pcm16(destino, trecho, TAXA_ALVO)
        print(f"[OK] {arq.name}: {taxa} Hz, {canais} canal(is), {bits} bits "
              f"-> {len(trechos)} trecho(s) de {duracao:g} s")

    print(f"\n{contador} arquivo(s) salvos em {saida}")
    return 0


def verificar(pasta: Path) -> int:
    arquivos = sorted(pasta.rglob("*.wav"))
    if not arquivos:
        print(f"Nenhum .wav encontrado em {pasta}")
        return 1

    problemas = 0
    print(f"{'arquivo':40} {'taxa':>6} {'can':>3} {'bits':>4} {'dur(s)':>6} {'nível(dB)':>9}  situação")
    for arq in arquivos:
        try:
            amostras, taxa, canais, bits = ler_wav(arq)
        except (wave.Error, ValueError) as erro:
            print(f"{arq.name:40} erro ao ler: {erro}")
            problemas += 1
            continue

        mono = para_mono(amostras)
        dur = len(mono) / taxa
        db = nivel_db(mono)
        avisos = []
        if taxa != TAXA_ALVO:
            avisos.append(f"taxa {taxa} (esperado {TAXA_ALVO})")
        if canais != 1:
            avisos.append("não é mono")
        if bits != 16:
            avisos.append("não é PCM16")
        if abs(dur - DURACAO_PADRAO) > 0.1:
            avisos.append(f"duração {dur:.2f} s")
        if db < LIMITE_SILENCIO_DB:
            avisos.append("quase mudo")
        if np.mean(np.abs(mono) >= LIMITE_ESTOURO) > 0.001:
            avisos.append("som estourado")

        if avisos:
            problemas += 1
        situacao = "OK" if not avisos else "; ".join(avisos)
        print(f"{arq.name[:40]:40} {taxa:>6} {canais:>3} {bits:>4} {dur:>6.2f} {db:>9.1f}  {situacao}")

    print(f"\n{len(arquivos)} arquivo(s) conferidos, {problemas} com aviso.")
    return 0 if problemas == 0 else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara áudios para o Edge Impulse (16 kHz, mono, PCM16).")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_conv = sub.add_parser("converter", help="converte e corta WAVs no padrão da GS")
    p_conv.add_argument("entrada", type=Path, help="arquivo .wav ou pasta com .wav")
    p_conv.add_argument("saida", type=Path, help="pasta de saída")
    p_conv.add_argument("--rotulo", required=True, help="classe: sirene, buzina ou ambiente_rua")
    p_conv.add_argument("--duracao", type=float, default=DURACAO_PADRAO, help="segundos por trecho (padrão 5)")
    p_conv.add_argument("--normalizar", action="store_true", help="ajusta o volume para pico de 90%%")

    p_ver = sub.add_parser("verificar", help="confere se os WAVs estão no padrão")
    p_ver.add_argument("pasta", type=Path)

    args = parser.parse_args()
    if args.comando == "converter":
        return converter(args.entrada, args.saida, args.rotulo, args.duracao, args.normalizar)
    return verificar(args.pasta)


if __name__ == "__main__":
    sys.exit(main())
