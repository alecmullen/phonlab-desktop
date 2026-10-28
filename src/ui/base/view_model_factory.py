from typing import Any, Protocol

from ui.base.view_model import ViewModel


class ViewModelFactory(Protocol):
    def create[T: ViewModel](
        self,
        view_model_type: type[T],
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> T: ...
