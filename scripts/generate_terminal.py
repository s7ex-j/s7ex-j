"""
Genera un GIF de terminal retro para el README del perfil de GitHub.
Basado en x0rzavi/github-readme-terminal (libreria `gifos`) + ascii_magic
para renderizar una foto como arte ANSI de puntos.

Instalacion local (para probarlo antes de subirlo):
    pip install --upgrade github-readme-terminal ascii_magic
    (requiere tambien ffmpeg instalado en el sistema)

Coloca tu foto de perfil (cuadrada, idealmente) en:
    assets/avatar.jpg

Uso:
    python scripts/generate_terminal.py
Genera assets/terminal-banner.gif
"""

import os
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

import gifos
from ascii_magic import AsciiArt

GITHUB_USER = "s7ex-j"
AVATAR_PATH = "assets/avatar.jpg"
OUTPUT_PATH = "assets/terminal-banner.gif"


def render_avatar_ascii(columns: int = 46) -> list:
    """Convierte la foto de perfil en arte ANSI (estilo 'puntos') y
    devuelve las lineas listas para insertar en el terminal.
    Si no hay foto, devuelve un placeholder en vez de fallar."""
    if not os.path.exists(AVATAR_PATH):
        return ["[Coloca una foto en assets/avatar.jpg para ver tu retrato aqui]"]

    art = AsciiArt.from_image(AVATAR_PATH)
    # monochrome=False devuelve el string ya con codigos ANSI de color
    ascii_str = art.to_ascii(columns=columns, monochrome=False)
    return ascii_str.split("\n")


def main():
    t = gifos.Terminal(width=760, height=560, xpad=15, ypad=15)

    time_now = datetime.now(ZoneInfo("America/Lima")).strftime(
        "%a %b %d %I:%M:%S %p %Z %Y"
    )

    # --- Pantalla de arranque ---
    t.toggle_show_cursor(False)
    t.gen_text("GIF_OS Boot v1.0", 1)
    t.gen_text("Lima, Peru -- UPN / ISIL", 2)
    t.gen_text("", 4, count=15)
    t.clear_frame()

    # --- Login simulado ---
    t.gen_text("GIF OS v1.0 (tty1)", 1, count=5)
    t.gen_text("login: ", 3, count=5)
    t.toggle_show_cursor(True)
    t.gen_typing_text("jharol", 3, contin=True)
    t.gen_text("", 4, count=5)
    t.toggle_show_cursor(False)
    t.gen_text("password: ", 4, count=5)
    t.toggle_show_cursor(True)
    t.gen_typing_text("*********", 4, contin=True)
    t.toggle_show_cursor(False)

    t.gen_text(f"Last login: {time_now} on tty1", 6)
    t.gen_prompt(7, count=5)
    prompt_col = t.curr_col
    t.toggle_show_cursor(True)
    t.gen_typing_text("\x1b[91mfetch.s", 7, contin=True)
    t.delete_row(7, prompt_col)
    t.gen_text("\x1b[92mfetch.sh\x1b[0m", 7, count=3, contin=True)

    # --- Stats reales de GitHub ---
    try:
        git_user_details = gifos.utils.fetch_github_stats(GITHUB_USER)
        top_languages = [lang[0] for lang in git_user_details.languages_sorted]
    except ZeroDivisionError:
        # Usuario sin PRs - usar fallback
        top_languages = ["Python", "SQL", "R", "LaTeX", "JavaScript"]
    except Exception as e:
        print(f"WARNING: Error fetching GitHub stats: {e}")
        top_languages = ["Python", "SQL", "R", "LaTeX", "JavaScript"]

    t.clear_frame()

    # --- Retrato en ASCII/ANSI (arriba del todo) ---
    avatar_lines = render_avatar_ascii(columns=46)
    row = 1
    for line in avatar_lines:
        t.gen_text(line, row, 1, count=1, contin=True)
        row += 1

    # --- Info del sistema (debajo del retrato, estilo neofetch) ---
    info_start_row = row + 1
    user_details_lines = f"""
\x1b[30;101mjharol@GitHub\x1b[0m
--------------
\x1b[96mRol objetivo: \x1b[93mAnalista de Datos Junior / BI\x1b[0m
\x1b[96mCarreras: \x1b[93mIng. Industrial (UPN) + Ciencia de Datos e IA (ISIL)\x1b[0m
\x1b[96mUbicacion: \x1b[93mLima, Peru\x1b[0m

\x1b[30;101mStack:\x1b[0m
--------------
\x1b[96mLenguajes: \x1b[93mPython, SQL, R\x1b[0m
\x1b[96mHerramientas: \x1b[93mPower BI, LaTeX, Git\x1b[0m
\x1b[96mTop lenguajes GitHub: \x1b[93m{', '.join(top_languages[:5])}\x1b[0m

\x1b[30;101mProyectos:\x1b[0m
--------------
\x1b[96m- demanda-delivery-v2: \x1b[93melasticidad + SQL + Power BI\x1b[0m
\x1b[96m- A.N.D.R.E.: \x1b[93mstacking de 4 modelos, Mundial 2026\x1b[0m
\x1b[96mORCID: \x1b[93m0009-0009-7897-3439\x1b[0m
"""
    t.gen_text(user_details_lines, info_start_row, 1, count=5, contin=True)

    t.gen_prompt(t.curr_row)
    t.toggle_show_cursor(True)
    t.gen_typing_text(
        "\x1b[92m# Habla conmigo sobre elasticidad de demanda o stacking de modelos :)",
        t.curr_row,
        contin=True,
    )
    t.gen_text("", t.curr_row, count=120, contin=True)

    t.gen_gif()

    os.makedirs("assets", exist_ok=True)
    # gifos creates output.gif in current working directory
    if os.path.exists("output.gif"):
        shutil.move("output.gif", OUTPUT_PATH)
        print(f"INFO: GIF generado en {OUTPUT_PATH}")
    else:
        # Try to find output.gif in common locations
        for path in ["output.gif", "./output.gif", "frames/output.gif"]:
            if os.path.exists(path):
                shutil.move(path, OUTPUT_PATH)
                print(f"INFO: GIF generado en {OUTPUT_PATH} (found at {path})")
                break
        else:
            print("ERROR: output.gif not found after generation")
            # List files for debugging
            for root, dirs, files in os.walk("."):
                for f in files:
                    if f.endswith(".gif"):
                        print(f"  Found GIF: {os.path.join(root, f)}")


if __name__ == "__main__":
    main()