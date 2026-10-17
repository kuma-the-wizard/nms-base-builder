## 18.1.78 - Independent recovery timer and visible status

- Prevent other add-ons' save-copy operations and normal saves from restarting BBE's recovery countdown or clearing its placement count. Only a project-path change starts a new schedule.
- Keep the load-time deadline when Blender delays the first safe idle tick.
- Show the countdown, placement progress, waiting reason, or backup error in Recovery. Retry failed backups after one minute rather than silently waiting another full interval.
- Wait for active transform/sculpt/paint operations before saving; retain three consecutive independent recovery generations.

## 18.1.77 - Import designs without a base type

- Accept shared JSON/TXT designs with missing, blank, or unsupported base-type metadata using the selected fallback for Blender's scene metadata.
- Preserve supported base types, all part records, and the original source file. Normalize metadata before changing the current scene.
- Verify the reported 676-part TXT design imports completely.

## 18.1.76 - Direct prefab catalogue

- Restore the prefab catalogue below the prefab actions in both the top bar and sidebar.
- Remove the Parts selector/list and nested Legacy Asset Browser panel; rename the sidebar section Prefabs.
- Cache the catalogue outside scene undo data, refresh on startup/file load and prefab save/delete, and provide a refresh button for externally added files.

## 18.1.75 - Focused Prefabs and compact recovery controls

- Remove the legacy Parts/Prefabs browser block from the top-bar Prefabs dropdown while keeping prefab actions and the separate Asset Browser.
- Narrow Scene Preview to 14 UI units and Project Recovery to 16.
- Put the recovery mode and Minutes/Qty value side by side in the top bar and sidebar. Retain the existing time, placement and rotation behavior.

## 18.1.74 - Compact dropdowns and colored action icons

- Reduce individual toolbar dropdown widths by 8-30 percent while retaining the Color palette width and natural header label sizes.
- Add 43 transparent action icons covering 74 existing symbol names throughout shared toolbar/sidebar controls, Save Manager, recovery, optimizer, and support menus. Keep native state indicators and unmapped icons available through a safe fallback.
- Reuse the toolbar symbols in toolbar customization.

## 18.1.73 - Compact credits, colored sidebar and Recovery menu

- Give Project Recovery its own top-bar menu beside BBE, sharing the sidebar recovery controls.
- Tighten the two native-text credit lines and their punctuation spacing while preserving the purple EXTENDED word size.
- Turn the hammer striking face downward without moving the handle. Reuse colored toolbar symbols in matching sidebar headers; add distinct recovery, save and shield/update symbols.
- Default Import/Export, Save Manager and Transformations to collapsed, so fresh workspaces start with only BBE expanded. Preserve Blender saved workspace panel states.

## 18.1.72 - Native credit text

- Render creator names, Base Builder and credit punctuation with Blender native text for sharp UI rendering. Keep only the purple EXTENDED credit word as artwork and align both colons with their names on the text baseline.

## 18.1.71 - Hammer, RGB icon and clear BBE branding

- Use a recognizable hammer for Builder and three additive RGB circles with a white center for Color.
- Replace the cramped branding row with crisp, stacked Base Builder / EXTENDED artwork, the existing logo and smaller creator credits. Keep the sidebar compact at different widths and UI zoom levels using a native preview, without adding project images or textures.
- Put BBE on the left of its panel header and the short version label on the right.

## 18.1.70 - Clearer toolbar icons and save selection

- Keep the familiar top-bar symbol shapes, draw their colors in the symbols themselves on transparent backgrounds, and strengthen their small-size strokes. Remove the colored circular badges.
- Label Account and Save Slot as separate steps in both Save Manager views. Until a slot is chosen, explain where ship imports will appear and show their button disabled instead of silently omitting it.

## 18.1.69 - Ship Management loading progress

- Show progress while Ship Management reads, verifies, backs up and writes game save files, including creation of a new save slot. Keep the existing verified write and rollback behavior.

## 18.1.68 - Visible import and export progress

- Show staged progress for Optimize & Export to Save, including part collection, save loading, verification, backup and replacement. Start the confirmed export after the dialog closes so its progress bar is visible.
- Show progress when reading builds, loading the save list, importing from a game save, and exporting to the clipboard or standalone project, base and Corvette files. The existing model import and proxy loading bars remain in place.
- Refresh the four corrected B_STR_T NW display meshes when an older BBE project opens, in Detailed or Simple proxy mode. Leave user edited meshes alone. These display meshes do not change the game's native model; the correction makes Blender's preview match it.

