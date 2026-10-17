release 18.1.84
-------------

### Corvette picker
- Close the Corvette selection menu after choosing a ship. Keep its button labeled Select Corvette and show the selected ship below it.
- Remove freighters from selectable ship lists and selection lookup in both Main and Expedition saves. Preserve Corvette health warnings and repair actions.

release 18.1.83
----------------

- Fixed WASD being blocked by the sidebar Asset Browser listener in saved workspaces; active transforms and controller sessions still retain input ownership.
- Keep export progress visible through validation, verified writes and list refresh.
- Speed up save checks by avoiding unnecessary copies of unchanged data and repeated translation-table construction, retaining backups and preservation validation.

release 18.1.82
-------------

## Cockpit selector stability and feature help

- Fix changing/garbled cockpit selector labels by retaining their strings for the dialog and undo/redo lifetime. The reviewed cockpit list stays stable; changed or removed entries require reopening instead of redirecting a selection.
- Add Swap Cockpit Order to both BBE menus, retaining the Optimizer Settings shortcut. The swap changes scene export order immediately, never physical placement. Ordinary and optimized exports use that order; saving the .blend keeps it with the project, and Undo/Redo works.
- Add clearer hover descriptions, contextual How this works popups and BBE Feature Help. Topics explain cockpit order, optimizer settings, Corvette export, keep-build repair, file replacement, recovery and WASD navigation, including when changes take effect and what can undo them. Help is local and does not modify data.

## Ship warnings, keep-build repair and new-slot export

- Check Corvette health as soon as a save is loaded. The shared I/O selector highlights affected builds in red, explains the problem and identifies ship slots consistently as 1–12. Missing-build Corvettes are also listed; the freighter stays separate.
- Add Repair — Keep My Build directly below the selected build in I/O, in both the top bar and sidebar, and Repair Build in Ship Management. Repair retains the saved objects, transforms, colors and readable inventories, technology, hyperslots, class, stats and appearance. Invalid data resets are listed and require separate confirmation. A missing build can be supplied through scene export or Replace From File.
- Add Overwrite Selected Ship / New Empty Ship Slot to ordinary and optimized Corvette Export to Save. New slots use the minimal Corvette ship record with exactly the scene objects; no template parts are added. Slots reserved by orphan builds are never treated as empty. Both Main and Expedition contexts are supported.
- Never add a missing cockpit during repair or export. Show an unflyable-ship warning and allow the operation. Repairs without a cockpit keep their warning in the selector until the user adds one.
- Stale selections, changed scenes or optimizer settings, changed save files and competing Ship Management drafts are rejected; verified backups precede writes. Preserve unrelated ships and freighter data.
- Keep ordinary and optimized objects-only exports from overwriting or renaming a non-Corvette ship through an uncertain build link. Complete reviewed replacement remains available to correct the slot.
- Preserve ship inventory, class and appearance when importing a Corvette from a game save, so Export Corvette works without first importing a .nmsship template. The source metadata survives saving and reopening the Blender project. Older projects can explicitly use the original Corvette selected in I/O while retaining their current edited parts.
- Use the same save-point selection in the list, importer and Ship Management, including equal timestamps.
- Show mismatched ship slots in red, with a brief reason and full details in Link Status. Keep the manager open and safe inventory edits available.
- Keep Replace From File as a separate explicitly reviewed option. A complete .nmsship replaces ownership, inventories, appearance and the linked build together; objects-only replacement requires one correctly linked Corvette.
- Require confirmation for duplicate build replacement. Preserve unrelated ships, builds, contexts and freighter data. Save Changes revalidates the draft, checks external changes, creates verified backups and rolls back failed writes.
- Verified with English/obfuscated synthetic saves, the supplied report in memory, backup/rollback tests and Blender 5.1.2 / 5.2.2. No in-game repair validation is claimed.

## Optional WASD navigation

- Matching WASD Navigation toggles in the BBE dropdown and sidebar. Off by default; settings follow Blender add-on preferences.
- Hold right mouse for look and WASD/arrow movement; Q/E moves vertically, Shift speeds up, Ctrl slows down and wheel adjusts speed. Release right mouse or Esc stops. Quick right-click retains the context menu.
- Works in Object and Mesh Edit modes with left-click selection. Changes only the viewport, leaving camera view before movement; does not transform objects or the camera. Existing modal tools/controller sessions retain input.
- Timers run only during navigation and stop on release, disable, file load or unregister. Native keymap and lifecycle checks passed in Blender 5.1.2 / 5.2.2.

## Saved Asset Browser compatibility

- Restore the thumbnail grid for older saved Asset Browser layouts that used an unlinked cube helper. Keep normal model objects out of automatic helper cleanup.

## Opt-in Blender diagnostic tickets

