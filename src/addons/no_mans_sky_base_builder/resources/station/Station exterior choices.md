# Choosing the station's large exterior parts

The library contains alternative station configurations. Turning every eye on overlays those alternatives. Start with one hull family and one Body, then enable the large components that match your station.

All 80 exterior reference objects were checked against the extracted game's scene hierarchy for their own hull family and procedural branch. Their positions match; Tet and Oct's low arch rings are authored that way. The 6.5.5 update corrects misleading names and preserves geometry and eye settings.

| Hull | Compatible choices |
| --- | --- |
| **Tet** | Choose one **Upper** component and one **Lower** component. The Lower object supplies the paired mounts. The **Arch ring** is independently optional. |
| **Oct** | Choose one **Single** component and one **Paired** component. The Single mount is below the hull; the pair runs diagonally along its sides. The **Arch ring** is independently optional. These used to be misleadingly named Upper and Lower. |
| **Disk** | Choose **Vertical ring layout**, or the layout with one **Upper** component and optionally **Arch ring** or **Partial arch ring**. Hide the vertical ring when using that Upper/arch layout. Choose one **Lower** component independently. Feet, Clasps and Clasptri are alternatives. |
| **EX** | Choose one **All ...** set, or a mixed combination of one **Upper** and one **Lower** component. Hide the All sets when using Upper/Lower. Feet and Clasps are alternatives. |
| **Tri** | Choose one **All ...** set, or a mixed combination of one **Upper** and one **Lower** component. Hide the All sets when using Upper/Lower. Feet, Clasps and Ctri are alternatives. |
| **Simple** | Choose one **Upper** component. Keep its **Upper mounting plate** visible when displaying the component. |

You can hide any reference component while designing. Eye icons remain independent; these rules describe compatible native configurations, not enforced Blender controls. A configuration compatible with the scene data is an example, not a reconstruction of your current system's seed.

The audit compares all delivered exterior vertices and triangles with their source instances, including the full parent transforms and option ancestry. The maximum coordinate difference is 0.000494 game units from floating-point rounding. This verifies the extracted scene alignment; it does not establish runtime flight or build restrictions.
