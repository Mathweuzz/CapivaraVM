import argparse
import os
import sys
from typing import List

from capivara import __version__
from capivara.util.logging import configure_logger

# Códigos de saída (inspirados em sysexits.h)
EX_OK = 0
EX_USAGE = 64          # uso incorreto de comando/argumento
EX_NOINPUT = 66        # entrada ausente (ex.: classpath inexiste)
EX_UNAVAILABLE = 69    # serviço indisponível (funcionalidade não implementada)

def _split_classpath(cp: str) -> List[str]:
    return [p for p in cp.split(":") if p]

def _normalize_main(name: str) -> str:
    # Aceita "pkg.Main" e normaliza para "pkg/Main"
    return name.replace(".", "/")

def _validate_classpath(paths: List[str]) -> None:
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        sys.stderr.write(
            f"[capivara] ERRO: entradas de classpath inexistentes: {missing}\n"
        )
        sys.exit(EX_NOINPUT)

def _cmd_run(args: argparse.Namespace) -> int:
    logger = configure_logger(args.loglevel)
    classpath = _split_classpath(args.classpath)
    _validate_classpath(classpath)

    main_bin = _normalize_main(args.main_class)
    logger.info("CapivaraVM %s bootstrap OK.", __version__)
    logger.info("Main class requisitada: %s", main_bin)
    logger.info("Classpath: %s", classpath)

    # Passo 1: ainda não implementado o interpretador/loader.
    sys.stderr.write(
        "CapivaraVM: interpretador ainda não implementado (Passo 1). "
        "Argumentos aceitos e validados com sucesso.\n"
    )
    return EX_UNAVAILABLE

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capivara",
        description="CapivaraVM — JVM interpretada em Python (alvo: Java 8).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"CapivaraVM {__version__}",
        help="Exibe a versão e sai.",
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    p_run = subparsers.add_parser(
        "run",
        help="Executa uma classe principal Java (stub no Passo 1).",
        description="Executa uma classe com método main(String[]). (Stub no Passo 1.)",
    )
    p_run.add_argument(
        "main_class",
        help="Nome da classe principal (ex.: pkg.Main). Aceita ponto ou barra.",
    )
    p_run.add_argument(
        "--cp",
        "--classpath",
        dest="classpath",
        default=".",
        help="Classpath (dirs e/ou .jar separados por ':'). Default='.'.",
    )
    p_run.add_argument(
        "--log",
        dest="loglevel",
        default=None,
        help="Nível de log (DEBUG, INFO, WARNING, ERROR). "
             "Sobrescreve $CAPIVARA_LOG.",
    )
    p_run.set_defaults(func=_cmd_run)

    return parser

def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        exit_code = args.func(args)
        sys.exit(exit_code)
    except AttributeError:
        # Nenhum subcomando → uso incorreto
        parser.print_usage(sys.stderr)
        sys.exit(EX_USAGE)

if __name__ == "__main__":
    main()