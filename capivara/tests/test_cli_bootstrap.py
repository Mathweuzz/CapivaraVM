import os
import sys
import subprocess
import tempfile
import shutil
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT_ROOT / "capivara" / "tests" / "fixtures"

class TestCLIBootstrap(unittest.TestCase):
    def test_help(self):
        """`python -m capivara.cli --help` deve sair com 0 e mostrar 'run'."""
        r = subprocess.run(
            [sys.executable, "-m", "capivara.cli", "--help"],
            capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("run", r.stdout)

    def test_run_without_main_shows_usage(self):
        """`python -m capivara.cli run` sem MainClass deve falhar com uso."""
        r = subprocess.run(
            [sys.executable, "-m", "capivara.cli", "run"],
            capture_output=True, text=True
        )
        # argparse retorna 2 quando falta argumento posicional
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("usage:", (r.stderr or r.stdout).lower())

    def test_stub_with_compiled_java_class(self):
        """
        Compila Hello.java com `javac --release 8`, depois chama o stub:
        deve retornar 69 (não implementado), mas aceitar/validar cp e classe.
        """
        # Verificar javac
        r = subprocess.run(["javac", "-version"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, msg="javac não encontrado no PATH")

        # Diretório de build temporário
        build_dir = PROJECT_ROOT / "build" / "test-classes"
        if build_dir.exists():
            shutil.rmtree(build_dir)
        build_dir.mkdir(parents=True, exist_ok=True)

        # Copiar Hello.java e compilar
        src_java = FIXTURES / "Hello.java"
        dst_java = build_dir / "Hello.java"
        dst_java.write_text(src_java.read_text(), encoding="utf-8")

        r = subprocess.run(
            ["javac", "--release", "8", "Hello.java"],
            cwd=str(build_dir),
            capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 0, msg=f"Erro ao compilar: {r.stderr}")

        # Executar o stub
        r = subprocess.run(
            [sys.executable, "-m", "capivara.cli", "run", "Hello", "--cp", str(build_dir)],
            capture_output=True, text=True
        )
        # 69 = EX_UNAVAILABLE (stub não implementado)
        self.assertEqual(r.returncode, 69, msg=(r.stdout + r.stderr))
        combined = (r.stdout + r.stderr)
        self.assertIn("interpretador ainda não implementado", combined)
        self.assertIn("Hello", combined)

if __name__ == "__main__":
    unittest.main(verbosity=2)