- Send captured BBE errors to the owner inbox as Blender Diagnostics after explicit approval, without Discord, an account, email, a private reporter link, replies or attachments.
- Respect Blender Online Access and offline mode. Automatic prompts wait for online access and an idle 3D View. Preview the error and review the full local report before sending; reporting never enables networking.
- Include BBE/Blender versions, platform and detailed proxy-pack availability. Redact common personal paths, credential fields and email addresses. No project, game save, screenshot or attachment is uploaded.
- Use a separate bounded Python helper so sending does not block Blender. Failed sends remain local for manual retry; per-report identifiers prevent duplicates after a lost response. Status and Review / Send Last Error appear in Updates & Support.
- Capture handled errors in Ship Management, import/export, recovery and other BBE operators, as well as uncaught execute/invoke exceptions. This does not collect native Blender crash dumps.

Website support 2.1.0 was deployed and independently verified before publication of 18.1.84. Local client/server integration, consent/offline tests and Blender 5.1.2 / 5.2.2 checks passed. Normal website support conversations remain available separately.

release 18.1.81
-------------

## Ship Management with uncertain Corvette links

- Open Ship Management when an existing Corvette build link is missing, duplicated, invalid or points to an unrecognized ship. A fresh install no longer makes these existing save conditions look like a failure to open the manager.
- Keep inventory, cargo, technology, ship class, saved stats and existing hyperslot edits available. Before saving, compare the complete draft with the original snapshot and preserve all uncertain ownership, build and surrounding context records exactly.
- Lock Move Up/Down and Add Minimal Corvette only in affected Main or Expedition contexts. Healthy contexts remain editable independently. Duplicate Save / Clear Builds still requires valid links in every context.
- Add an Ownership notice / Link Status dialog explaining the affected context and slots locally. No save upload is required and no ownership link is guessed or automatically rewritten.
- Start on the selected Corvette and context when available, otherwise the active or first owned ship.

Verified with synthetic English-key and obfuscated saves and Blender 5.1.2 / 5.2.2 LTS operator tests. The notice and disabled controls were also inspected in Blender 5.2.2. This protects existing uncertain links; it does not repair them or claim in-game validation of the reported user's save. The existing verified-backup writer is unchanged.

release 18.1.80
-------------

## Detailed proxy loading and Asset Browser helper

- Resolve each detailed model's texture paths against the local HD pack before the model enters the scene. Progress redraws should no longer show the pack author's missing texture paths as pink materials.
- If a detailed texture is missing or the optional pack is damaged, reject that model and keep or use its simple proxy. Projects saved on another computer with unavailable detailed textures switch their BBE parts and groups to simple proxies on opening; object identities, transforms and group caches are retained. The original `.blend` is not overwritten.
- Remove BBE's hidden Asset Browser context helper from the scene after its window closes, while retaining it for the next browser launch.

The detailed-proxy pack remains optional. These changes were tested with the pack installed, with its textures unavailable, and with simple-proxy fallback in Blender 5.1.2 and 5.2.2 LTS. Install **no_mans_sky_base_builder-18.1.80.zip** through Blender's **Install from Disk**, then restart Blender.

release 18.1.79
-------------

## Group color reset and Charon Forge activation check

- Fix Reset Default Color on a selected group. It restores each child part's cached color, including simple proxies, without the group's missing `ObjectID` error.
- When Charon Forge is active or set to load at startup, BBE asks before activating: Continue disables Charon and enables BBE; Cancel keeps Charon and leaves BBE inactive.
- If Charon is enabled after BBE, BBE warns that the current session is incompatible and asks for a save and restart. BBE cannot control Charon's installer or safely undo their overlapping registrations after Charon has activated.
- The reported Blender 5.2 `acquire(): cookie doesn't exist!` traceback occurs in Blender's extension installer before BBE code runs. Save work, fully restart Blender, then retry Install from Disk. If it recurs, check whether Blender's session temporary directory is being removed.

Install the intact **no_mans_sky_base_builder-18.1.79.zip** via Blender's **Install from Disk**, then restart Blender. Tested in Blender 5.1.2 and 5.2.2 LTS; the Charon prompt was checked in a separate Blender 5.1 GUI session. Existing projects and game saves were not changed.

release 18.1.78
-------------

## Recovery, stability and a clearer interface

### Automatic project recovery
- Fix recovery timers being repeatedly restarted by other add-ons' save-copy operations or normal saves. BBE now keeps its own schedule, including after a delayed first idle tick.
- Choose a time interval (10 minutes by default) or placement count (5 parts by default). Keep the latest three consecutive recovery saves per project; each new save replaces only the oldest generation.
- See the live countdown, placement progress, waiting reason, and backup errors. Failed backups retry after one minute.
- Use the dedicated Recovery menu or sidebar panel to back up now, open a recovery copy, or open/change the shared backup folder. Project copies and game-save backups use separate subfolders.
- Recovery copies do not overwrite the original project. Saving waits while undo/redo settles or an active editing operation makes saving unsafe.

### Stability and importing
- Harden rapid undo/redo handling around generated window meshes, decals and lighting refresh.
- Import JSON/TXT designs with missing or blank base-type metadata using the selected fallback, including designs that have never been assigned to a ship or base.
- Add visible staged progress across import/export workflows, including Optimize & Export and Ship Management save operations.
- Correct the four B_STR_T NW fuel-pod cover rim display meshes and refresh recognized older proxies without replacing custom edited meshes.
- Clarify scene, selected-build and save-slot part counts, and the Account/Save Slot selection steps.