## 18.1.67 - Fuel pod rim proxies and BBE navigation

- Load the four authored NW fuel-pod cover rim meshes instead of rebuilding them from the NE rim. The rebuilt meshes disagreed with the individual assets. Switching Simple Proxies to Detailed Proxies refreshes these parts in existing projects.
- Move Project Recovery from I/O to the BBE top-bar menu and its own panel in the BBE sidebar category. Keep backup folder controls with recovery.
- Compact the sidebar brand block, show BBE and the version in its panel header, and retain DjMonkey and FuriousFurby credits and support links. Add a purple Extended badge.
- Add distinct colored symbol icons to the top toolbar menus for faster visual scanning.

## 18.1.66 - One configurable backup folder

- Store new project recovery copies and game-save backups under one shared backup folder, separated into Projects and Game Saves subfolders. The default is NoMansSkyBaseBuilder/Backups in the user home folder.
- Add Open Backup Folder and Change Folder controls to both I/O menus and add-on preferences. Folder changes apply to both backup types; earlier backups stay in their original locations. Recovery copies in the prior Blender configuration location remain available in the recovery menu.
- Keep the save-slot backup shortcut scoped to that slot's subfolder, and update its labels and help text.

## 18.1.65 - Three rotating recovery slots

- Use three fixed recovery slots for each project. The first, second, and third backup fill them in order; the fourth atomically replaces the first, then the fifth replaces the second.
- Convert the newest three timestamped recovery copies from 18.1.64 to rotating slots on the next backup. Ignore incomplete temporary copies in the recovery menu.

## 18.1.64 - Undo stability and project recovery

- Keep generated hab-window display meshes available to Blender undo; pause decal, window, and lighting refresh while undo/redo settles. Preserve the original undo preference settings during rapid history operations.
- Add independent `.blend` recovery copies with a default 10-minute interval, an optional 5-part trigger, and a limit of three copies per project. Recovery controls and recent copies appear in both I/O menus. Copies do not overwrite the open project or NMS game saves.
- Clarify Save Manager counts: the save-slot total covers owned builds in that slot, while the selected Corvette count covers one saved build. Show the current Blender scene count and source save point, with a read-only refresh button.

## 18.1.63 - First-run update consent

- Ask once whether to enable automatic update checks. Yes enables and saves Blender Online Access and the startup-update setting, then checks for updates.
- No or dismissal keeps automatic checks off and remembers the choice across restarts and upgrades. An existing disabled setting is respected.
- The prompt explains that Blender's global internet access also applies to other add-ons. Forced offline mode stays offline; background sessions do not prompt or start automatic checks.
- Updates & Support can enable checks later using the same Yes/No prompt. Installation of downloaded updates remains user-controlled.
- Includes the complete Colour & Materials sidebar restored in 18.1.62.

## 18.1.62 - Restore the sidebar Colour & Materials section

- Restore the complete Colour & Materials section in the Base Builder sidebar, including the material palette selector, colour swatches, and colour picker.
- Keep the top-toolbar Color menu available alongside the sidebar controls.
- Preserve all fixes and assets from 18.1.61.

## 18.1.61 - Large-room glass placement

- Correct misplaced corner panes on Square Rooms and Square Deepwater Chambers, and floating roof panes on Cylindrical Rooms and Deepwater Chambers. Solid and Material Preview now use the same correctly assembled glass geometry.
- Apply the correction to recognised Detailed Proxy meshes when placing parts, switching quality, or opening older shared projects. Preserve part transforms, export records, texture coordinates, and other geometry; leave custom glass meshes alone.

## 18.1.60 - Sidebar Asset Browser input and visibility

- Keep thumbnail and scrollbar input inside the browser content, allowing Blender's vertical sidebar tabs and resize border to receive clicks normally.
- Hide the thumbnail overlay when its native panel is collapsed, including collapsed panels restored from shared projects. Reset panel visibility when a file loads.
- Use the same bounds for drawing and input, and ignore clipped tiles that are not visible.

## 18.1.59 - Textures in shared Blender projects

- Resolve saved Detailed Proxy textures from another user's downloaded HD library against the local installed pack. This fixes pink decals and materials when opening shared `.blend` projects.
- Match only known BBE library paths and manifest textures; preserve packed artwork and unrelated user images. Loading textures does not save or overwrite the project file.

## 18.1.58 - Category navigation and fossil preservation

