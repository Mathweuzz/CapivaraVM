import argparse
import os
import sys
from typing import List

from capivara import __version__
from capivara.util.logging import configure_logger
from capivara.loader.loader import ClassLoader
from capivara.runtime.klass import RuntimeClass
from capivara.classfile.attributes import CodeAttribute
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

def _run_static_noargs(classpath: List[str], main_bin: str, entry: str, desc: str) -> int:
    """
    Carrega classe e executa método static <entry><desc> sem args.
    Suporta apenas retorno void ou int neste passo.
    """
    ld = ClassLoader(classpath)
    rc: RuntimeClass = ld.load_class(main_bin)

    m = rc.find_method(entry, desc)
    if not m:
        sys.stderr.write(f"[capivara] método não encontrado: {entry}{desc}\n")
        return EX_USAGE
    if (m.access_flags & FL.ACC_STATIC) == 0:
        sys.stderr.write(f"[capivara] método não é static: {entry}{desc}\n")
        return EX_USAGE

    code: CodeAttribute | None = None
    for a in m.attributes:
        if isinstance(a, CodeAttribute):
            code = a
            break
    if not code:
        sys.stderr.write("[capivara] método sem atributo Code\n")
        return EX_UNAVAILABLE

    interp = Interpreter()
    res = interp.exec_code(code.code, code.max_locals, code.max_stack)

    if res.kind == "int":
        print(f"RET: {res.int_value}")
    return EX_OK

def _cmd_run(args: argparse.Namespace) -> int:
    logger = configure_logger(args.loglevel)
    classpath = _split_classpath(args.classpath)
    _validate_classpath(classpath)

    main_bin = _normalize_main(args.main_class)
    logger.info("CapivaraVM %s bootstrap OK.", __version__)
    logger.info("Main class requisitada: %s", main_bin)
    logger.info("Classpath: %s", classpath)

    # Novo: se usuário informar entry/desc, executamos método static (sem args)
    if args.entry and args.desc:
        return _run_static_noargs(classpath, main_bin, args.entry, args.desc)

    # Comportamento antigo (preservado p/ testes anteriores):
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
    parser.add_argument(
        "--version", action="version", version=f"CapivaraVM {__version__}"
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    p_run = subparsers.add_parser(
        "run",
        help="Executa uma classe Java.",
        description="Executa uma classe Java. (Neste passo: use --entry/--desc para método static sem args.)",
    )
    p_run.add_argument("main_class", help="Nome da classe (ex.: pkg.Main).")
    p_run.add_argument("--cp", "--classpath", dest="classpath", default=".", help="Classpath (dirs/jars separados por ':').")
    p_run.add_argument("--log", dest="loglevel", default=None, help="Nível de log.")

    # Novos argumentos para este passo:
    p_run.add_argument("--entry", help="Nome do método static a executar (ex.: run).")
    p_run.add_argument("--desc", help="Descritor do método (ex.: ()I, ()V).")

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
        sys.exit(EX_USAGE)

if __name__ == "__main__":
    main()