### Interface improvements
- Restore the direct prefab catalogue in both toolbar and sidebar; remove the obsolete Parts list and nested Legacy Asset Browser section.
- Add transparent colored symbols across the toolbar, sidebar and action controls, with RGB Color and hammer Builder icons.
- Tighten dropdown widths and place recovery Minutes/Qty beside its mode selector. Preserve the Color palette width.
- Clean up BBE branding and sharp native creator credits. Fresh workspaces start with only BBE expanded; saved workspace panel states remain respected.

### Install
Download **no_mans_sky_base_builder-18.1.78.zip** below. In Blender, use **Install from Disk**, select the intact ZIP, then restart Blender. Keep the previous installer for rollback. The GitHub source archives are not the installer.

Windows x64. Recovery timer regression checks passed in Blender **5.1.2** and **5.2.2 LTS**, including real save-copy callbacks, three-generation rotation, source-file preservation, failure/retry behavior and placement triggers. The countdown and automatic backup were also checked in the Blender UI. The reported 676-part TXT design imported completely in both versions.

Includes all changes since 18.1.63; automatic update checks remain opt-in. Base Builder by DjMonkey. Extended by FuriousFurby.

release 18.1.63
-------------

- Ask once whether to enable automatic update checks. Yes enables and saves Blender Online Access and the startup-update setting, then checks for updates.
- No or dismissal keeps automatic checks off and remembers the choice across restarts and upgrades. An existing disabled setting is respected.
- The prompt explains that Blender's global internet access also applies to other add-ons. Forced offline mode stays offline; background sessions do not prompt or start automatic checks.
- Updates & Support can enable checks later using the same Yes/No prompt. Installation of downloaded updates remains user-controlled.
- Includes the complete Colour & Materials sidebar restored in 18.1.62.

Verified Yes/No operators, preference persistence across restart, legacy settings,
failed preference saving, and forced offline mode in Blender 5.1.2 and 5.2.2 LTS.
The first-run prompt was visually inspected in Blender 5.1.2.

release 18.1.62
-------------

Restore the complete Colour & Materials section in the Base Builder sidebar,
including the palette selector, swatches, and colour picker. The top-toolbar
Color menu remains available. All 18.1.61 runtime files and assets are retained
except the restored panel registration, version number, and release instructions.

Install no_mans_sky_base_builder-18.1.62.zip using Blender's Install from Disk,
then restart Blender. Windows x64; Blender 5.1.2 and 5.2.2 LTS validation covered
panel registration, all 18 palettes, and the existing bulk-colouring checks.
The ZIP passed archive integrity and comparison with the published 18.1.61 installer.

release 18.0.9-station-reference
-------------

## Fixed

- Selecting multiple repeated parts now colours every selected piece visibly.
- The colour picker updates every selected copy's viewport colour and labels.
- Mixed HD/proxy selections preserve their geometry and textures, while
  unselected parts keep their existing colour.
- Colour edits preserve part identity, transforms and reserved UserData bits.
- Extension startup safely handles Blender's temporarily restricted context.

Includes the previously local shared-builder/material/part-handler integration
hooks, with the built-in implementation used by default. No companion add-on,
separate model download, NMSDK, external Python or pip command is required.

Retains the reactor and girder mirroring fixes, Duplicate Along Curve behaviour,
fossil import fixes, corrected cuboid models and station-reference tools from
18.0.8.

## Installation

1. Download **no_mans_sky_base_builder-18.0.9-station-reference.zip** from Assets.
2. Save your Blender work.
3. Open **Edit > Preferences > Get Extensions > Install from Disk** and select
   the intact ZIP.
4. Enable **No Man's Sky Base Builder**, then restart Blender.

Windows x64; tested with Blender **5.1.2** and **5.2.2 LTS**. Use the attached
plugin ZIP for installation. GitHub's Source code archives are for developers.
Keep the previous installer if you need to roll back. Previously misidentified
parts are not repaired automatically by upgrading.

## Verification

The final ZIP was extracted into a clean folder and tested for bulk colouring,
colour picking, mixed HD/proxy parts, exported colour data, duplication, curve
following, all 266 mirror pairs in both directions, fossil imports, corrected
cuboid parts, textured Corvette weapons, aligned hab/bay details, both browser icons, UI/assets, station imports and private-copy save round-trips.
Archive CRCs and every extracted file hash were checked. No live game save was
modified, and no new in-game test is claimed. SHA256SUMS.txt is attached.


release 6.5.2
-------------

* Fixed an issue where the Asset Browser would not load on Linux.


release 6.5.1
-------------

* Fixed incorrect scale of Swarm Trophy parts.


release 6.5.0
-------------


