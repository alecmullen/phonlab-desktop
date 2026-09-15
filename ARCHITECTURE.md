# Architecture

This codebase is divided into layers which we strive to couple loosely. The main layers are `core` and `ui`. The submodules of each layer are organized by feature. In order to maintain loose coupling, each layer deals in its own set of dataclass entities.

This is a PyQt project. We use PyQt heavily in both layers, because we use it for both UI and threading purposes.

## core

The `core` module handles heavy computations, I/O, and core business logic. `core` is completely unaware of, and should not import from, the `ui` module. Much of the `core` functionality is meant to be launched in separate threads, but some are meant to run syncronously. Each feature should be implemented as a folder containing these basic elements, inheriting from the `base` submodule as needed:
  - **`UseCase`, `UseCaseSync`, or custom workers**: 

    - Subclass `UseCase` or `UseCaseSync` to implement a self-contained task. `UseCase` returns a generator and also defines a `stop` method. This pattern is leveraged by `JobManager`, which can launch and manage asyncronus tasks. `UseCaseSync` simply returns immediately. 

    - Some features will have particular threading requirements and and can be implemented with custom managers and workers. See `core/play_audio` for an example.

  - **`entities`**:
    - Define any necessary dataclasses, especially if your function uses multiple parameters and/or return values. Use the decorator `@dataclass`.

## ui

The `ui` module has access to `core`. However, it should map any `core` data entities into `ui` entities as soon as possible. `ui` uses `core` entities exclusively to interface with `core` methods. `core` entities should not be passed around, especially to views. 

`ui` defines its own entities, which inherit from the `State` class and are named with a `-State` suffix. 

The `ui` module follows the [MVVM](https://www.geeksforgeeks.org/websites-apps/introduction-to-model-view-view-model-mvvm/) architectural pattern. A UI feature (e.g. a plot, window, or other view) can be placed in its own folder containing the following elements:
  - **ViewModel**: 
    - Inherits from `ViewModel`. Handles underlying business logic and tracks states pertinent to the given view. It is unaware of the corresponding view class. Manages `JobManager` instances and launches `UseCases`. A single signal, `state_changed`, is used to emit all state changes. This is inspired by the [UDF](https://developer.android.com/develop/ui/compose/architecture) pattern.

  - **View**: 
    - This can be a plot, window, or other kind of view. It contains a `ViewModel` as an instance property and subscribes to it, rendering changes reactively when state changes are emitted.

  - **State**:
    - Inherits from `State`. These are dataclasses which track the current underlying state of the view, and are emited from the `ViewModel` to be consumed by a subscribed view. Any mapping logic between `core` entities and `State` entities can be contained within these files.