- Allow the active Asset Browser category to collapse. Category and group navigation clear the search instead of leaving category headers disabled.
- Keep each fossil's exact variant through Simple/Detailed proxy switches and group/ungroup operations, including group export and restoration.
- Restore damaged fossil proxies when opening older projects if their variant is still recorded. Preserve unidentified fossils and user-edited meshes.

## 18.1.57 - Sidebar build file import

- Make the sidebar's file import button open the same Corvette, base, prefab, and JSON/TXT importer as the I/O menu.

## 18.1.56 - Standalone Corvette and base files

- Add direct import for `.nmsship`, `.nmsbase`, `.nmsprefab`, and build JSON/TXT in the I/O menu, including parts-only files with a selectable base type.
- Export Corvette `.nmsship` packages while retaining their class, inventory, technology, appearance, and other package entries. New ships can use an existing `.nmsship` as a metadata template.
- Export planet, freighter, space, and station bases as `.nmsbase` without changing their BaseType. Clarify that the older File controls work with BBE project JSON and that Save Manager writes to a game save.

## 18.1.44 - Clickable sidebar thumbnails

- Place parts by clicking their full-size images in the NMS Asset Browser sidebar, with the same variant and right-click actions as the separate browser.
- Restore Presets beside Favorites and Recent in the sidebar and keep category, group, and search controls available above the grid.

## 18.1.43 - Detailed proxies and saved Asset Browser recovery

- Allow Detailed Proxies to use the installed model pack while the separate HD scenes/effects component is missing or downloading.
- Repair image paths embedded in newly appended HD models so textures resolve from the installed library instead of the original build machine.
- Point the HD scenes/effects updater to the verified archive on the public release.
- Restore the clickable thumbnail grid when a saved Asset Browser window opens with Blender, and give the sidebar a direct button to open that browser.

## 18.1.42 - Ship Management scene isolation

- Open Ship Management in an independent Blender main window so its empty preview scene cannot replace the ship-building scene or black out Scene Preview.
- Restore the source scene when the manager closes, including OS-window close, and recover older orphaned preview scenes on add-on enable or file load.

## 18.1.41 - Visible import progress from toolbar menus

- Start Save Manager imports after the toolbar click returns, allowing Blender to close the I/O popover before the import progress appears. Cancel if the selected scene or save changes in the meantime.
- Place the viewport progress panel near the bottom so the BBE and Lighting popovers cannot cover it during other long operations.

## 18.1.37 - Browser responsiveness and calibrated preview beams

- Restore class-marker beams to the established FF calibration: 31.1 local units, with placement scale applied once. Existing shortened preview meshes migrate without editing build records.
- Refresh category/search/favourite views immediately. Reuse browser revisions instead of scanning every part on each timer event.
- Bulk-copy thumbnail pixels and use compact RGBA8 GPU textures while retaining the bounded cache and existing image resolution.
- Replace Heavy Landing Gear's placeholder with a transparent render of its bundled model. Move U_PARAGON to Uncategorised / No Build Menu Group.
- Remove Base Files, Build Metadata and Clipboard sections from the I/O popover; retain Save Manager and the existing sidebar workflows.

## 18.1.27 - Save Manager gating and unified backups

- Remove the estimated technology auto-optimizer and DPS projection. Ship Management still displays saved base rolls and supports manual slot editing.
- Restore a right-click menu in the inventory grid for item edits and moving an existing hyperslot.
- Put Duplicate Save immediately below Backup Saves in the sidebar and I/O Save Manager; it no longer depends on an open Ship Management window.
- Reset stale account/ship selection when a save changes. Start each selected save on Planet so Corvette controls require choosing the Corvette tab; import/export and Corvette optimization require a selected build, while Ship Management requires the Corvette tab.
- Back up both save points and available metadata before every export or save edit. The Select Save gear configures backup location and retention per account/save slot. Only new, verified BBE backup generations roll over; previous-version backups are untouched.

## 18.1.26 - Ship Management window and inventory safeguards

- Open Ship Management in its own resizable window with square, paged grid cells and a confirmation before discarding edits. A closed window with an unsaved draft offers recovery.
- Batch grid drawing and use an empty preview scene to keep ship-menu interaction responsive even with complex Blender builds in the main window.
- Read the installed game's Chargeable and StackMultiplier fields: hide internal counts on nonchargeable technology, respect one-per-slot products, and distribute larger cargo quantities across available unlocked cells.
- Make hyperslot text and double outline purple. Place Ship Management beneath Optimize & Export in the Corvette Save Manager.
- Add a primary/secondary technology layout search that keeps modules, rolls and hyperslots intact. Show saved base rolls and relative layout scores; optionally record an observed in-game weapon DPS for a clearly marked projection. Exact game-calculated final stats remain an in-game measurement.

