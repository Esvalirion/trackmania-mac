# trackmania-mac

Run **Trackmania (2020)** on Apple Silicon Macs with one script. Free, no CrossOver, no Whisky, no GUI wrapper.

```sh
git clone https://github.com/Pab450/trackmania-mac.git
cd trackmania-mac
./tm install   # ~260 MB runtime + Ubisoft Connect
./tm run       # sign in, install Trackmania, then ./tm run again
```

Tested on an M1 Pro running macOS 26.6 (Tahoe), September 2026.

## Requirements

- Apple Silicon Mac, macOS 14 or later
- Rosetta 2: `softwareupdate --install-rosetta --agree-to-license`
- `python3` (ships with the Xcode Command Line Tools: `xcode-select --install`)
- A Ubisoft account. Trackmania is free to play; Club access is tied to your Ubisoft account, whichever store you bought it on.

## Usage

| Command | What it does |
| --- | --- |
| `./tm install` | Downloads the Wine runtime, creates the prefix, installs Ubisoft Connect |
| `./tm run` | Launches Trackmania, or Ubisoft Connect if the game is not installed yet |
| `./tm kill` | Stops every Wine process |
| `./tm logs` | Follows the Wine log |
| `./tm wine <args>` | Runs a command in the prefix, e.g. `./tm wine winecfg` |
| `./tm reset` | Deletes the prefix (Ubisoft Connect and the game), keeps the runtime |

Launch the game with `./tm run`, not with the **Play** button in Ubisoft Connect. The button can hang on "Preparing to launch your game" under Wine.

### Renderer

`TM_RENDERER` picks the Direct3D 11 to Metal translator:

| Value | Translator |
| --- | --- |
| `d3dmetal` (default) | Apple's D3DMetal, from the Game Porting Toolkit |
| `dxmt` | [DXMT](https://github.com/3Shain/dxmt), a DX10/11 to Metal layer |
| `wined3d` | Wine's own OpenGL backend, as a last resort |

```sh
./tm kill && TM_RENDERER=dxmt ./tm run
```

The game inherits the renderer from Ubisoft Connect, so always run `./tm kill` before switching.

### Files

Everything lives in `./data` (override with `TM_DATA`): the runtime, the Wine prefix and the game. To uninstall, delete `./data`.

## How it works

```
Trackmania.exe + Ubisoft Connect (32-bit, Chromium Embedded Framework)
        │
Wine 9 built from CrossOver 24 sources (Sikarugir engine), WoW64, Rosetta 2
        │
D3DMetal or DXMT ──► Metal
```

Getting there took two fixes the usual wrappers lack:

1. **The Wine version.** Apple's Game Porting Toolkit (what Whisky used) is based on Wine 7.7. Current Ubisoft Connect needs WinRT APIs that Wine 7.7 lacks and aborts on startup. Newer upstream Wine gets further, but every Chromium renderer process crashes, which leaves the Ubisoft Connect window blank.
2. **The libcef patch.** The CrossOver-based engine starts Ubisoft Connect with `--in-process-gpu --disable-gpu`. Ubisoft builds its embedded Chromium with command-line switches disabled, so the flags are silently ignored. CrossOver fixes this by patching three bytes of `libcef.dll` in memory ("CW HACK 25737", public in the [CrossOver sources](https://media.codeweavers.com/pub/crossover/source/)). [`patch_libcef.py`](patch_libcef.py) applies the same change to the file. `./tm run` re-applies it before every launch, because Ubisoft Connect updates itself.

Other settings, all in [`tm`](tm):

- `WINE_SIMULATE_WRITECOPY=1`: a CrossOver compatibility switch for Chromium's memory-protection checks.
- `WINEMSYNC=1`: Mach-semaphore synchronization, recommended for DXMT.
- Wine's `renderer=gl`: stops Ubisoft Connect from crashing during GPU detection.
- Crash dialogs are disabled: crashes are logged instead of opening a debugger window.

Every download is pinned and verified by SHA-256, except the Ubisoft Connect installer. Ubisoft serves only the latest version, and the client updates itself anyway.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `warning: Unknown libcef.dll build` and a blank Ubisoft Connect window | Ubisoft shipped a new Chromium. Look up the matching `CW HACK` bytes in the latest CrossOver sources (`dlls/ntdll/loader.c`) and update `RVA`, `BEFORE` and `AFTER` in `patch_libcef.py`. PRs welcome. |
| Parts of the track are missing | Set shader and texture quality to High or Very High in the game settings. |
| Crash when loading a track, or poor performance | Try the other renderer: `./tm kill && TM_RENDERER=dxmt ./tm run`. |
| Stuck on "Preparing to launch your game" | Close Ubisoft Connect with `./tm kill` and start the game with `./tm run`. |
| Anything else | `WINEDEBUG=err+all ./tm run`, then check `./tm logs` and `data/prefix/drive_c/Program Files (x86)/Ubisoft/Ubisoft Game Launcher/logs/`. |

## Development

```sh
shellcheck tm
python3 -m unittest discover tests
```

To update a pinned component, change its URL and SHA-256 at the top of `tm`, then test a clean install: `TM_DATA=/tmp/tm-test ./tm install`.

## Credits

- [Sikarugir](https://github.com/Sikarugir-App): the Wine engine and runtime template, including D3DMetal and DXMT
- [CodeWeavers](https://www.codeweavers.com): CrossOver, whose open-source Wine patches make Ubisoft Connect work
- [Gcenx](https://github.com/Gcenx): Wine for macOS builds
- [3Shain/dxmt](https://github.com/3Shain/dxmt)
- [wiesson/mac-gaming](https://github.com/wiesson/mac-gaming): Chromium-under-Wine debugging notes

## Disclaimer

Not affiliated with Ubisoft, Nadeo, Apple or CodeWeavers. This repository contains no game, Wine or Apple binaries; `./tm install` downloads them from their publishers. D3DMetal is covered by Apple's license. `patch_libcef.py` modifies Ubisoft Connect's `libcef.dll` in your local install only. Use at your own risk.

## License

[MIT](LICENSE)
