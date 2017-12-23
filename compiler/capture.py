__all__ = (
    "CaptureTable",
    "TooManyCapturesException",
    "CaptureNotFoundException",
)


import typing


class CaptureTable:
    __slots__ = (
        "_max_length",
        "_capture_names",
        "_capture_name_2_id",
    )

    def __init__(self, max_length) -> None:
        self._max_length = max_length
        self._capture_names = []
        self._capture_name_2_id = {}

    def add_capture(self, capture_name: str) -> int:
        capture_id = len(self._capture_names)

        if capture_id == self._max_length:
            raise TooManyCapturesException()

        self._capture_names.append(capture_name)
        assert capture_name not in self._capture_name_2_id.keys()
        self._capture_name_2_id[capture_name] = capture_id
        return capture_id

    def find_capture(self, capture_name: str) -> int:
        capture_id = self._capture_name_2_id.get(capture_name, None)

        if capture_id is None:
            raise CaptureNotFoundException()

        return capture_id

    def get_capture_names(self) -> typing.List[str]:
        return self._capture_names


class TooManyCapturesException(Exception):
    pass


class CaptureNotFoundException(Exception):
    pass
