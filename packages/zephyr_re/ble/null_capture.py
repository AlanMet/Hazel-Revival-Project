"""No-op capture for product installs (no session log files)."""


class NullCapture:
    live_path = None

    def log(self, *args, **kwargs) -> None:
        pass

    def log_section(self, *args, **kwargs) -> None:
        pass

    def log_operation(self, *args, **kwargs) -> None:
        pass

    def log_command_result(self, *args, **kwargs) -> None:
        pass