* A UI polish pass across the panels of the tool, improving visual consistency across different tools. (credit: Kuma the Wizard, with additional feedback/tweaks from DjMonkey)
* Panels that contain particular tools are now collapsed by default, to help with initial overwhelm when loading for the first time. (credit: DjMonkey)
* New workspace buttons that simplify the Blender UI and quicker access to the Asset Browser UI. (credit: Kuma the Wizard & DjMonkey)
* Expanded Mirror Options: Specify different axis options and auto-duplication settings with these new options (credit: Kuma the Wizard)
* Expanded Curve Options: Selecting the "Duplicate Along Curve" button now provides an expanded property box with dynamic options like number of parts and part scale. Selecting and deselecting the curve will toggle these tools. (credit: Kuma the Wizard)
* Batch Tools: Various options for selecting and swapping multiple objects all at once. (credit: Kuma the Wizard)
* Added a colour picker button that lets you drop material and colour options quicker between parts from another part. (credit: Kuma the Wizard)
* Bugfixes and visual updates to the Save Manager tools. (credit: Kuma the Wizard)
* Added a top section for logos, guides, and support (credit: Kuma the Wizard & DjMonkey)
* Added Prismatic Core Trophy models to the catalogue. (credit: DjMonkey)
* Consolidated the terminology and file format for Presets => Prefabs. From this update onward both Blender and App will produce `.nmsprefab` files compatible with both tools. Blender can still read `.json` preset files for backward compatibility. (credit: DjMonkey)
* Prefabs now appear in a left-most tab within the Asset Browser UI. (credit: DjMonkey)



release 6.4.1
-------------

* Added parts for 6.4.0 - Swarm update.
* Added a built-in Save Editor panel to import/export bases and corvettes to a save directly from the Blender extension itself. A big thanks to Kuma the Wizard who spent a few weeks building this feature out and the patience listening to feedback from myself and other community builders.
* Fixed an error pop up when using the Duplicate Part button.


release 6.3.0
-------------

* Improvements and optimizations to the mirror, mirror across X, and flip functions (Thanks to Kuma the Wizard).
* Model fixes to B_DECO_Q_1,B_STR_AA_N,B_STR_AA_S, S_SAIL, TOYCORE, PANEL_GLASS, S_ROOF objects and added settlement class objects (Thanks to Kuma the Wizard).
* Added more logic checks to the PySide start up to prevent start up errors for some users with the Asset Browser.
* Fixed an issue where Blender would become unresponsive after loading the Asset Browser.
* Added parts from 6.3.0 update including GAMETABLE and Quicksilver rewards.
* Removed extraneous print statements.


release 6.2.0
-------------

* Added the option to tag base parts as a "Favourite" which adds them to a dedicated tab in the Asset Browser.
* Added the option to pin category tabs which places them in their own pinned section to the left of the tab bar.
* Base Building App prefabs (.nmsprefab) can now be listed and loaded natively using the Preset/Prefab mechanism.
* Fixed visibility of the Vesper Rim part in the asset browser.


release 6.1.7
-------------

* Added Freighter colour options to the Colour and Materials tool.
* Editing colours/materials should no longer reset additional UserData information like logic switches, states, etc.


release 6.1.6
-------------

* Revamped the colour options to allow users to use colours from a variety of material palettes.
* Added a button only export the objects of the base to the user clipboard.
* Re-processed meshes for STORAGEPANEL and BUILDFLATPANEL.
* Fixed an issue where the Asset Browser would not load on Linux.
* Fixed an issue where the Asset Browser tabs would be squashed and not be scrollable on Mac.
* Fixed a mesh placement issue with the B_STR_U corvette pieces.


release 6.1.5
-------------

* Fixed an issue when adding parts from the Asset Browser was not taking into consideration the current selection.
* Fixed an issue where miniimze and maximize buttons disappared from the Asset Browser window.
* Fixed an issue where the Wonder Projector was not retaining it's message data.


release 6.1.4
-------------

* It is no longer required to installed bpy_external for the Asset Browser to work.
* Visual refresh to the Asset Browser which improves readability and consistency with the Base App.
* Added connection point data to the Corvette Mini Teleporter.


release 6.1.3
-------------

* It is no longer required to install Python in order to use the Asset Browser tool
    * The tool now uses the Python installation that is part of Blender itself.
    * Using the Asset Browser should now be a lot more stable to use for users setting things up for the first time.
    * Existing users can remove their Python installation if they were only using it for this tool.
    * There is still a small wait on the first-time load as things initialize.
* Added a Guides button to the tool.


release 6.1.2
-------------

* Ported add-on structure to newer Blender extension structure.
* Removed YAML as a Python dependency as it’s no longer used.
* Fixed an issue where the corvette “_Y_NE” parts were not being listed in their respective variants panel in the Asset Browser.
* Collapsed L/R corvette connector pieces into one item with the variants sub-window in the part drawer.
* Fixed naming of variants for the Atlas Corvette parts.
* Fixed visibility of NW parts for the Hardrame Diffuser Rim
* Fixed visibility of Speedbird Dome Rime in the Asset Browser
* Fixed an issue where the Asset Browser could not load on systems of certain language settings.


release 6.1.1
-------------

* Improved the search responsiveness on the Asset Browser.
* Part variant’s have been removed from the Asset Browser and are now accessed from a sub-menu from the “parent” part in the Asset Browser.
* Added the “Mirror Across X Axis” tool.


release 6.1.0
-------------

