__all__ = (
    "RegisterPool",
    "RegisterStack",
    "NoMoreRegisterException",
    "DuplicateRegisterNameException",
    "RegisterNotFoundException",
)


import contextlib
import typing


class RegisterPool:
    __slots__ = (
        "_size",
        "_max_register_id",
        "_delta",
    )

    def __init__(self, size: int) -> None:
        self._size = size
        self._max_register_id = -1
        self._delta = _RegisterPoolDelta(None, 0, self._size)

    def get_max_register_id(self):
        return self._max_register_id

    def get_next_register_id(self) -> int:
        register_id = self._delta.get_next_register_id()
        return register_id

    def allocate_register(self, register_name: typing.Optional[str] = None) -> int:
        register_id = self._delta.allocate_register(register_name)

        if register_id > self._max_register_id:
            self._max_register_id = register_id

        return register_id

    def free_unnamed_register(self) -> None:
        self._delta.free_unnamed_register()

    def find_register(self, register_name: str) -> int:
        return self._delta.find_register(register_name)

    @contextlib.contextmanager
    def save(self) -> typing.ContextManager[None]:
        delta = self._delta
        self._delta = _RegisterPoolDelta(delta, delta.get_next_register_id(), self._size)
        yield
        self._delta = delta


class _RegisterPoolDelta:
    __slots__ = (
        "_parent",
        "_used_size",
        "_size",
        "_register_names",
        "_register_name_2_id",
    )

    def __init__(self, parent: typing.Optional["_RegisterPoolDelta"], used_size: int, size: int) \
        -> None:
        self._parent = parent
        self._used_size = used_size
        self._size = size
        self._register_names = []
        self._register_name_2_id = {}

    def get_next_register_id(self) -> int:
        register_count = len(self._register_names)
        register_id = self._used_size + register_count
        return register_id

    def allocate_register(self, register_name: typing.Optional[str]) -> int:
        register_id = self.get_next_register_id()

        if register_id >= self._size:
            raise NoMoreRegisterException()

        if register_name is None:
            self._register_names.append(register_name)
        else:
            if register_name in self._register_name_2_id.keys():
                raise DuplicateRegisterNameException()

            assert not (len(self._register_names) >= 1 and self._register_names[-1] is None)
            self._register_names.append(register_name)
            self._register_name_2_id[register_name] = register_id

        return register_id

    def free_unnamed_register(self) -> None:
        register_name = self._register_names.pop()
        assert register_name not in self._register_name_2_id.keys()

    def find_register(self, register_name: str) -> int:
        register_id = self._register_name_2_id.get(register_name)

        if register_id is None:
            if self._parent is None:
                raise RegisterNotFoundException()

            register_id = self._parent.find_register(register_name)

        return register_id


class RegisterStack:
    __slots__ = (
        "_register_pool",
        "_register_infos",
    )

    def __init__(self, register_pool: RegisterPool) -> None:
        self._register_pool = register_pool
        self._register_infos = []

    def push(self, register_id: typing.Optional[int] = None) -> int:
        if register_id is None:
            register_id = self._register_pool.allocate_register()
            register_needs_freeing = True
        else:
            register_needs_freeing = False

        self._register_infos.append((register_id, register_needs_freeing))
        return register_id

    def pop(self) -> int:
        register_id, register_needs_freeing = self._register_infos.pop()

        if register_needs_freeing:
            assert register_id == self._register_pool.get_next_register_id() - 1
            self._register_pool.free_unnamed_register()

        return register_id

    def peek(self) -> int:
        register_id, _ = self._register_infos[-1]
        return register_id


class NoMoreRegisterException(Exception):
    pass


class DuplicateRegisterNameException(Exception):
    pass


class RegisterNotFoundException(Exception):
    pass
