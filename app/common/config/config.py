import os
from pathlib import Path


class Config:
    """
    Class for loading environment variables from .env.{APP_ENV} file
    """

    def __init__(self):
        app_env = os.getenv("APP_ENV")
        if not app_env:
            raise ValueError("APP_ENV variable is not present")
        env_file = Path().absolute() / f".env.{app_env}"
        if not env_file.is_file():
            raise FileNotFoundError(f"Couldn't find file with .env.{app_env} name")
        self._load_env_file(env_file)

    @staticmethod
    def _load_env_file(env_file: Path) -> None:
        """
        Function loads variables from env file, existing environment variables take precedence
        Args:
            env_file (Path): path to env file
        """

        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value

    @staticmethod
    def get(key: str) -> str:
        """
        Function gets environment variable value
        Args:
            key (str): name of environment variable
        Returns:
            str: value of environment variable
        Raises:
            ValueError: if environment variable is not set
        """

        value = os.getenv(key)
        if value:
            return value
        raise ValueError(f"No such env: {key}")

    @staticmethod
    def set(key: str, value: str) -> None:
        """
        Function sets value for environment variable
        Args:
            key (str): name of environment variable
            value (str): new value for environment variable
        """

        os.environ[key] = value
