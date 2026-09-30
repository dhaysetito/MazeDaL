DEFAULT_THEME: dict[str, str] = {
    "path": (
        "\x1b[48;5;15m"
    ),
    "entry": (
        "\x1b[48;5;15m"
        "\x1b[38;5;196m"
    ),
    "exit": (
        "\x1b[48;5;15m"
        "\x1b[38;5;27m"
    ),
    "wall": "\x1b[38;5;240m",
    "bg": "\x1b[48;5;15m",
    "wall_block": "⬛",
    "path_block": "  ",
    "entry_block": "🟥",
    "exit_block": "🟩",
    "solve_block": "🟨",
    "point_block": "🟦",
    "reset": "\x1b[0m",
}

NORD_THEME: dict[str, str] = {
    "path": (
        "\x1b[38;5;15m"
        "\x1b[48;5;230m"
    ),
    "entry": "\033[32m",
    "exit": "\033[31m",
    "wall": "\033[38;5;130m",
    "bg": "\033[30m",
    "wall_block": "██",
    "path_block": "  ",
    "entry_block": "██",
    "exit_block": "██",
    "solve_block": "··",
    "reset": "\033[0m",
}

DRACULA_THEME: dict[str, str] = {
    "path": "\x1b[38;5;212m",
    "entry": "\x1b[38;5;84m",
    "exit": "\x1b[38;5;203m",
    "wall": "\x1b[38;5;61m",
    "bg": "\x1b[48;5;236m",
    "wall_block": "██",
    "path_block": "  ",
    "entry_block": "🚬",
    "exit_block": "❤️ ",
    "solve_block": "💃 ",
    "reset": "\x1b[0m",
}

LUFFY_THEME: dict[str, str] = {
    "path": (
        "\x1b[48;5;160m"
    ),
    "entry": (
        "\x1b[48;5;160m"
    ),
    "exit": (
        "\x1b[48;5;160m"
    ),
    "wall": "\x1b[38;5;221m",
    "bg": "\x1b[48;5;160m",
    "wall_block": "🟨",
    "path_block": "  ",
    "entry_block": "👒",
    "exit_block": "🏝️ ",
    "solve_block": "🍖",
    "reset": "\x1b[0m",
}

ZORO_THEME: dict[str, str] = {
    "path": (
        "\x1b[48;5;232m"
    ),
    "entry": "\x1b[48;5;232m",
    "exit": "\x1b[48;5;232m",
    "wall": "\x1b[38;5;34m",
    "bg": "\x1b[48;5;232m",
    "wall_block": "🟩",
    "path_block": "  ",
    "entry_block": "⚔️ ",
    "exit_block": "🍶",
    "solve_block": "❓",
    "reset": "\x1b[0m",
}

BROOK_THEME: dict[str, str] = {
    "path": "\x1b[48;5;232m",
    "entry": (
        "\x1b[48;5;232m"
        "\x1b[38;5;25m"
    ),
    "exit": (
        "\x1b[48;5;232m"
        "\x1b[38;5;25m"
    ),
    "wall": "\x1b[38;5;25m",
    "bg": "\x1b[48;5;232m",
    "wall_block": "🟦",
    "path_block": "  ",
    "entry_block": "🎻",
    "exit_block": "🐋",
    "solve_block": "♪♪",
    "reset": "\x1b[0m",
}

GAME_THEME: dict[str, str] = {
    "path": (
        "\x1b[48;5;234m"
    ),
    "entry": (
        "\x1b[48;5;234m"
        "\x1b[38;5;196m"
    ),
    "exit": (
        "\x1b[48;5;234m"
        "\x1b[38;5;27m"
    ),
    "wall": "\x1b[38;5;15m",
    "bg": "\x1b[48;5;234m",
    "wall_block": "🧱",
    "path_block": "  ",
    "entry_block": "👻",
    "exit_block": "🪦 ",
    "solve_block": "👻",
    "reset": "\x1b[0m",
}

THEMES: dict[str, tuple[str, dict[str, str]]] = {
    "1": ("Default", DEFAULT_THEME),
    "2": ("Nord", NORD_THEME),
    "3": ("Dracula", DRACULA_THEME),
    "4": ("Luffy", LUFFY_THEME),
    "5": ("Zoro", ZORO_THEME),
    "6": ("Brook", BROOK_THEME),
    "7": ("Game", GAME_THEME),
}