* Added parts from 6.1 BREACH update.


release 6.0.0
-------------

* Added parts for Corvette pieces
* Added parts for Fossil pieces
* Added other missing parts from recent updates.
* Added a mirror and flip button which can be used on certain corvette pieces.
* Improved support for message fields.
* UserData value is now retained during import and export, which should make Corvette workflows nicer.


release 2.1.4
-------------

* Added parts from Worlds Part II (Ruins, exotic plants, etc)


release 2.1.3
-------------

* Added support for base parts added up to Worlds Part 1 Update.
* Adjusted hallway and walkway freighter models.
* Added some Linux compatibility thanks to dsalt on GitHub.
* Updated output JSON format to match latest version found in the game.


release 2.1.2
-------------

* Fixed model issues on FRE_FACE_WINDOW, BLD_HOLOGEK, CREATHOLOGRAM, S_GAZEBO0.
* Replaced GEK statue's with their actual representation, rather than Blobs.
* Added cable connection point to U_SILO_S, U_EXTRACTOR_S, and U_GASEXTRACTOR
* Added a UI control to the cable window to toggle between the different cable types. (Power, ByeBeat, Portal, Pipe)
* Renamed the tab to "No Man's Sky Base Builder"


release 2.1.1
-------------

* Fixed model issues on BLD_BUI_HAND, BLD_CRANE, and MAPTABLE.
* Fixed error when using the snapping buttons on power controllers.
* Fixed snapping data for large structures/prefabs.
* Fixed an issue where connecting power controllers would make extraneous wires and controllers.
* Added power connections to the base teleporters.


release 2.1.0
-------------

* Fixed errors when using Blender 4.0
* Base parts up to date as of ORBITAL update.


release 2.0.5
-------------

* Fixed a bug where some scaled parts were being assigned a random color.


release 2.0.4
-------------

* Added model support for Timber, Alloy and Stone variant pieces.


release 2.0.3
-------------

* Added some automation scripts for updating this tool.
* Added a bunch of missing objects since the last year (Expeditions/Sentinel/Outlaws/Endurance/Waypoint).
* Thanks to Peter Laan for assistance with missing parts and their source file locations.


release 2.0.2
-------------

* Simplified Qt Dependencies. (Swapped to PySide6)
* Compatible with latest Python 3.10 and Blender 3.0 versions.


release 2.0.1
-------------

* Fixed an issue where loading a base using presets would error.
* Small fixes to asset naming and categorization in the Asset Browser.


release 2.0.0
-------------

* Added over 250 new parts to support the FRONTIERs update.
* Fixed issues with cable placement logic introduced with FRONTIERS.
* Added a new Asset Browser UI for better browsing on building parts. (See readme and video tutorials for more information.)
* Added category support for Presets. The tool will now recognise sub-folders within the user Preset folder.
* Added a button to apply the default colour to a base part.
* A fancy new logo.


release 1.3.3
-------------

Thanks to Wormhole Badger (@MarkAlanSwann1) for supplying the proxy models for
this update.

* Added a Fireworks category with firework items.
* Added support for the following items.
    * Unlockables
        * BASE_HOUDINI1
        * BASE_HOUDINI2
        * BASE_HOUDINI3
        * BASE_INFEST1
        * BASE_INFEST2
        * BASE_INFEST3
        * BASE_LAVA1
        * BASE_LAVA2
        * BASE_LAVA3
        * BASE_SWAMP1
        * BASE_SWAMP2
        * BASE_SWAMP3
        * BASE_TOYJELLY
        * SLIME_MED
        * SPOOKY_PLANT
        * SPEC_FIREWORK01
        * SPEC_FIREWORK02
        * SPEC_FIREWORK03
        * SPEC_FIREWORK04
        * SPEC_FIREWORK05
        * SPEC_FIREWORK06


release 1.3.2
-------------

* Added the Derelict Freighter Turret as a buildable item.
* Added some window and door items to the visibility ghost list.
* Changed blender ops naming from "nms." to "object.nms_".
* Added more snapping positions so walls can be snapped below floors.
* Complete rework of triangle pieces.
    * Triangles are now the correct size.
    * 3D model updated to better represent part, with indication of the direction of the triangle.
    * Fixed snapping points on triangle pieces.
* Renamed Parts...
    * BASE_HOTPLANT1 > * BASE_HOTPLANT01
    * BASE_HOTPLANT2 > * BASE_HOTPLANT02
    * BASE_HOTPLANT3 > * BASE_HOTPLANT03
* Added support for the following models ...
    * Freighter
        * TURRET_ABAND - Freighter Turret
* Fixed a power connection position on the Light Floor (credit: @bjj)
* "Connect" can now operate on multiple selections. (credit: @bjj)
* Added a "Select Connected" button to the Power Tooling (credit: @bjj)
* Added a "Select Floating" button to the Power Tooling (credit: @bjj)
* Fixed a power line division bug (credit: @bjj)
* Material clears when importing OBJs. (credit: @bjj)
* Power Controllers now created at the 3D cursor position. (credit: @bjj)


release 1.3.1
-------------

