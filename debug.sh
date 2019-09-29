#!/usr/bin/env bash

comm -3 <(for x in playlists/pretty/*; do basename "${x}" .md; done) <(for x in playlists/plain/*; do head -n 1 $x; done | sort)
