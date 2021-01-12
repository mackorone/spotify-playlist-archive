# spotify-playlist-archive [![Build Status](https://travis-ci.com/mackorone/spotify-playlist-archive.svg?branch=master)](https://travis-ci.com/mackorone/spotify-playlist-archive)

> Daily snapshots of public Spotify playlists

Spotify's playlists are great. I like that they're updated once in a while -
change is good! I don't like, however, that it's impossible to see older
versions. How am I supposed to remember the name of that song I really liked?
Apparently, I'm not alone: see
[here](https://community.spotify.com/t5/Content-Questions/View-previous-versions-of-playlists/td-p/4400750),
[here](https://community.spotify.com/t5/Accounts/A-playlist-was-modified-Can-I-get-the-old-songs-back/td-p/1001889),
[here](https://community.spotify.com/t5/Content-Questions/Seeing-an-old-version-of-a-playlist/td-p/1318739),
[here](https://community.spotify.com/t5/Other-Partners-Web-Player-etc/Playlists-Is-there-any-way-to-recover-previous-versions-of-a/td-p/4726831),
[here](https://community.spotify.com/t5/Desktop-Mac/Find-Songs-of-old-versions-of-Spotify-Playlists/td-p/998504),
[here](https://community.spotify.com/t5/Closed-Ideas/Playlist-Versioning-History/idi-p/1133819),
[here](https://community.spotify.com/t5/Closed-Ideas/Playlist-History-Versioning/idi-p/1346418),
[here](https://community.spotify.com/t5/Closed-Ideas/Playlists-Playlist-History/idi-p/1816799),
and [here](https://community.spotify.com/t5/Live-Ideas/Playlists-Edit-History/idi-p/4573743).
Since Spotify won't take snapshots of our favorite playlists, let's do it ourselves!

## Quick start

1. To view the current version of a playlist, click on its name [below](https://github.com/mackorone/spotify-playlist-archive#playlists)
1. To see all songs that ever belonged to a playlist, click "cumulative"
1. To determine which songs were added or removed from a playlist, click "githistory"
1. To add a playlist to the archive, simply `touch playlists/plain/<playlist_id>` and make a pull request

## How it works

This repository contains a script for scraping Spotify playlists and publishing
them back to the repo. The script is run daily via
[Travis CI](https://travis-ci.com/mackorone/spotify-playlist-archive). It's
also run after every commit, which means that playlists get regenerated
whenever the scraping or formatting logic changes, or when new playlists are
added - cool!

The script determines which playlists to scrape by looking at the file names in
`playlists/plain`. Files get regenerated as follows: a pretty version of each
playlist gets dumped in `playlists/pretty`, new tracks are added to the
files in `playlists/cumulative`, and a plaintext version of each playlist is
written back to `playlists/plain`. The plain version is sorted alphabetically,
rather than by track number, so that it only changes when tracks are added or
removed, making [Git History](https://githistory.xyz/) a nice way to visualize
how the playlist evolves over time.

## Development

This project uses [`pip-tools`](https://github.com/jazzband/pip-tools) to manage
dependencies.

To get started, first create and activate a new virtual environment:
```
$ python3.8 -m venv venv
$ source venv/bin/activate
```

Then install `pip-tools`:
```
$ pip install pip-tools
```

Lastly, use `pip-sync` to install the dev requirements:
```
$ pip-sync requirements/requirements-dev.txt
```

## Playlists

- [2010s Hits](/playlists/pretty/2010s%20Hits.md)
- [24K Magic Radio](/playlists/pretty/24K%20Magic%20Radio.md)
- [88 Keys](/playlists/pretty/88%20Keys.md)
- [A.M. Commute](/playlists/pretty/A.M.%20Commute.md)
- [Acoustic Concentration](/playlists/pretty/Acoustic%20Concentration.md)
- [Acoustic Hits: Oldies but Goodies](/playlists/pretty/Acoustic%20Hits:%20Oldies%20but%20Goodies.md)
- [Acoustic Love](/playlists/pretty/Acoustic%20Love.md)
- [Acoustic Rock](/playlists/pretty/Acoustic%20Rock.md)
- [All New Indie](/playlists/pretty/All%20New%20Indie.md)
- [All Out 00s](/playlists/pretty/All%20Out%2000s.md)
- [All Out 10s](/playlists/pretty/All%20Out%2010s.md)
- [All Out 60s](/playlists/pretty/All%20Out%2060s.md)
- [All Out 70s](/playlists/pretty/All%20Out%2070s.md)
- [All Out 80s](/playlists/pretty/All%20Out%2080s.md)
- [All Out 90s](/playlists/pretty/All%20Out%2090s.md)
- [All The Feels](/playlists/pretty/All%20The%20Feels.md)
- [Always Perfect](/playlists/pretty/Always%20Perfect.md)
- [Ambient Relaxation](/playlists/pretty/Ambient%20Relaxation.md)
- [Anti Pop](/playlists/pretty/Anti%20Pop.md)
- [Apply Yourself](/playlists/pretty/Apply%20Yourself.md)
- [Atmospheric Calm](/playlists/pretty/Atmospheric%20Calm.md)
- [Barack Obama's 2020 Summer Playlist](/playlists/pretty/Barack%20Obama's%202020%20Summer%20Playlist.md)
- [Beast Mode](/playlists/pretty/Beast%20Mode.md)
- [Beats to think to](/playlists/pretty/Beats%20to%20think%20to.md)
- [Bedroom Pop](/playlists/pretty/Bedroom%20Pop.md)
- [Binaural Beats: Focus](/playlists/pretty/Binaural%20Beats:%20Focus.md)
- [Black Girl Magic](/playlists/pretty/Black%20Girl%20Magic.md)
- [Brain Food](/playlists/pretty/Brain%20Food.md)
- [Butter](/playlists/pretty/Butter.md)
- [Café montréalais](/playlists/pretty/Café%20montréalais.md)
- [Calm Before the Storm](/playlists/pretty/Calm%20Before%20the%20Storm.md)
- [Canadian '90s](/playlists/pretty/Canadian%20'90s.md)
- [Carry Me Away Radio](/playlists/pretty/Carry%20Me%20Away%20Radio.md)
- [Chill Beats](/playlists/pretty/Chill%20Beats.md)
- [Chill Hits](/playlists/pretty/Chill%20Hits.md)
- [Chill House](/playlists/pretty/Chill%20House.md)
- [Chill Pop](/playlists/pretty/Chill%20Pop.md)
- [Chill Tracks](/playlists/pretty/Chill%20Tracks.md)
- [chill\DnB](/playlists/pretty/chill\DnB.md)
- [Chilled R&B](/playlists/pretty/Chilled%20R&B.md)
- [Chillin' on a Dirt Road](/playlists/pretty/Chillin'%20on%20a%20Dirt%20Road.md)
- [Coffee Beats](/playlists/pretty/Coffee%20Beats.md)
- [Concentração Perfeita](/playlists/pretty/Concentração%20Perfeita.md)
- [Confidence Boost](/playlists/pretty/Confidence%20Boost.md)
- [Creativity Boost](/playlists/pretty/Creativity%20Boost.md)
- [Cyberpunk Synthwave](/playlists/pretty/Cyberpunk%20Synthwave.md)
- [Dance Party](/playlists/pretty/Dance%20Party.md)
- [Dance Rising](/playlists/pretty/Dance%20Rising.md)
- [Deep Focus](/playlists/pretty/Deep%20Focus.md)
- [Digster HITS - Best of 2013](/playlists/pretty/Digster%20HITS%20-%20Best%20of%202013.md)
- [Disco Forever](/playlists/pretty/Disco%20Forever.md)
- [Discover Weekly (@catzs)](/playlists/pretty/Discover%20Weekly%20(@catzs).md)
- [Dreampop](/playlists/pretty/Dreampop.md)
- [EDM Top 100](/playlists/pretty/EDM%20Top%20100.md)
- [Energy Boost](/playlists/pretty/Energy%20Boost.md)
- [Epic & Melodic](/playlists/pretty/Epic%20&%20Melodic.md)
- [Epic Gaming](/playlists/pretty/Epic%20Gaming.md)
- [Feel Good Friday](/playlists/pretty/Feel%20Good%20Friday.md)
- [Fresh & Chill](/playlists/pretty/Fresh%20&%20Chill.md)
- [Fresh Finds: Best of Pop 2020](/playlists/pretty/Fresh%20Finds:%20Best%20of%20Pop%202020.md)
- [Fresh Finds: Experimental](/playlists/pretty/Fresh%20Finds:%20Experimental.md)
- [Friday Cratediggers](/playlists/pretty/Friday%20Cratediggers.md)
- [Girl Krush](/playlists/pretty/Girl%20Krush.md)
- [Global Top 50](/playlists/pretty/Global%20Top%2050.md)
- [Good Vibes](/playlists/pretty/Good%20Vibes.md)
- [Got Djent?](/playlists/pretty/Got%20Djent?.md)
- [Grimes Radio](/playlists/pretty/Grimes%20Radio.md)
- [Happy Hits!](/playlists/pretty/Happy%20Hits!.md)
- [Happy Pop](/playlists/pretty/Happy%20Pop.md)
- [Have a Great Day!](/playlists/pretty/Have%20a%20Great%20Day!.md)
- [HEADPHONES](/playlists/pretty/HEADPHONES.md)
- [Heart Beats](/playlists/pretty/Heart%20Beats.md)
- [Heavy Queens](/playlists/pretty/Heavy%20Queens.md)
- [Hot Country](/playlists/pretty/Hot%20Country.md)
- [Hot Rhythmic](/playlists/pretty/Hot%20Rhythmic.md)
- [hyperpop](/playlists/pretty/hyperpop.md)
- [Indie Chillout](/playlists/pretty/Indie%20Chillout.md)
- [Indie Favourites](/playlists/pretty/Indie%20Favourites.md)
- [indie pop & chill](/playlists/pretty/indie%20pop%20&%20chill.md)
- [Indie Pop](/playlists/pretty/Indie%20Pop.md)
- [Indie Rock Road Trip](/playlists/pretty/Indie%20Rock%20Road%20Trip.md)
- [Instrumental Backdrop](/playlists/pretty/Instrumental%20Backdrop.md)
- [Jazz Vibes](/playlists/pretty/Jazz%20Vibes.md)
- [Jazzy Romance](/playlists/pretty/Jazzy%20Romance.md)
- [Just Good Music](/playlists/pretty/Just%20Good%20Music.md)
- [just hits](/playlists/pretty/just%20hits.md)
- [K-Pop Rising](/playlists/pretty/K-Pop%20Rising.md)
- [Lady Gaga Radio](/playlists/pretty/Lady%20Gaga%20Radio.md)
- [Late Night Jazz](/playlists/pretty/Late%20Night%20Jazz.md)
- [License To Chill](/playlists/pretty/License%20To%20Chill.md)
- [Lo-Fi Beats](/playlists/pretty/Lo-Fi%20Beats.md)
- [Lo-fi Indie](/playlists/pretty/Lo-fi%20Indie.md)
- [Lorem](/playlists/pretty/Lorem.md)
- [Lounge - Soft House](/playlists/pretty/Lounge%20-%20Soft%20House.md)
- [Love Pop](/playlists/pretty/Love%20Pop.md)
- [Low Key Pop](/playlists/pretty/Low%20Key%20Pop.md)
- [Lowkey Tech](/playlists/pretty/Lowkey%20Tech.md)
- [Mega Hit Mix](/playlists/pretty/Mega%20Hit%20Mix.md)
- [Melantronic](/playlists/pretty/Melantronic.md)
- [Mellow Beats](/playlists/pretty/Mellow%20Beats.md)
- [Mellow Classics](/playlists/pretty/Mellow%20Classics.md)
- [Middle Kids - Complete Collection](/playlists/pretty/Middle%20Kids%20-%20Complete%20Collection.md)
- [Mood Booster](/playlists/pretty/Mood%20Booster.md)
- [Morning Acoustic](/playlists/pretty/Morning%20Acoustic.md)
- [Morning Coffee - Wake Up](/playlists/pretty/Morning%20Coffee%20-%20Wake%20Up.md)
- [Morning Motivation](/playlists/pretty/Morning%20Motivation.md)
- [Morning Workout 2020 Hits](/playlists/pretty/Morning%20Workout%202020%20Hits.md)
- [mosaic](/playlists/pretty/mosaic.md)
- [Motivation Mix](/playlists/pretty/Motivation%20Mix.md)
- [murga](/playlists/pretty/murga.md)
- [New Boots](/playlists/pretty/New%20Boots.md)
- [New Music Friday Indonesia](/playlists/pretty/New%20Music%20Friday%20Indonesia.md)
- [New Music Friday](/playlists/pretty/New%20Music%20Friday.md)
- [New Pop Revolution](/playlists/pretty/New%20Pop%20Revolution.md)
- [Night Pop](/playlists/pretty/Night%20Pop.md)
- [Not Quite Classical](/playlists/pretty/Not%20Quite%20Classical.md)
- [Orgánica](/playlists/pretty/Orgánica.md)
- [Peace](/playlists/pretty/Peace.md)
- [Peaceful Meditation](/playlists/pretty/Peaceful%20Meditation.md)
- [Peaceful Piano](/playlists/pretty/Peaceful%20Piano.md)
- [Peaceful Pop](/playlists/pretty/Peaceful%20Pop.md)
- [Piano in the Background](/playlists/pretty/Piano%20in%20the%20Background.md)
- [Plugged In](/playlists/pretty/Plugged%20In.md)
- [POLLEN](/playlists/pretty/POLLEN.md)
- [Pop Remix](/playlists/pretty/Pop%20Remix.md)
- [Pop Rising](/playlists/pretty/Pop%20Rising.md)
- [Power Hour](/playlists/pretty/Power%20Hour.md)
- [Rap UK](/playlists/pretty/Rap%20UK.md)
- [RapCaviar](/playlists/pretty/RapCaviar.md)
- [Relax & Unwind](/playlists/pretty/Relax%20&%20Unwind.md)
- [Ren hygge](/playlists/pretty/Ren%20hygge.md)
- [Rocket League Game Soundtrack (Complete)](/playlists/pretty/Rocket%20League%20Game%20Soundtrack%20(Complete).md)
- [Rocket League Soundtrack (Complete OST)](/playlists/pretty/Rocket%20League%20Soundtrack%20(Complete%20OST).md)
- [Roots Revival](/playlists/pretty/Roots%20Revival.md)
- [Sad Bops](/playlists/pretty/Sad%20Bops.md)
- [Sad Indie](/playlists/pretty/Sad%20Indie.md)
- [Sci-Fi Scapes](/playlists/pretty/Sci-Fi%20Scapes.md)
- [Shoegaze Classics](/playlists/pretty/Shoegaze%20Classics.md)
- [Skatepark Punks](/playlists/pretty/Skatepark%20Punks.md)
- [Sleep](/playlists/pretty/Sleep.md)
- [Soft Pop Hits](/playlists/pretty/Soft%20Pop%20Hits.md)
- [Songs to Sing in the Car](/playlists/pretty/Songs%20to%20Sing%20in%20the%20Car.md)
- [Songs to Sing in the Shower](/playlists/pretty/Songs%20to%20Sing%20in%20the%20Shower.md)
- [Soul 'n' the City](/playlists/pretty/Soul%20'n'%20the%20City.md)
- [Streamed](/playlists/pretty/Streamed.md)
- [Summer Days](/playlists/pretty/Summer%20Days.md)
- [Summer Hits](/playlists/pretty/Summer%20Hits.md)
- [Summer Party](/playlists/pretty/Summer%20Party.md)
- [Sunny Day](/playlists/pretty/Sunny%20Day.md)
- [Synthwave | Retro | 80s Vaporwave](/playlists/pretty/Synthwave%20|%20Retro%20|%2080s%20Vaporwave.md)
- [tear drop](/playlists/pretty/tear%20drop.md)
- [Techno Bunker](/playlists/pretty/Techno%20Bunker.md)
- [The Good Cup](/playlists/pretty/The%20Good%20Cup.md)
- [The Other List](/playlists/pretty/The%20Other%20List.md)
- [The Piano Bar](/playlists/pretty/The%20Piano%20Bar.md)
- [The Sound of Medieval](/playlists/pretty/The%20Sound%20of%20Medieval.md)
- [This Is Barry White](/playlists/pretty/This%20Is%20Barry%20White.md)
- [This Is Grimes](/playlists/pretty/This%20Is%20Grimes.md)
- [This Is Lady Gaga](/playlists/pretty/This%20Is%20Lady%20Gaga.md)
- [This Is Tiësto](/playlists/pretty/This%20Is%20Tiësto.md)
- [Today's Top Hits](/playlists/pretty/Today's%20Top%20Hits.md)
- [Totally Stress Free](/playlists/pretty/Totally%20Stress%20Free.md)
- [Twenty One Pilots Radio](/playlists/pretty/Twenty%20One%20Pilots%20Radio.md)
- [Ultimate Indie](/playlists/pretty/Ultimate%20Indie.md)
- [United States Top 50](/playlists/pretty/United%20States%20Top%2050.md)
- [Unwind 00s](/playlists/pretty/Unwind%2000s.md)
- [Warm Fuzzy Feeling](/playlists/pretty/Warm%20Fuzzy%20Feeling.md)
- [Wild + Free](/playlists/pretty/Wild%20+%20Free.md)
- [Women of Pop](/playlists/pretty/Women%20of%20Pop.md)
- [You & Me](/playlists/pretty/You%20&%20Me.md)
- [Young & Free](/playlists/pretty/Young%20&%20Free.md)
- [Young, Wild & Free](/playlists/pretty/Young,%20Wild%20&%20Free.md)
- [Your Favorite Coffeehouse](/playlists/pretty/Your%20Favorite%20Coffeehouse.md)