## 18.1.12 - Projected decals and warm pill lighting

- Standalone HD decals conform to receiving hull triangles and stop at gaps and edges; their placement boxes no longer display six copies of the artwork. Existing saved scenes refresh automatically.
- Preserve decal IDs, transforms and export records through projection, saves and proxy changes.
- Restore surrounding orange spill from embedded red/yellow pill lights; combine nearby colored stacks before applying the light budget. White accents, blue reactor/booster lights and self-lit markers remain.
- Existing HD model and scene downloads are unchanged.

## 18.1.10 - Marker alignment and balanced glow

- Shortened all class-marker projections from 40 to 31.1 model units, matching the meeting point measured from FF's three emitters.
- Enlarged the soft emitter halo around the complete marker and made hologram layers additive so stacked bodies do not cut dark silhouettes into the orb.
- Increased reactor and landing-booster spill, reduced generic warm spill, and preserved shadow-free light budgets.
- Evaluate transforms before creating lamps after load; changing part scale refreshes spill strength automatically.
- Updated optional HD scenes/effects component; the main HD model library remains unchanged.

## 18.1.9 - Optional HD scenes, object lighting and landing effects

- Scene pads, space backdrop, hologram display meshes and effect data now install with the persistent HD library; HD icons and all simple proxies remain in the core add-on.
- Existing HD users download only the 8 MB scenes/effects component. New installs download both components through the same Download & Enable confirmation. No model re-download on ordinary add-on updates.
- Delete HD Pack removes both managed components after confirmation. Missing optional assets leave the core functional and show a download button in Lighting & Scenes.

- Audited all 2,275 available HD assets; enabled local spill for emissive items throughout the library, including decorations and technology.
- Added native lamp colour and unlit-material profiles for 573 mapped parts. Lighting retains a bounded 32/64 local-light budget.
- Restored both native hover meshes on Mag-Field Landing Thrusters with animated emission and local light. Animation follows Blender timeline playback.
- Renamed Ship Lights to Object Lights. Display effects follow part transforms and never export as buildable parts.
- Added simple geometry fallbacks for four empty legacy FBX assets: Pipe, Freighter Face Wall, Industrial Room and Settlement Landing Pad.
- Audit coverage is not full game-renderer parity: particles, gameplay-triggered effects and unmapped native scenes remain separately tracked in QA.

## 18.1.8 - Marker projections and reactor lighting

- Longer one-sided A/B/S hologram beams start at the visible emitter; particles no longer protrude behind it.
- Soft additive emitter halos build up when markers overlap, matching the bright stacked-marker effect.
- Ray Tracing is an independent on/off control beside Smooth/Photo quality settings. Existing preview files retain their prior ray tracing state.
- Blue reactor and thruster emissives and local light spill, including Zenith, Medusa, Azimuth and Ceto reactors.
- Display-only changes preserve object IDs, placement, export data and existing HD downloads. Holograms remain lightweight Blender approximations.

# 18.1.7 - Ship glow, ray tracing and open space pad

- Restores coloured ship light spill and emissive glow using original BBE code,
  with the existing local NMS Preview viewer as the visual reference.
- Smooth mode keeps 16 samples and up to 32 shadow-free part lamps. Ray Traced
  mode enables Blender EEVEE ray tracing, 64 samples and up to 64 part lamps.
  Both modes retain all emissive surfaces and only one shadow-casting rig light.
- Uses the fast Bloom compositor rather than FFT Fog Glow.
- Ship Lights, Light Spill and Glow controls; lights follow their parent parts.
  Adding, removing or switching part proxies refreshes their display effects.
- Removes the outpost gravity capsule and flat shield effect cards from scenery.
  The actual platform is open to space, with the build surface at Z=0.
- A/B/S markers now include a soft 10m projection beam, matched to the native
  particle size range, plus electrical motes. These are Blender approximations.
- Updates embedded marker/pad caches when opening older saved previews.
- Display material overrides, compositor and render settings restore when the
  preview is disabled. Original mesh assets, IDs and exported transforms stay intact.
- Small core update; the existing HD proxy library needs no redownload.

# 18.1.6 - Independent BBE scene preview

- Replaces the Charon Forge lighting integration with an original BBE renderer setup.
- Station Corvette Pad, Space Outpost Pad and Deep Space scenes; native standalone
  pads meet Z=0. Space uses a single small static background image.
