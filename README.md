examples/spring-petclinic have a codebase demo~ like ppt
[here](https://speakerdeck.com/michaelisvy/spring-petclinic-sample-application)

## Submodules
To clone submodules do
```sh
git submodule update --init --recursive
```

## Usage
Use [uv](https://docs.astral.sh/uv/) for virtual env creation.
Or lookup uv.lock file to install pip dependencies and make your own python environment.

Also somehow install `plantuml`.

```sh
uv run main.py
plantuml -tsvg diagram.puml
```

Outputs: diagram.puml and diagram.svg files.
