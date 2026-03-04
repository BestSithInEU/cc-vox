"""TTSBackend ABC and DockerBackend base classes."""

from __future__ import annotations

import abc
import urllib.error
import urllib.request

from ._docker import docker_stop_by_port
from ._errors import TTSConnectionError, TTSGenerationError


class TTSBackend(abc.ABC):
    """Abstract base for every TTS backend.

    Subclasses must declare class attributes: name, priority, port, health_path.
    """

    name: str
    priority: int
    port: int
    health_path: str

    health_timeout: float = 2.0
    generate_timeout: float = 60.0

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Skip enforcement on intermediate ABCs
        if abc.ABC in cls.__bases__:
            return
        for attr in ("name", "priority", "port", "health_path"):
            if not hasattr(cls, attr):
                raise TypeError(
                    f"{cls.__name__} must define class attribute '{attr}'"
                )

    @property
    def base_url(self) -> str:
        return f"http://localhost:{self.port}"

    def is_available(self) -> bool:
        """Health-check the backend service."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}{self.health_path}", method="GET",
            )
            resp = urllib.request.urlopen(req, timeout=self.health_timeout)
            return 200 <= resp.status < 300
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def ensure_running(self) -> bool:
        """Start the service if possible, then return availability."""
        return self.is_available()

    def generate(self, text: str, voice: str, speed: float) -> bytes:
        """Template method: wraps _generate_impl with error handling."""
        from ._debug import Timer, log

        log(f"{self.name}: generating {len(text)} chars, voice={voice}, speed={speed}")
        try:
            with Timer(f"{self.name}: generate"):
                return self._generate_impl(text, voice, speed)
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            raise TTSConnectionError(
                f"{self.name}: connection failed: {exc}"
            ) from exc
        except TTSGenerationError:
            raise
        except Exception as exc:
            raise TTSGenerationError(
                f"{self.name}: generation failed: {exc}"
            ) from exc

    @abc.abstractmethod
    def _generate_impl(self, text: str, voice: str, speed: float) -> bytes:
        """Backend-specific audio generation — override in subclasses."""
        ...

    def stop(self) -> None:
        """Stop the backend service. No-op by default."""


class DockerBackend(TTSBackend, abc.ABC):
    """Base for backends running in Docker containers."""

    def stop(self) -> None:
        docker_stop_by_port(self.port)
