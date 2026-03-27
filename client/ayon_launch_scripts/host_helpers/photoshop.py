import time

from . import HostConnectionHelper, register_helper


@register_helper
class PhotoshopConnectionHelper(HostConnectionHelper):
    host_name = "photoshop"

    @staticmethod
    def _get_stub():
        from ayon_photoshop.api.launch_logic import stub

        return stub()

    def await_connection(
        self,
        timeout=30,
        required_consecutive=3,
        stabilization_delay=1.0,
    ):
        from ayon_photoshop.api.launch_logic import ConnectionNotEstablishedYet

        start = time.monotonic()
        consecutive_success = 0

        while (time.monotonic() - start) < timeout:
            try:
                _stub = self._get_stub()
                if _stub:
                    # Verify that Photoshop can process requests, not just that
                    # a websocket exists.
                    _stub.get_active_document_name()
                    consecutive_success += 1

                    if consecutive_success >= required_consecutive:
                        time.sleep(stabilization_delay)
                        _stub.get_active_document_name()
                        return

                    time.sleep(0.3)
                    continue

            except ConnectionNotEstablishedYet:
                consecutive_success = 0

            except Exception as exc:
                consecutive_success = 0

            time.sleep(0.5)

        raise RuntimeError("Timed out waiting for stable Photoshop WebSocket connection")

    def is_connected(self) -> bool:
        try:
            self._get_stub().get_active_document_name()
            return True
        except Exception:
            return False

    def stabilize_after_operation(self, operation: str, delay: float = 2.0):
        time.sleep(delay)
        self.await_connection(required_consecutive=3, stabilization_delay=1.0)

    def revert_on_failure(self):
        try:
            self._get_stub().revert_to_previous()
        except Exception:
            pass

    def close_application(self):
        from ayon_photoshop.api.launch_logic import ConnectionNotEstablishedYet

        try:
            self._get_stub().close()
        except ConnectionNotEstablishedYet:
            pass

    def force_exit(self):
        from ayon_core.lib.events import emit_event

        emit_event("application.close")
