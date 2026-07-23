from abc import abstractmethod
from typing import Callable

class ViewModel[ViewState]():
    def __init__(self, state=ViewState):
        self.state = state
        self.listeners = []

    def subscribe(self, listener: Callable):
        self.listeners.append(listener)

    @abstractmethod
    def on_dispatch(self, action):
        pass

    def dispatch(self, action):
        self.on_dispatch(action)
        for listener in self.listeners:
            listener(self.state)