* Added `bl_options = {"UNDO", "REGISTER"}` everywhere required.
* Changed material colour of U_PORTALLINE.
* Added .gitignore file.


release 1.3.0
-------------

* Fixed some Blender error messages when interacting with non-NMS scene items.
* Missing/Modded parts will be named their ID instead of "cube".
* New models for C_ROOF, M_ROOF
* Added support for the following models ...
    * Freighter
        * ABAND_BARREL - Industrial Barrel
        * ABAND_BENCH - Industrial Bench
        * ABAND_CASE - Secure Briefcase
        * ABAND_CRATE_L - Storage Unit
        * ABAND_CRATE_M - Salvage Crate
        * ABAND_CRATE_XL - Large Storage
        * ABAND_SHELF - Heavy-Duty Furniture
        * FOORLIGHT - Emergency Light
        * FOOTLOCKER - Crew Footlocker
        * HEATER - Emergency Heater
        * LOCKER2 - Crew Locker
        * MEDTUBE - Sample Container
        * PALLET - Industrial Pallet
        * PLANTTUBE - Floral Cannister


release 1.2.1
-------------

* Fixed naming of BUILDCHAIR.
* Fixed a model positioning issue with NPCFRIGTERM.
* Added snapping positions for Plants, Platers and Bioroom.
* Adjusted scaling for gold, silver and bronze statues.
* Added support for the following models ...(with help from @DevilinPixy)
    * Main
        * PANEL_GLASS
    * Decoration
        * STATUE_DIP_B
        * STATUE_DIP_S
        * STATUE_DIP_G
    * Exocraft
        * GARAGE_MECH
    * Technology
        * POWERLINE_HIDER
        * BUILDHARVESTER
    * Farming
        * TOXICPLANT
        * SNOWPLANT
        * SCORCHEDPLANT
        * SACVENOMPLANT
        * RADIOPLANT
        * POOPPLANT
        * PEARLPLANT
        * NIPPLANT
        * GRAVPLANT
        * LUSHPLANT
        * BARRENPLANT
        * CREATUREPLANT
    * Freighter
        * GARAGE_FREIGHT
        * S_CONTAINER0
        * S_CONTAINER1
        * S_CONTAINER2
        * S_CONTAINER3
        * S_CONTAINER4
        * S_CONTAINER5
        * S_CONTAINER6
        * S_CONTAINER7
        * S_CONTAINER8
        * S_CONTAINER9
    * Unlockables
        * BASE_BEAMSTONE
        * BASE_BUBBLECLUS
        * BASE_COLDPLANT1
        * BASE_COLDPLANT2
        * BASE_COLDPLANT3
        * BASE_CONTOURPOD
        * BASE_DUSTPLANT1
        * BASE_DUSTPLANT2
        * BASE_DUSTPLANT3
        * BASE_ENGINEORB
        * BASE_HOTPLANT1
        * BASE_HOTPLANT2
        * BASE_HOTPLANT3
        * BASE_HYDROPOD
        * BASE_MEDGEOMETR
        * BASE_MEDPLANT01
        * BASE_MEDPLANT02
        * BASE_MEDPLANT03
        * BASE_RADPLANT01
        * BASE_RADPLANT02
        * BASE_RADPLANT03
        * BASE_ROBOTOY
        * BASE_ROCK01
        * BASE_ROCK02
        * BASE_ROCK03
        * BASE_SHARD
        * BASE_SHELLWHITE
        * BASE_STARJOINT
        * BASE_TOXPLANT01
        * BASE_TOXPLANT02
        * BASE_TOXPLANT03
        * BASE_WEIRDCUBE
        * BASE_WPLANT1
        * BASE_WPLANT2

release 1.2.0
-------------

* Added support for the decal items.
* Added models for...
    * BUILDDECAL
    * BUILDDECAL2
    * BUILDDECALNMS
    * BUILDDECALNUM0
    * BUILDDECALNUM1
    * BUILDDECALNUM2
    * BUILDDECALNUM3
    * BUILDDECALNUM4
    * BUILDDECALNUM5
    * BUILDDECALNUM6
    * BUILDDECALNUM7
    * BUILDDECALNUM8
    * BUILDDECALNUM9
    * BUILDDECALSIMP1
    * BUILDDECALSIMP2
    * BUILDDECALSIMP3
    * BUILDDECALSIMP4
    * BUILDDECALVIS1
    * BUILDDECALVIS2
    * BUILDDECALVIS3
    * BUILDDECALVIS4
    * BUILDDECALVIS5
    * SPEC_DECAL01
    * SPEC_DECAL02
    * SPEC_DECAL03
    * SPEC_DECAL04
    * SPEC_DECAL05
    * SPEC_DECAL06
    * SPEC_DECAL07
    * SPEC_DECAL08

release 1.1.9
-------------

