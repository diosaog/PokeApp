from __future__ import annotations

from pathlib import Path
import streamlit as st

from conex_pkhex import PKHeXRuntime, get_bridge_path
from utils import DEFAULT_DLL_HINT


def try_auto_load_bridge() -> bool:
    """Try to load PKHeXBridge without user input."""
    try:
        if st.session_state.get("pkhex_loaded", False):
            if get_bridge_path():
                return True
            st.session_state.pkhex_loaded = False

        candidates = [
            st.session_state.get("pkhex_dll_path") or DEFAULT_DLL_HINT,
            r"Bridge\PKHeXBridge\bin\Release\net9.0\win-x64\publish",
            r"Bridge\PKHeXBridge\bin\Release\net9.0",
            r"Bridge\PKHeXBridge\bin\Debug\net9.0",
            r"Bridge\PKHeXBridge\bin\Release\net8.0\win-x64\publish",
            r"Bridge\PKHeXBridge\bin\Debug\net8.0\win-x64\publish",
        ]

        try:
            roots = [Path("Bridge"), Path("."), Path("tools")]
            seen = set()
            for root in roots:
                if not root.exists():
                    continue
                for exe in root.rglob("PKHeXBridge.exe"):
                    candidates.append(str(exe))
                    parent = str(exe.parent)
                    if parent not in seen:
                        seen.add(parent)
                        candidates.append(parent)
        except Exception:
            pass

        for cand in candidates:
            try:
                if not cand:
                    continue
                PKHeXRuntime.load(cand)
                st.session_state.pkhex_loaded = True
                st.session_state.pkhex_dll_path = cand
                st.session_state.setdefault("pkhex_mode", "auto")
                return True
            except Exception:
                continue
        st.session_state.pkhex_loaded = False
        return False
    except Exception:
        return False