- Smooth preview: 16 samples, three area lights, one shadow light, no ray tracing,
  screen-space GI or volumetric effects. Photo mode increases viewport samples.
- Grid, axes and light-guide overlays hide automatically, while selection outlines
  and editing gizmos remain available. Previous viewport/world/render settings
  return when Scene Preview is disabled.
- Retires old BBE per-part lamps when opening older scenes; user lights are preserved.
- Adds all three settlement class-marker HD meshes, transparent hologram lettering,
  projection scan lines and a fixed budget of electrical motes/streaks. Scan lines
  animate with timeline playback; effects are a Blender approximation of NMS.
- Marker corrections are tiny core resources; existing HD packs need no redownload.
- Scene objects never enter exported builds. Part transforms and IDs are unchanged.

## 18.1.5 preview - compact removal button

- Place an icon-only trash button to the right of Detailed Proxies. Keep its hover tooltip and deletion confirmation.

## 18.1.4 preview - remove the optional HD pack

- Add a compact Delete HD Pack button below Detailed Proxies, with confirmation and Cancel selected by default.
- Switch all scenes in the current file to simple proxies before removal; keep the pack if any part cannot switch. Only delete the managed downloaded pack, never bundled models or icons.
- Disable removal during downloads and when no downloaded pack is installed. Detailed Proxies offers the normal download again after removal.

## 18.1.3 preview - first-install feedback

- Offer Enable Online Access & Download directly in the HD confirmation, explaining that this changes Blender's global preference. Cancelling leaves the preference unchanged; an explicit offline launch remains respected.
- Keep overall progress moving forward across download, checksum verification and installation. Show phase details and percentage in the viewport header and download panel; avoid a stale progress bar in Blender's cached menu popover.
- Highlight the active Simple or Detailed proxy mode in the Builder menu.
- Reuse the existing verified HD pack; models, textures and icons are unchanged.

## 18.1.2 preview - simpler Detailed Proxies

- Detailed Proxies automatically detects the installed model pack. If missing, one Download & Enable confirmation downloads, verifies, installs and enables it inside Blender.
- Remove folder/ZIP management buttons from the normal prompt and remove the idle library sidebar panel. Show progress and cancellation only during downloads; retain offline ZIP installation in operator search.
- Refresh manifest detection after an on-disk add-on update. Cancelling a download, switching to Simple Proxies or opening another file prevents a pending automatic quality switch.
- Vesper in-game check confirmed by the user; no additional orientation changes in this version.

## 18.1.1 preview - complete simple-model coverage

- Bundle geometry-only fallbacks for 191 parts that previously depended on the optional HD library, including Stag Alloy Annexe and station parts. All HD icons remain bundled.
- Use the same model resolver for browser placement, Save Manager, clipboard imports and proxy quality changes. Re-selecting a proxy quality refreshes older placeholders without changing placements.
- Use the native game placement transforms for 24 Vesper Aerofoil/Cowling variants; correct the approximate upside-down offsets. The reported NE reversal still requires reproduction from the affected build: the NE asset itself matches the native placement.
- Existing HD library installations are retained; this update does not require downloading HD assets again.
- Regression: the FF Corvette imports all 525 records through both import paths, with and without the optional library; export preserves IDs, UserData, timestamps and placement vectors.

# Base Builder Extended 18.1.0 — preview

- Optional HD library installs through Builder > Detailed Proxies, with progress,
  cancellation, checksum verification and an offline ZIP installer.
- Persistent asset storage is shared between Blender versions and survives BBE
  updates. Existing saved scenes can relink their old bundled texture paths.
- Main installer includes Game Lighting & Scenes: game-data planet/space skies,
  time of day, sun direction, scene presets and optional native part lamps.
- Lighting adapted from Charon Forge 0.1.2 with credit; BBE adds independent
  per-scene resources and restoration of previous viewport shading and worlds.
- Lossless HD library cleanup preserves geometry, UVs, normals, materials and
  textures. No mesh decimation or texture downsampling.
- Simple/Detailed preference also applies to subsequent asset placement.
- Existing mirror, pipe endpoint snapping and exported part IDs are preserved.

Save and restart all Blender windows after installing this preview.
The separate HD download becomes public with the corresponding release.

# Base Builder Extended 18.0.18

- Adding a pipe or bubble duct from the native asset browser now mates real
  endpoints with the selected pipe, using the sidebar Snap continuation history.
