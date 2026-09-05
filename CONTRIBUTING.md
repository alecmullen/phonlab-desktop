# Contributing

## Branches and Pull Requests

`main` and `dev` can only be updated by PR. Ongoing developments are generally merged to `dev`, and `dev` is merged to `main` when preparing for a release. Automatic builds are generated from `main`. 

In the future, we may implement `release/` branches for development freezes, to be branched off of `dev` and later merged into `main`.

Going forward, we will encourage feature branches to be prefixed with `feature/` or `bug/`, followed by a descriptive title. Branches may be deleted on Github after merging. Rebasing before merging is encouraged.

Please try to limit pull requests to 400 lines or under. If necessary, you can split it into multiple pull requests to a feature branch before mergign the feature branch.

## Linting, formatting, and type checking

Linting, formatting, and type checking are enforced with ruff and ty on `dev` and `main`. Install both and run `ruff check` and `ty check` and fix any errors introduced. Run `ruff format` to automatically format. Rules are mostly default, with the addition that type annotations are required on methods.

## Translation/Localization

All user-facing text should be passed through `self.tr()` from within a Qt component. This extracts all strings so the app can be translated to other languages. Ex: `TextItem(self.tr("example"))`