* Updated Add-on information for Blender 2.82
* Added missing Half Metal Arch object.
* Added missing power connection to Garage Wall items.
* Added missing power connections to Light Posts.
* Added missing power connection to Byte Beat Switch.
* Enabled message capturing on Byte Beat Switch.
* Added some snapping information to the short wall pieces.
* Improved models for...
    * BUILDLIGHT
    * BUILDLIGHT2
    * BUILDLIGHT3
    * BYTEBEATSWITCH
    * C_GDOOR
    * M_GDOOR
    * W_GDOOR
    * C_WALL_Q
    * C_WALL_Q_H
    * M_WALL_Q
    * M_WALL_Q_H
    * W_WALL_Q
    * W_WALL_Q_H

release 1.1.8
-------------

* Arranged the Tools panel into a neater and more compact layout.
* Missing object cube placeholder's are now named after the object ID in the scene.
* Added OBJ add-on as a plugin dependency.


release 1.1.7
-------------

* Added a specific "Delete" button in the tools area that safely removed Base Parts and Presets from the scene.
* BYTEBEAT machines and their configurations are now supported.
    * BYTEBEAT machines and their songs can now be saved as presets and shared with other people.
    * Example: https://djmonkeyuk.github.io/nms-base-builder-presets/Byte%20Beats
* Optimized the creation of wiring controls. Bases with lots of wiring should now load faster.
* Added models for...
    * BYTEBEAT
    * BYTEBEATSWITCH
    * L_FLOOR_Q
    * U_BYTEBEATLINE

release 1.1.6
-------------

* Fixed a rotation accuracy bug when generating presets.
* Preset files now have a time stamp applied to them to help with date sorting in the Preset Directory.
* Improved timestamp data on individual base objects.


release 1.1.5
-------------

* Added support for triangle pieces.

release 1.1.4
-------------

* Support for Blender 2.81.
* Added support for Freighter bases.
    * Added simple model parts for Freighter pieces.
    * Restricted movement of FREIGHTER_CORE, AIRLCKCONNECTOR and BRIDGECONNECTOR.
    * Freighter BaseType key detected on import and kept at export. Planet base key used as default.
    * Added snapping support for Freighter parts.
* Improved snapping information for cube parts.
* Improved snapping information for light/noise boxes.
* Updated import/export functions with new keys and values from NMS version 2.16.
* Added a "Open Preset Folder" button that opens explorer window for quick access to preset .json files.


release 1.1.3
-------------

* Added a "Get More Presets..." button that opens the directory web-page for community made presets.

release 1.1.2
-------------

* Added a 'Build Counter' to the Base Properties panel to show the total number of NMS objects in your scene.
* Fixed communication message modules forgetting messages.
* Fixed the 'X' delete preset button in the preset list.
* Apply radian rotation values when snapping objects for better accuracy.
    (which fixes some cases where small offsets were being applied to snap positions)
* Fixed an issue where objects weren't remembering their snapped partner object when they don't have matching snap points.
* Added socket model and power connection to CONTAINER objects.
* Added CONTAINER7.
* Added Infrastructure Ladder.
* Added Oscilloscope.


release 1.1.1
-------------

* Fixed preset folder creation for new users.


release 1.1.0
-------------

* General
    * Further improvements to Blender 2.8 support.
    * Vastly improved loading times for base and preset generation.
    * Added more custom warnings and error messages so the user encounters less Python trace-back errors.
    * Removed the default Blender Cube, Light and Camera when generating bases.
    * Ensured all items fit under the default "Collection" in the Outliner.
    * Fixed the transparent shader being applied to all items instead of just structural items as intended.
    * Turned off relationship lines by default.
    * Part and Preset list search bar to always be visible.
    * Base parts are now listed alphabetically in the UI list.
* Presets
    * A better control is generated, calculated from the total floor-area of the preset parts.
    * Fixed an issue where presets were not generating properly if more than one instance existed.
* Snapping
    * Snapping an object remembers which object it has previously snapped to.
    * Allows you to use the snap buttons without having to select two items at a time after the initial snap has been done.
    * Updated snap information for BUILDLANDINGPAD.
    * Swapped the selection order when snapping one object to another.
* Power
    * When selecting a point then pressing "New Point". This will automatically create a power line between the new point and the previous point.
    * Added power sockets to farm planter and mega planter.
* Models improvements for...
    * BUILDLANDINGPAD
    * GARAGE_M
    * GARAGE_SUB
    * PLANTER
    * PLANTERMEGA
* Added models for...
    * GARAGE_L
    * GARAGE_S
    * SUMMON_GARAGE
    * RACE_RAMP
    * BASE_TOYCORE
    * BASE_TOYCUBE
    * BASE_TOYSPHERE
    * U_SILO_S
    * CUBEROOF
    * BUILDGASHARVEST
    * STATUE_GEK_B
    * STATUE_GEK_S
    * STATUE_GEK_G
    * STATUE_SHIP_B
    * STATUE_SHIP_S
    * STATUE_SHIP_G
* Code refactor.
    * Restructured object and class hierarchy to something more manageable.
    * Replaced most bpy.ops methods with bpy.data methods.
    * Enhanced the caching mechanism for base part and preset retrieval.
    * Added framework to easily allow custom behavior for specific parts.
    * Categorized utility methods into their own modules.


release 1.0.0
-------------

