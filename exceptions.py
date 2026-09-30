class MazeError(Exception):
    """Base maze exception."""
    def __init__(self, message: str = "Unknown error") -> None:
        super().__init__(message)


class ConfigError(MazeError):
    """Configuration parsing exception."""
    def __init__(
            self, field: str, message: str = "Unknown config error"
            ) -> None:
        """
        Initialize configuration exception.

        Args:
            message: Exception message.
        """
        super().__init__(f"{field} {message}")

    @staticmethod
    def missing_file(field: str) -> "ConfigError":
        """
        Return missing file exception.

        Args:
            field: Configuration field name.

        Returns:
            Missing file configuration error.
        """
        return ConfigError(field, "is missing")

    @staticmethod
    def missing_field(field: str) -> "ConfigError":
        """
        Return missing field exception.

        Args:
            field: Configuration field name.

        Returns:
            Missing field configuration error.
        """
        return ConfigError(field, "is missing")

    @staticmethod
    def invalid_int(field: str) -> "ConfigError":
        """
        Return invalid integer exception.

        Args:
            field: Configuration field name.

        Returns:
            Invalid integer configuration error.
        """
        return ConfigError(field, "must be an integer")

    @staticmethod
    def invalid_bound(field: str) -> "ConfigError":
        """
        Return invalid bounds exception.

        Args:
            field: Configuration field name.

        Returns:
            Invalid bounds configuration error.
        """
        return ConfigError(
            field,
            "out of bounds: expected value between 1 and 50"
        )

    @staticmethod
    def invalid_coordinates(field: str) -> "ConfigError":
        """
        Return invalid coordinates exception.

        Args:
            field: Configuration field name.

        Returns:
            Invalid coordinates configuration error.
        """
        return ConfigError(
            field,
            "must be in format x,y where x and y are integers"
        )

    @staticmethod
    def invalid_bound_coordinates(field: str, width: int, height: int
                                  ) -> "ConfigError":
        """
        Return out-of-bounds coordinates exception.

        Args:
            field: Configuration field name.
            width: Maze width.
            height: Maze height.

        Returns:
            Invalid coordinates configuration error.
        """
        return ConfigError(
            field,
            f"coordinates out of bounds: "
            f"expected 0 <= x < {width} and 0 <= y < {height}"
        )

    @staticmethod
    def aggregate(errors: list["ConfigError"]) -> "ConfigError":
        """
        Aggregate multiple configuration errors.

        Args:
            errors: List of configuration errors.

        Returns:
            Aggregated configuration exception.
        """
        messages = "\n".join(str(e) for e in errors)
        return ConfigError(f"\n{messages}", "")
