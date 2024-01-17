## Introduction

Playlists must be registered to be included in the archive. The
[`playlists/registry`](https://github.com/mackorone/spotify-playlist-archive/tree/main/playlists/registry)
directory acts as the registry; the filenames within it are the playlist IDs to
include. To add a playlist to the archive, simply create an empty file in
`playlists/registry` named after your playlist ID and submit a pull request.

> [!TIP]
> If you don't know what a playlist ID is, you can use
> [this tool](https://spotifyplaylistarchive.com/get-playlist-id) to extract it
> from the playlist's URL.

## Adding Playlists

> [!IMPORTANT]
> If you want to add multiple playlists, please follow the slightly more
> complicated instructions below. It's much easier for me to merge one combined
> pull request than multiple separate pull requests.

### Adding a single playlist

Instructions for creating single new file in `playlists/registry`:

1. Go to https://github.com/mackorone/spotify-playlist-archive/new/main/playlists/registry
1. [Click "Fork this repository"](https://user-images.githubusercontent.com/3769813/171501788-04d8550b-a853-4996-90a1-cb2888b22c7f.png)
1. [Enter the playlist ID as the file name, leave the file empty](https://user-images.githubusercontent.com/3769813/171501819-37415b0c-9b08-4eaa-ac3e-7b7098efcaae.png)
1. [Scroll down and click "Propose new file"](https://user-images.githubusercontent.com/3769813/171502287-00abab1e-b0a7-4f54-8367-a6c3d9abcae4.png)
1. [Click "Create pull request"](https://user-images.githubusercontent.com/3769813/171502378-27f94960-df34-4566-a769-844fc644de5b.png)
1. [Click "Create pull request" again](https://user-images.githubusercontent.com/3769813/171502466-d9622f19-9acd-4bf1-b6aa-8858cd89bf56.png)

### Adding multiple playlists

Instructions for creating multiple new files in `playlists/registry`, one for each playlist:

1. If you haven't done so already, fork this repository
    1. Go to https://github.com/mackorone/spotify-playlist-archive
    1. [Click "Fork"](https://github.com/mackorone/spotify-playlist-archive/assets/3769813/e4f44811-8e93-4156-99b9-2b1cc0ead90d)
    1. [Click "Create fork"](https://github.com/mackorone/spotify-playlist-archive/assets/3769813/e947dc93-3fd2-4813-bd04-261eadf450d0)
1. [Click the "playlists" folder](https://github.com/mackorone/spotify-playlist-archive/assets/3769813/8557ef7b-d5f0-4d56-ba7a-09e6b9c6b7e2)
1. [Click the "registry" folder](https://github.com/mackorone/spotify-playlist-archive/assets/3769813/d6ab878d-d3f0-479d-bb0d-7979dc3200b6)
1. [Click "Upload files"](https://github.com/mackorone/spotify-playlist-archive/assets/3769813/3b5a352d-44ee-45e9-9c42-6a8ab9c6aa1b)
1. [Upload empty files from your computer, one for each playlist](https://github.com/mackorone/spotify-playlist-archive/assets/3769813/4e2ca87e-64fa-4649-87bc-fe021e63cafc)
1. Double-check the files, add a commit message, and
   [click "Commit changes"](https://github.com/mackorone/spotify-playlist-archive/assets/3769813/6d6f1566-3f62-4087-bd77-bb9d05d1a515)
1. Go back to your forked repo and [click "Open pull request"](https://github.com/mackorone/spotify-playlist-archive/assets/3769813/dab791d6-3b41-4fb4-9f19-d811047bfa78)
1. [Click "Create pull request"](https://github.com/mackorone/spotify-playlist-archive/assets/3769813/0c950c20-f2b4-400f-9a82-027ee914f5b3)
1. [Click "Create pull request" again](https://github.com/mackorone/spotify-playlist-archive/assets/3769813/92e02200-ddc9-40de-a051-c394a6894f32)

## Source Code

The source code for this project lives here:
[mackorone/spotify-playlist-archive-src](https://github.com/mackorone/spotify-playlist-archive-src)