* Updated code-base to work for Blender 2.8.
* Internal base version updated to 4. Additional save data keys added to export.
* Unlocked scale channels on all base parts as scaling is now supported. Works for ALL base parts.
    * (Use at your own risk, in-game snapping behavior becomes unreliable for base parts not intending to be scaled.)
* Added power socket details to some base part models that require electricity.
* Added a set of features for managing power and electricity.
    * Connect electrical base parts together from the new power UI panel.
    * Snap and cycle wire ends to base part connection points.
    * Divide existing wires into two, creating an additional control.
    * Split existing wires into two, creating a gap with 2 additional controls.
    * Create arbitrary control points to create more complex wire paths.
    * Quickly create logic gates and switches in the logic UI area.
* Fixed a minor matrix offset on wall snap points.
* MAINROOMCUBE and BUILDLANDINGPAD model improvements.
* Fixed and adjusted "nice name" table.
* Added models for...
    * W_GDOOR
    * M_GDOOR
    * C_GDOOR
    * W_ROOF_IC
    * M_ROOF_IC
    * C_ROOF_IC
    * U_BATTERY_S
    * U_EXTRACTOR_S
    * U_GASEXTRACTOR
    * U_GENERATOR_S
    * U_MINIPORTAL
    * CREATURE_FEED
    * CREATURE_FARM
    * COOKER
    * BUILDANTIMATTER
    * U_BIOGENERATOR
    * BUILDTABLE3
    * NOISEBOX
    * LIGHTBOX
    * U_POWERLINE
    * U_PORTALLINE
    * U_PIPELINE


release 0.9.3
-------------
* Refactored module and code structure.
* Faster loading times for bases and presets with OBJ reference cache mechanism (only imports OBJs for first load).
* Improved models for mainrooms.
* Added support for a vast amount of decoration and technology parts: WATERBUBBLE, SHIELDSTATION, HEALTHSTATION, O2_HARVESTER, DRESSING_TABLE, BUILDTERMINAL, FOUNDATION, CRATELRARE, CRATELCYLINDER, MAINROOMFRAME, SMALLLIGHT, BUILDLABLAMP, GARAGE_B, CUBEWINDOWSMALL, CUBEWINDOWOVAL, WALLSCREEN, WALLSCREENB, WALLSCREENB2, WALLFLAG1, WALLFLAG2, WALLFLAG3, WALLFAN, TECHPANEL, STORAGEPANEL, STATUE_WALK_?, STATUE_ASTRO_?, SERVERSTACK, OCTACABINET, FLOORMAT1, DRAWS, BUILDSIDEPANEL, BUILDLIGHTTABLE, BUILDHCABINET, BUILDFLATPLANEL, BUILDCANRACK, BUILDBED, BLDWALLUNIT, BASE_WPLANT3, BASE_TREE03, BASE_MEDPLANT01, BASE_MEDPLANT02, BASE_MEDPLANT03, BASE_BONEGARDEN, BASE_BARNACLE, ?_DOOR_H, ?_DOORWINDOW, ?_DOOR, ?_ARCH_H, ?_ROOF_M, ?_ROOF_C, BASE_TERRARIUM, BASE_AQUARIUM, NPCWEAPONTERM, NPCBUILDERTERM


release 0.9.2
-------------
* Added some legacy base building parts.
* New OBJs for Standing Planter, Walls, Floors, Folding Door, Corner Post.


release 0.9.1
-------------
* Added under water parts to the list.
* Added and improved snap point information and relationships.
* Improved appearance of L shape hallway pieces.
* Implemented first phase of mod support. (see readme for more details.)
* Light objects now create blender lights.
* Improved room visibility switch to display current mode.
* Added "Lighted" as an option on room visibility.


release 0.9.0
-------------
* Added colour options.
* Improved overall UI. Changed to collapsible areas and added button icons.
* Changes to snapping information.
* Added nice name mechanism to base parts.

release 0.8.0
-------------
* Improved and added various models.
* New Snapping area in the tool. With convenient Duplicate button. (Expect some items would not snap yet!)
* Items with compatible snapping will automatically snap on creation.
* Fixed a bug where the tool would disappear when no item was selected.
* Re-organised Basic parts into more granular categories (floors, stairs, walls, etc)


release 0.7.2
-------------
* Improved obj's of CUBEFLOOR, C_WALL_Q_H, BUILDPAVING and BUILDPAVING_BIG.
* Added obj for BUILDSODA2L and CUBESTAIRS.


release 0.7.0
-------------
* Added options for defining and building presets.
* Added large paving, pipe and curved pipe.


release 0.6.0
-------------
* Added a button to toggle between different room visibility. Shown, Ghost and Hidden.
* Added display support for...
    Chairs
    Locker
    Sofas
    Worktop
    Ceiling light
    Cube Inner Doors
    Cube Walls
    Large Desk
    Robotic Arm
    Shelf Panel
    Roof Monitor
    Weapon Rack
    Plant Pot
    Ladder
    Main room Window


release 0.5.0
-------------
* Initial release
For habs or the Thunderbird bay already placed in an older saved scene, select
those parts and switch to Low-Res, then back to High-Res to refresh their meshes.
