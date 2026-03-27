from abc import ABC, abstractmethod


class HostConnectionHelper(ABC):
    @property
    @abstractmethod
    def host_name(self) -> str:
        pass

    @abstractmethod
    def await_connection(
        self,
        timeout=30,
        required_consecutive=3,
        stabilization_delay=1.0,
    ):
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def stabilize_after_operation(self, operation: str, delay: float = 2.0):
        pass

    def revert_on_failure(self):
        """Revert unsaved changes. No-op by default."""
        return

    @abstractmethod
    def close_application(self):
        pass

    @abstractmethod
    def force_exit(self):
        pass


_HELPERS = {}


def register_helper(cls):
    _HELPERS[cls.host_name] = cls
    return cls


def get_connection_helper(host):
    name = getattr(host, "name", None)
    helper_cls = _HELPERS.get(name)
    return helper_cls() if helper_cls else None


# Import helper modules to register implementations.
from . import photoshop  # noqa: E402,F401
