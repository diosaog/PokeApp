from __future__ import annotations
from pathlib import Path

ROOT = Path('.')

# Pistas de mojibake comunes
BAD_HINTS = ['', '', '']

REPL = {
    # Palabras frecuentes en espaol con tildes
    'Pokémon': 'Pokmon', 'Pokédex': 'Pokdex',
    'Sesión': 'Sesin', 'Código': 'Cdigo', 'Heurística': 'Heurstica',
    'Género': 'Gnero', 'Región': 'Regin', 'campeón': 'campen', 'Campeón': 'Campen',
    # Variantes con  ya vistas
    'Pokmon': 'Pokmon', 'Poke': 'Pok', 'Sesin': 'Sesin', 'Cdigo': 'Cdigo', 'Regin': 'Regin', 'Gnero': 'Gnero',
}

def maybe_fix_text(s: str) -> str:
    fixed = s
    # Si hay signos de UTF-8 mal decodificado, intenta latin1utf8
    if any(h in fixed for h in BAD_HINTS):
        try:
            fixed = fixed.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
        except Exception:
            pass
    for a, b in REPL.items():
        fixed = fixed.replace(a, b)
    return fixed

def main() -> None:
    for p in ROOT.rglob('*.py'):
        if any(part.startswith('.venv') for part in p.parts) or 'Bridge' in p.parts:
            continue
        txt = p.read_text(encoding='utf-8', errors='ignore')
        if not any(h in txt for h in BAD_HINTS) and '' not in txt:
            continue
        new = maybe_fix_text(txt)
        if new != txt:
            p.write_text(new, encoding='utf-8')
            print('fixed', p)

if __name__ == '__main__':
    main()

