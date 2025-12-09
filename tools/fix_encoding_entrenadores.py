import re
from pathlib import Path

p = Path('entrenadores.py')
src = p.read_text(encoding='utf-8', errors='ignore')

# 1) Normalizar placeholder de nivel en _badge_row: (None, "-")
src = re.sub(
    r"(Lv\.\{level\}\</span\>\"\) if level not in \(None,\s*)\"[^\"]*\"(\) else)",
    r'\1"-"\2',
    src,
)

# 2) Defaults rotos para level/nature en equipo (t.get)
src = re.sub(r"t\.get\('level',\s*'[^']*'\)", "t.get('level', '-')", src)
src = re.sub(r"t\.get\('nature',\s*'[^']*'\)", "t.get('nature', '-')", src)

# 3) Defaults rotos para level en cajas (p.get)
src = re.sub(r"p\.get\('level',\s*'[^']*'\)", "p.get('level', '-')", src)

# 4) Etiquetas rotas: Gnero, Regin
src = src.replace("G", "G")
src = src.replace("Regi", "Regi")  # noop safeguard

# 5) Lnea de encabezado Entrenador/Regin: forzar formato limpio
src = re.sub(
    r"\*\*Entrenador:\*\* \{jugador\}.*?\*\*Regi.*?:\*\* \{region\}",
    "**Entrenador:** {jugador}    **Regin:** {region}",
    src,
)

# 6) Gender symbol computation: reemplazar lnea por versin limpia
src = re.sub(
    r"gender_sym\s*=.*",
    "gender_sym = '' if gender == 'M' else ('' if gender == 'F' else '-')",
    src,
)

p.write_text(src, encoding='utf-8')
print('ok')
