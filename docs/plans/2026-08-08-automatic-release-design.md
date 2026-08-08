# Automatic Release Workflow Design

## Objective

Publish a complete Moviu release from a single version tag without manually creating the GitHub release or uploading binaries.

## Trigger And Validation

Pushing any `v*` tag triggers the workflow. A manual dispatch with an explicit tag remains available for recovery. Before building, an Ubuntu job installs dependencies, confirms that the tag matches `VERSION` in `moviu_server/config.py`, and runs the complete unit-test suite. A mismatch or failed test prevents publication.

## Native Builds

After validation, a matrix builds on pinned `windows-2022` and `ubuntu-22.04` images with Python 3.11.9 and pinned direct dependencies. Both jobs use `MoviuPrintServer.spec`, ensuring that the application icon, changelog, Tkinter support, and packaged resources remain consistent. The outputs use stable filenames consumed by the website's latest-release links.

## Publication

The publish job runs only after both native builds succeed. For a new tag, it creates the GitHub release, generates release notes from Git history, and uploads both binaries. If the release already exists during a manual retry, it replaces the binary assets instead of failing. GitHub's standard source archives remain available automatically.
