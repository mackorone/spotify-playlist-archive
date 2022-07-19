## Adding Playlists

To add a playlist to the archive, simply `touch playlists/registry/<playlist_id>` and make a pull request.

Alternatively, follow these steps:
1. Go to https://github.com/mackorone/spotify-playlist-archive/new/main/playlists/registry
1. [Click "Fork this repository"](https://user-images.githubusercontent.com/3769813/171501788-04d8550b-a853-4996-90a1-cb2888b22c7f.png)
1. [Enter the playlist ID as the file name, leave the file empty](https://user-images.githubusercontent.com/3769813/171501819-37415b0c-9b08-4eaa-ac3e-7b7098efcaae.png)
1. [Scroll down and click "Propose new file"](https://user-images.githubusercontent.com/3769813/171502287-00abab1e-b0a7-4f54-8367-a6c3d9abcae4.png)
1. [Click "Create pull request"](https://user-images.githubusercontent.com/3769813/171502378-27f94960-df34-4566-a769-844fc644de5b.png)
1. [Click "Create pull request" again](https://user-images.githubusercontent.com/3769813/171502466-d9622f19-9acd-4bf1-b6aa-8858cd89bf56.png)

## Development

### Setup

This project uses [`pip-tools`](https://github.com/jazzband/pip-tools) to manage
dependencies.

To get started, first create and activate a new virtual environment:
```
$ python3.8 -m venv venv
$ source venv/bin/activate
```

Then upgrade `pip` and install `pip-tools`:
```
$ pip install --upgrade pip
$ pip install pip-tools
```

Lastly, use `pip-sync` to install the dev requirements:
```
$ pip-sync requirements/requirements-dev.txt
```

### Formatting

This project uses [`isort`](https://github.com/pycqa/isort) and
[`black`](https://github.com/psf/black) to automatically format the source code.
You should invoke both of them, in that order, before submitting pull requests:
```
$ isort src/
$ black src/
```

### Linting

This project uses [`flake8`](https://github.com/pycqa/flake8) for linting, a
basic form of static analysis. You can use `flake8` to check for errors and bad
code style:
```
$ flake8 src/
```

### Type Checking

This project uses [`pyre`](https://github.com/facebook/pyre-check) to check for
type errors. You can invoke it from anywhere in the repository as follows:
```
$ pyre
```

Note that Pyre depends on [`watchman`](https://github.com/facebook/watchman), a
file watching service, for incremental type checking. It takes a few minutes to
install, but it's worth the investment - it makes type checking almost
instantaneous.

### Unit Testing

After making changes, you should update unit tests and run them as follows:
```
$ cd src
$ python -m unittest tests/\*.py
```

### Integration Testing

Copy the `playlists` directory to `_playlists`:
```
$ cp -r playlists _playlists
```

Then run the script:
```
$ src/main.py
```
