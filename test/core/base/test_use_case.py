from collections.abc import Generator

from core.base.use_case import UseCase


class ConcreteUseCase(UseCase[int]):
    def __call__(self, *values: int) -> Generator[int, None, None]:
        yield from values


def test_call_returns_a_generator_of_results():
    use_case = ConcreteUseCase()

    assert list(use_case(1, 2, 3)) == [1, 2, 3]


def test_run_sync_returns_first_yielded_value():
    use_case = ConcreteUseCase()

    assert use_case.run_sync(1, 2, 3) == 1


def test_run_sync_starts_a_fresh_generator_on_each_call():
    use_case = ConcreteUseCase()

    assert use_case.run_sync(1, 2, 3) == 1
    assert use_case.run_sync(4, 5, 6) == 4
