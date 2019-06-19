- Add unit tests
- Add type hints
- Format with black
- Render HTML fancy tables
- Splitting by `" | "` breaks for some tracks
- Clean up near-duplicates in cumulative playlists
- Travis fails on non-master upstream branches
- Apparently playlist IDs can change. For example, "Songs to Sing in the
  Shower" changed from 4TNBeyX7awz89qwtTmh9D4 to 37i9dQZF1DWSqmBTGDYngZ on
  2019-06-18. We should handle this automatically. Note that currently, because
  the pretty playlist files use playlist names as the filenames, we don't lose
  history. However, we *do* lose history for plain files.
