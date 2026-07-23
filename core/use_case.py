from abc import ABC, abstractmethod
import asyncio


class UseCase[T](ABC):

    @abstractmethod
    def invoke() -> T:
        pass

    def __call__(self, success, error):
        async def call():
            try:
                response = self.invoke()
                success(response)
            except Exception as err:
                error(err)
        return asyncio.run(call())