- Added the textured high-resolution Curved Bubble Duct under its existing
  BASE_BUBPIPE_L ID, preserving the low-proxy origin, orientation and sockets.
- The alternate Qt asset browser now uses the high-resolution asset loader too.
- Existing curved bubble ducts can be upgraded with Builder > High-res Proxies.
  No saved scene or game IDs are automatically changed.

Save and restart all Blender windows after installing.

# Base Builder Extended 18.0.17

- Removed the 14 internal-ID junction experiments and alternate straight/T/X
  bubble entries from the browser after the user's standalone-placement test.
- Kept the established PIPE, PIPESHAPE, CURVEPIPESHAPE, BASE_BUBPIPE and
  BASE_BUBPIPE_L entries. Curved Bubble Duct is back in Structural Adornments
  without an experimental label. Existing snapping and mirror fixes remain.
- Retained model assets, IDs and snap data for loading existing Blender scenes.
  The standalone-junction test files remain available for future investigation.
- This cleanup does not establish new in-game compatibility for any part.

Save and restart all Blender windows after installing.

# Base Builder Extended 18.0.16

- Added all 14 native regular-pipe and bubble-duct junction models under
  Decoration > Pipe Junction Tests: elbow, T, cross, 3-way corner, 4-way corner,
  5-way and 6-way. Each exports its exact internal part ID for user testing.
- Added sockets at every opening, compatibility with existing pipes, and local
  reflection rules for the new geometry. Both mesh quality settings are included.
- Relabelled the previous four bubble variants as Alternate ID Test parts and
  grouped them separately. The ordinary Bubble Duct remains the default straight.
- Native junction models are verified in Blender. Standalone in-game placement
  is deliberately unverified; these entries are for the user's requested tests.

Save and restart all Blender windows after installing.

# Base Builder Extended 18.0.15

- Restored curved (L), straight (S), T and X bubble ducts in both asset browsers,
  with their bundled models and thumbnails, labelled as legacy variants.
- Added end-to-end sockets for every restored shape, including all T/X branches,
  source/target cycling, mixed bubble/ordinary-pipe connections, and rotated parts.
- Corrected low-resolution BASE_BUBPIPE snapping: its centred Z-axis FBX needs
  different sockets from the high-resolution Y-axis native mesh.
- Preserved original object IDs and existing scene geometry. Legacy variant IDs
  are absent from the locally audited current-game object table; Blender snapping
  and serialization do not establish that these IDs work in an unmodified game.
- Retained the user-confirmed 18.0.14 mirror and ordinary-pipe fixes.

Save your work and restart all Blender windows after installing.

# Base Builder Extended 18.0.14

- Replaced Euler mirror guesses with full world/local reflection matrices.
  Audited 779 IDs and supplied geometry-based relations for 695 IDs, including
  native Corvette counterparts, diagonal walls, triangular floors and curved
  walls. Variant rotations and off-centre origins are included. Native detailing
  is retained; intrinsically asymmetric parts still cannot become exact mirror
  images through NMS rotation/Up/At alone and retain legacy handling.
- Mirror keeps native part identity, synchronizes SnapID after counterpart swaps,
  preserves proxy quality and shared source meshes, and supports all three axes.
- Added missing PIPE snap membership, end-to-end defaults for curved/straight
  pipes, and cross-ID pipe matching. Unsupported snaps leave objects in place.
- Sidebar now shows Base Builder Extended and the installed manifest version.
  Base Builder credit remains prominent for DjMonkey; Extended credit is
  Furiousfurby. Original guides, Patreon, Discord and Steam Games remain.
- Updates & Support has a small blue header icon within Blender's normal theme.
- Automated Blender 5.1.2 and 5.2.2 checks cover export roundtrips, double mirrors,
  oblique transforms, actual high/low meshes and physical pipe socket alignment.
  In-game validation remains separate.

Save your work and restart Blender after updating. Existing mirrored placements
are not automatically rewritten; mirror the original parts again to repair them.

# Community update 18.0.9

- Fixed Corvette weapon placement/import using the textured high-resolution
  models while retaining turret handlers and proxy quality switching.
- Rebuilt all six hab/walkway high-resolution models and the Thunderbird
  landing bay with native mesh transforms, correcting detached wall details.
  The bay retains its native hab-style exterior and floor opening.
- Replaced B_TUR_F's placeholder with an actual model thumbnail; both asset
  browsers now resolve the physical icon.
