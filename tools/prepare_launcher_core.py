"""Narrow build overlay: keep backend domain barrel imports out of the desktop."""

import argparse
import ast
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def domain_imports(path):
    """`app.domain.*` modules a file imports, at module level or inside a
    function. The barrel package itself is never one of them."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        names = []
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
            if node.module == "app.domain":
                names = [f"app.domain.{alias.name}" for alias in node.names]
        elif isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        found.update(n for n in names if n.startswith("app.domain."))
    return found


def required_domain_modules(sources):
    """Every domain module the desktop sources reach, transitively. 0.26.5
    shipped without app.domain.unlimited_items (imported by quick_items), so
    each «Objetos ∞» command failed inside the packaged core."""
    wanted, queue = set(), [m for s in sources for m in domain_imports(s)]
    while queue:
        module = queue.pop()
        if module in wanted:
            continue
        source = REPO / (module.replace(".", "/") + ".py")
        if not source.is_file():
            raise RuntimeError(f"Desktop import without a module file: {module}")
        wanted.add(module)
        queue.extend(domain_imports(source))
    return sorted(wanted)


def prepare(output):
    if output.exists():
        raise RuntimeError("Use a fresh source overlay directory")
    (output / "app/domain").mkdir(parents=True)
    sources = []
    for group in ("launcher", "save_parser"):
        target = output / "app" / group
        target.mkdir()
        for source in (REPO / "app" / group).glob("*.py"):
            shutil.copy2(source, target / source.name)
            sources.append(source)
    # These packages expose only the explicitly imported desktop contracts.
    for relative in ("app/__init__.py", "app/domain/__init__.py"):
        (output / relative).write_text('"""Launcher distribution namespace."""\n', encoding="utf-8")
    for module in required_domain_modules(sources):
        relative = module.replace(".", "/") + ".py"
        shutil.copy2(REPO / relative, output / relative)
    shutil.copy2(REPO / "companion/launcher/core-entry.py", output / "core-entry.py")


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("output", type=Path)
    prepare(cli.parse_args().output)
