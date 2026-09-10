"""Save support comes from the wheel bundled with this extension."""

def installDependencies():
    # Keep the Save Manager entry point, without first-use pip downloads.
    try:
        import lz4.block
    except ImportError as exc:
        raise RuntimeError(
            'The bundled save library is unavailable. Install the complete Station Import ZIP '
            'through Preferences > Get Extensions > Install from Disk, then restart Blender.'
        ) from exc
    return True