- Fixed bulk colouring of repeated proxy parts: every selected copy now updates
  its visible viewport colour and colour/material labels, rather than only the
  first copy. The colour picker now refreshes every selected copy as well.
- Mixed high-resolution and proxy selections keep their original geometry and
  textures. Colouring preserves each part's reserved UserData bits, transforms
  and selection; unselected parts retain their existing colours.
- Fixed the update handler during extension startup when Blender temporarily
  has no active view layer. Colour changes request a normal viewport redraw.
- Included the previously local shared-builder, material-provider and runtime
  part-handler integration hooks. They use the built-in implementation by
  default and do not require a companion add-on.
- Retained the reactor/girder mirror mappings, curve starting alignment and
  path-following rotation, fossil imports, cuboid models and station references
  from 18.0.8. Models, textures and dependency wheels remain bundled.
- Tested the final package in isolated Blender 5.1.2 and 5.2.2 LTS processes.
  These are Blender/serialization checks; no new in-game validation is claimed.

Install the attached plugin ZIP through Install from Disk, then restart Blender.
Parts previously changed to the wrong design must be restored separately.

# Community update 18.0.8

- Restored normal Duplicate Along Curve rotation: copies turn with the path
  and form a flower around a circle. Supersedes 18.0.7's parallel-copy behavior.
- Corrected only the starting alignment: the first copy at the curve's start
  matches the selected source's orientation, replacing the forced 180-degree
  X rotation. Following copies keep that relative alignment as the path turns.
- Retained curve radius, tilt, Objects Size and curve-transform behavior.
  Part IDs are repeated unchanged; counterpart swaps remain Mirror-only.
- To repair an array made in 18.0.7, restart Blender, select the original source
  part plus that curve, then run Duplicate Along Curve again. Reseeding removes
  the old world-orientation locks. Existing saved layouts are not auto-migrated.
- Verified five-petal circles, tilted circles, Euler/quaternion sources, open
  Bezier and NURBS paths, quantity changes, copying/reseeding arrays, save/reopen,
  export IDs, unlinking, and repair of a saved 18.0.7 array. Visually checked a
  Blender render using B_STR_J_NE. No in-game test claimed.

# Community update 18.0.7 (curve behavior superseded by 18.0.8)

- New Duplicate Along Curve arrays preserve the source part's world rotation,
  orientation and scale. The curve supplies positions only: copies do not turn
  with the path or inherit its tilt, point radius or object scale.
- The explicit Objects Size control remains available as a multiplier of the
  original scale. Ordinary duplication never selects a mirrored counterpart.
- Closed curves place copies around the loop without stacking the last copy
  over the first. Replacing a curve's source uses the new source's transforms
  and the requested quantity instead of reusing the old array's values.
- Existing saved curve arrays retain their previous layout. To use the new
  behavior on one, select the original source part and that curve, then run
  Duplicate Along Curve again. Save your work and restart Blender after updating.
- Mirror counterpart fixes from 18.0.6 are retained. Blender regression checks
  cover open/circular/NURBS paths, transformed curves, three rotation modes,
  parent/delta transforms, quantity changes, duplication, export vectors,
  unlinking, save/reopen and legacy layout compatibility. No in-game test claimed.

# Community update 18.0.6

- Replaced guessed mirror suffixes with an explicit registry of 266 native
  Corvette counterpart pairs. Unknown/unpaired IDs keep their original design.
- Reactors B_GEN_0 through B_GEN_3 no longer change design when mirrored.
  Numbered B_CON2 hull links also retain their design.
- Corrected the four B_CON_L_n / B_CON_R_n connector pairs; restored the Osprey,
  Arcadia heavy booster and both numbered Rockhopper wing counterpart mappings.
  Kept genuine numbered Streamlined Trim Cap and Aeron Diffuser pairs.
- Updated mirror metadata to match the registry. This also fixes the shared
  counterpart resolver used by groups and curves, not just the sidebar button.
- Auto-duplicate and mirror now changes the new copy, leaving the original
  object and mesh unchanged. In-place curve mirrors update follower meshes and
  exported part IDs, not only the curve's seed ID.
- Regression checks cover all 266 pairs in both directions, exported IDs,
  positive object transforms, double-mirror restoration, all four reactors,
  hull-link designs, groups and curve followers. No in-game test claimed.
- Restart Blender after updating. Parts already changed to the wrong design
  are not automatically identifiable; restore those from an unaffected build
  or manually select the intended original part.

# Community update 18.0.5

