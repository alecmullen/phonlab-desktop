from collections.abc import Generator

from core.base.use_case import UseCase


class ConcreteUseCase(UseCase[int]):
    def __init__(self, values: list[int]):
        self.values = values
        self.stopped = False

    def invoke(self) -> Generator[int, None, None]:
        yield from self.values

    def stop(self) -> None:
        self.stopped = True


def test_run_sync_returns_first_yielded_value():
    use_case = ConcreteUseCase([1, 2, 3])

    assert use_case.run_sync() == 1


def test_run_sync_starts_a_fresh_generator_on_each_call():
    use_case = ConcreteUseCase([1, 2, 3])

    assert use_case.run_sync() == 1
    assert use_case.run_sync() == 1


def test_run_sync_does_not_call_stop():
    use_case = ConcreteUseCase([1])

    use_case.run_sync()

    assert use_case.stopped is False
