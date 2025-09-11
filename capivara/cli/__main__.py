import argparse
import os
import sys
from typing import List

from capivara import __version__
from capivara.util.logging import configure_logger
from capivara.loader.loader import ClassLoader
from capivara.util import flags as FL
from capivara.interp.loop import Interpreter

EX_OK = 0
EX_USAGE = 64
EX_NOINPUT = 66
EX_UNAVAILABLE = 69

def _split_classpath(cp: str) -> List[str]:
    return [p for p in cp.split(":") if p]

def _normalize_main(name: str) -> str:
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

    if args.entry and args.desc:
        ld = ClassLoader(classpath)
        interp = Interpreter(ld)
        res = interp.execute_static_entry(main_bin, args.entry, args.desc)
        if res.kind == "int":
            print(f"RET: {res.int_value}")
        return EX_OK

    sys.stderr.write(
        "CapivaraVM: interpretador ainda não implementado para 'main' padrão "
        "(sem --entry/--desc neste passo). Argumentos aceitos e validados.\n"
    )
    return EX_UNAVAILABLE

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capivara",
        description="CapivaraVM — JVM interpretada em Python (alvo: Java 8).",
    )
    parser.add_argument("--version", action="version", version=f"CapivaraVM {__version__}")

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    p_run = subparsers.add_parser(
        "run",
        help="Executa uma classe Java.",
        description="Executa uma classe Java. (Neste passo: use --entry/--desc para método static sem args ou com params int.)",
    )
    p_run.add_argument("main_class", help="Nome da classe (ex.: pkg.Main).")
    p_run.add_argument("--cp", "--classpath", dest="classpath", default=".", help="Classpath (dirs/jars separados por ':').")
    p_run.add_argument("--log", dest="loglevel", default=None, help="Nível de log.")
    p_run.add_argument("--entry", help="Nome do método a executar (ex.: run).")
    p_run.add_argument("--desc", help="Descritor do método (ex.: ()I, (I)I, ()V).")
    p_run.set_defaults(func=_cmd_run)
    return parser

def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        exit_code = args.func(args)
        sys.exit(exit_code)
    except AttributeError:
        parser.print_usage(sys.stderr)
        sys.exit(64)

if __name__ == "__main__":
    main()