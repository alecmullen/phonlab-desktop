# Architecture

This codebase is divided into layers which we strive to couple loosely. The main layers are `data`, `core` and `ui`. The submodules of each layer are organized by feature. In order to maintain loose coupling, each layer deals in its own set of data models. They are wired up thorugh dependency injection, implemented in the `bootstrap` module.

## data

The `data` module handles persistence. It implements `Repository` Protocols defined by the `core`. It is currently implemented as a SQLite database for local storage of linguistic annotations. In the future, it may include functionality for synchronizing with a remote database. Folders are organized around features, and contain these basic elements, inheriting from the `base` submodule as needed:
  - **`Entity`**:
    - Defines tables in the database and their relations; these entities double as Python data objects. Uses SQLAlchemy
  - **`DataSource`**:
    - Defines query functions with which to access the database for a particular entity or group of related entities. Uses SQLAlchemy ORM to access database without knowledge of the exact database platform (SQLite, PostgreSQL, etc.)
  - **`Repository`**:
    - Implements Protocol defined by `core` to fulfill data requests. Maps entities to `core`-defined data models, and may in the future mediate between multiple datasources

## core

The `core` module defines data objects and functionality for our domain, absract of UI and data implementations. It includes heavy computations, I/O, and business logic. `core` is completely unaware of, and should not import from, the `ui` module. It is unaware of the `data` layer implementations, but it depends on its own `Repository` Protocols, without knowledge of how they are implemented. Much of the `core` functionality is meant to be launched in separate threads, but some are meant to run syncronously. Each feature should be implemented as a folder containing these basic elements, inheriting from the `base` submodule as needed:
  - **`UseCase`, `UseCaseSync`, custom workers, or raw functions**: 

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