# COSMOS release and station reference integration

This contribution combines Kuma The Wizard of Cosmos's published 18.0.0
COSMOS release with the station reference integration and fixes contributed by
FuriousFurby. DjMonkey remains the original creator. His branding, artwork,
creator credit, community links, and support links are preserved.

## Source of the combined update

The starting repository commit is `d6f0bce1b1b9b2bbc662543dbc14326e83a5cd79`.
It predates the contents of Kuma's downloadable release, so this pull request
also includes his intervening code, model, texture, and browser updates.

Kuma's unmodified baseline is the `no_mans_sky_base_builder-18.0.0.zip` asset
on [the bp_v1.3 release](https://github.com/kuma-the-wizard/nms-base-builder/releases/tag/bp_v1.3).
Its SHA-256 is `ed55483a975a94ab7f0f915a71068d555e172808e80be17d08ce47e40dcc1a2c`.

Relative to that archive, the community integration changes or adds 79 files.
All 6,437 files under Kuma's `models` and `models-high-res` directories are
unchanged from his release. The upstream development helper
`asset_browser/utils.py` remains in the source tree and is excluded from the
Blender installer through the extension manifest.

## Additional changes by FuriousFurby

The 18.0.2 follow-up also recognizes complete station-base JSON imported through
Import from Clipboard or Open Base. It loads the reference automatically and
offers a collapsed Station Reference section under Import/Export, independent of
Save Manager. Objects-only JSON contains no base type and remains a parts-only
import. This path was checked with the real clipboard operator and a 318-part
station, plus ordinary bases, repeat imports, missing addresses and JSON files.

- New parts inherit the active object's transform only when that object is
  selected. With nothing selected, placement retains the part's default origin,
  rotation, and scale. This covers both builders and native browser placement.
- A separate Station save-import tab loads player parts alongside a reference.
  Exterior selection is manual: six hull families and their large optional
  shapes can be toggled and remembered per station.
- Station Reference contains Outside and Inside collections, separate from
  Station Player Parts. Interior roof and wall sections can be hidden for
  editing. Reference geometry is excluded from game-save exports.
- Shared geometry makes the reference smaller and quicker to load. Import and
  refresh use a compact Outliner layout, and reference controls appear only in
  Station mode.
- Station identification and rename fixes, preservation of imported part order,
  missing station proxy support, and settlement marker names and icons.
- Offline dependency wheels and secondary contributor credits in preferences
  and the included contributor document.

## Compatibility and validation

The combined 18.0.1 extension requires **Blender 5.1 on Windows x64**. This is
more restrictive than the old source manifest: the reference library was saved
with Blender 5.1, and the bundled dependency wheels target Windows.

The release-based build was checked in Blender 5.1.2, including placement with
and without selection, a 318-part station import/export using private save
copies, reference refresh and visibility persistence, compact Outliner state,
Station-only controls, contributor credits, and settlement icons. Clean-package
validation checked 2,257 high-resolution libraries and their 16,157 external
image references. Private saves, local appearance profiles, and test output are
not part of this repository update.

The installer is built from `src/addons/no_mans_sky_base_builder` using Blender's
extension build command. Required wheels and reference libraries are included;
the generated installer ZIP belongs in a release, not in source control.
