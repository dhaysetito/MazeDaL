from pathlib import Path

from exceptions import ConfigError, MazeError


class Parser:
    """Maze configuration parser."""
    def __init__(self, file_name: str = "config.txt") -> None:
        """
        Initialize configuration parser.

        Args:
            file_name: Configuration file path.
        """
        self.file_name = file_name
        self.width: int | None = None
        self.height: int | None = None
        self.entry: tuple[int, int] | None = None
        self.exit: tuple[int, int] | None = None
        self.output_file: str | None = None
        self.perfect: bool | None = None
        self.seed: int | None = None
        self.algorithm: str = "BFS"
        self.load_file: str | None = None

        self._read_file()

    def _read_file(self) -> None:
        """
        Read and validate configuration file.

        Parses configuration entries line by
        line while aggregating validation
        errors.
        """
        errors: list[ConfigError] = []
        try:
            with open(self.file_name, "r") as file:
                for line in file:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        self._parse_line(line)
                    except ConfigError as e:
                        errors.append(e)

        except FileNotFoundError:
            raise ConfigError.missing_file(f"[FILE] `{self.file_name}`")

        try:
            self._validate_required_fields()
        except ConfigError as e:
            errors.insert(0, e)

        if errors:
            raise ConfigError.aggregate(errors)

    def _parse_line(self, line: str) -> None:
        """
        Parse configuration line.

        Validates supported keys and converts
        configuration values into typed
        attributes.

        Args:
            line: Raw configuration line.
        """
        key, _, value = line.partition("=")
        key = key.strip().upper()
        value = value.strip()

        if key == "WIDTH":
            try:
                self.width = int(value)
            except ValueError as e:
                raise ConfigError.invalid_int(f"[{key}]") from e

            if self.width <= 0 or self.width > 50:
                raise ConfigError.invalid_bound(f"[{key}]")

        elif key == "HEIGHT":
            try:
                self.height = int(value)
            except ValueError as e:
                raise ConfigError.invalid_int("[HEIGHT]") from e

            if self.height <= 0 or self.height > 50:
                raise ConfigError.invalid_bound("[HEIGHT]")

        elif key == "ENTRY":
            try:
                x_str, y_str = value.split(",")
                x = int(x_str.strip())
                y = int(y_str.strip())

                self.entry = (x, y)

            except Exception as e:
                raise ConfigError.invalid_coordinates(f"[{key}]") from e

            if self.width is None or self.height is None:
                raise ConfigError(
                    (f"[{key}]"),
                    "WIDTH and HEIGHT must be defined before ENTRY"
                    )
            if x < 0 or x >= self.width or y < 0 or y >= self.height:
                raise ConfigError.invalid_bound_coordinates(
                    (f"[{key}]"), self.width, self.height
                    )

        elif key == "EXIT":
            try:
                x_str, y_str = value.split(",")
                x = int(x_str.strip())
                y = int(y_str.strip())
                self.exit = (x, y)
            except Exception as e:
                raise ConfigError.invalid_coordinates(f"[{key}]") from e

            if self.width is None or self.height is None:
                raise ConfigError(
                    (f"[{key}]"),
                    "WIDTH and HEIGHT must be defined before EXIT"
                    )
            if x < 0 or x >= self.width or y < 0 or y >= self.height:
                raise ConfigError.invalid_bound_coordinates(
                    (f"[{key}]"), self.width, self.height
                    )
            if self.exit == self.entry:
                raise MazeError("Entry and exit must be different")

        elif key == "OUTPUT_FILE":
            if not value:
                raise ConfigError(f"[{key}]", "cannot be empty")
            self.output_file = value

        elif key == "PERFECT":
            if value == "True":
                self.perfect = True
            elif value == "False":
                self.perfect = False
            else:
                raise ConfigError(f"[{key}]", "must be True or False")

        elif key == "SEED":
            if value == "None":
                pass
            else:
                try:
                    self.seed = int(value)
                except ValueError as e:
                    raise ConfigError.invalid_int(f"[{key}]") from e

        elif key == "LOAD_FILE":
            if not value:
                raise ConfigError(f"[{key}]", "cannot be empty")
            self.load_file = self._resolve_load_file(value)

        elif key == "ALGORITHM":
            if value not in ("BFS", "DFS"):
                raise ConfigError(f"[{key}]", "must be BFS or DFS")
            self.algorithm = value

        else:
            raise ConfigError("[" + key + "]", "unknown parameter")

    @staticmethod
    def _resolve_load_file(file_name: str) -> str:
        """Resolve a maze file, including bundled mazes by file name."""
        provided_path = Path(file_name)

        if provided_path.is_file() or provided_path.is_absolute():
            return str(provided_path)

        bundled_maze = Path(__file__).parent / "mazes" / provided_path
        if bundled_maze.is_file():
            return str(bundled_maze)

        return file_name

    def _validate_required_fields(self) -> None:
        """
        Validate mandatory configuration fields.

        Raises exceptions when required
        fields are missing.
        """
        if self.load_file is not None:
            return

        if self.width is None:
            raise ConfigError.missing_field("[WIDTH]")

        if self.height is None:
            raise ConfigError.missing_field("[HEIGHT]")

        if self.entry is None:
            raise ConfigError.missing_field("[ENTRY]")

        if self.exit is None:
            raise ConfigError.missing_field("[EXIT]")

        if self.output_file is None:
            raise ConfigError.missing_field("[OUTPUT_FILE]")

        if self.perfect is None:
            raise ConfigError.missing_field("[PERFECT]")