- Fixed Builder Tools > Duplicate passing a Part wrapper to Blender's selection
  API. Part, prefab and curve duplicates now return selectable Blender objects.
- Duplicate Along Curve now stores the requested quantity before update handlers
  run and synchronizes the curve controls. A count of one stays one instead of
  growing to two during the spacing refresh.
- Removed the launch buttons from Workspace and Parts & Prefabs. The NMS Asset
  Browser sidebar remains available; existing browser operators are retained.
- Rebuilt CUBEROOM and CUBEGLASS from native standalone placement rules and
  Part_* locators, with matching high-resolution and legacy FBX geometry.
  Preserved native UVs, normals and existing high-resolution materials/textures.
  Only the highest-detail shell is included, not stacked LODs, invisible proxy
  volumes or animated power overlays. Adjacent-room wall removal is not simulated.
- Restart Blender and re-import the affected rooms to replace cached old meshes.
  Existing open scenes are not automatically rewritten. No save-data transforms
  or in-game files are changed by this fix.

# Community update 18.0.4

- Fixed fossil imports returning a deleted placeholder object. Clipboard,
  Save Manager, Open Base and prefab import now receive the replacement object.
  Fossil transforms, palette data, timestamps and ordering are retained.
- Regression coverage includes all 143 fossil variants with repeated placements,
  and a 424-part Corvette containing a FOS_SKULL / FOS_HEAD_HD fossil.
- Compatibility audit against installed game executable 179666 (September 22,
  2026): current saves decode and round-trip through private copies; all 2,124
  build-object IDs and 1,344 part IDs remain present. Building globals are
  byte-identical to the previous audit.
- The game changed some placement flags, freighter styles/palettes and station
  scene definitions. The bundled model/reference library is retained in this
  bug-fix release; visual parity with every updated scene and in-game placement
  have not been revalidated. See GAME_UPDATE_COMPATIBILITY.md.

# Community update 18.0.3

- Added a separate **Vanilla Hidden Station Parts > Interior** Asset Browser
  category for audited native game assets that are valid station build objects
  but hidden from the normal construction menu.
- Restored `GAMETABLE` as **Holo-Arena Game Table**. The current 7.01 game table
  marks it placeable in station interiors and back sections and retains its
  native model, scaling and 3-D rotation. This update claims visible placement,
  not automatic initialization of the multiplayer game interaction.
- Re-audited the 7.01 build tables against Cosmos 7.0: no station ObjectID,
  part-model mapping or station placement flag changed in the hotfix.

# Community update 18.0.2

- Import from Clipboard and Open Base (.json) now automatically load the station
  reference when the imported record identifies a PlayerSpaceStationBase.
- Those imports expose a collapsed Station Reference section under Import/Export,
  without requiring Save Manager or access to a local save slot.
- Parts-only JSON remains a parts-only import. Arrays are accepted as well as
  Objects dictionaries; station detection never uses a previous import's type.
- Station records without GalacticAddress load with an isolated appearance key.
- Checked the real clipboard operator with a 318-part station, JSON-file imports,
  repeat imports, reference refresh, and ordinary base/Corvette imports.

# Community update 18.0.1

Based on Kuma's 18.0.0 release of DjMonkey's No Man's Sky Base Builder.

- New parts use their default origin and scale when the active object is deselected. Selected-object placement still works across high-res, proxy, and special-part paths.
- Station imports automatically add the compact reference: all six hull families, large optional attachments, and six interior cutaways. Repeated geometry is shared and cutaways are prebuilt.
- Station and orbital Space bases have separate Save Manager tabs. Station reference controls appear only under Station.
- Reference refresh preserves player parts and eye choices. Remembered station visibility and compact Outliner defaults are retained.
- All 22 custom settlement icons and the three missing settlement class-marker catalog entries are included in both browsers.
- Mixed special/ordinary parts retain save order on export. Station identity includes its system address. Renaming a station does not rename a ship; Corvette rename accepts valid ship slots.
- Dependencies are bundled for Windows / Blender 5.1, without first-use pip downloads.
- DjMonkey's branding and support links are preserved. Contributor credits for Kuma and FuriousFurby are in Preferences and CONTRIBUTORS.txt.

Kuma's high-resolution assets, native movable Asset Browser, favorites and recents, proxy switching, material system, group tools, and Cosmos save translation are retained. The station reference files contain their own geometry; the reference's dimensions and surfaces have not been simplified.

For habs or the Thunderbird bay already placed in an older saved scene, select
those parts and switch to Low-Res, then back to High-Res to refresh their meshes.
