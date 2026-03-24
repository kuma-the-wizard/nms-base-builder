"""
Bitfield helper for safely reading/writing colour and material indices
while preserving all other unknown data.

Design philosophy:
- Only operate on known bit regions (colour + material)
- Treat all other bits as opaque payload
- Never decode or modify unknown fields
"""

# Colour occupies lower 24 bits (but some bits may be reserved)
COLOUR_BITS_FULL = 0xFFFFFF

# Known reserved bits inside the colour range (DO NOT TOUCH)
# These are protected but not interpreted
RESERVED_BITS = (
    (1 << 8)  # e.g. resource flags (biogen, etc.)
    | (1 << 16)  # e.g. state
    | (1 << 17)  # e.g. type
)

# Safe colour mask (excludes reserved bits)
COLOUR_MASK = COLOUR_BITS_FULL & ~RESERVED_BITS


# Material occupies bits 24–31
MATERIAL_SHIFT = 24
MATERIAL_MASK = 0xFF << MATERIAL_SHIFT


def _extract_bits(value: int, mask: int, shift: int = 0) -> int:
    """Extract masked bits and shift down."""
    return (value & mask) >> shift


def _set_bits(value: int, new_bits: int, mask: int, shift: int = 0) -> int:
    """
    Replace masked bits while preserving everything else.
    """
    value &= ~mask
    value |= (new_bits << shift) & mask
    return value


# Colour API ---
def get_colour(value: int) -> int:
    """
    Get colour index from packed value.
    """
    return value & COLOUR_MASK


def set_colour(value: int, colour_index: int) -> int:
    """
    Set colour index safely.

    - Does NOT overwrite reserved bits
    - Preserves all unknown data
    """
    value &= ~COLOUR_MASK
    value |= colour_index & COLOUR_MASK
    return value


# Material API ---
def get_material(value: int) -> int:
    """
    Get material index from packed value.
    """
    return _extract_bits(value, MATERIAL_MASK, MATERIAL_SHIFT)


def set_material(value: int, material_index: int) -> int:
    """
    Set material index safely.

    - Preserves all other bits
    """
    return _set_bits(value, material_index, MATERIAL_MASK, MATERIAL_SHIFT)


# Combined Convenience API ---
def update_colour_material(
    base_value: int,
    *,
    colour_index: int | None = None,
    material_index: int | None = None,
) -> int:
    """
    Update colour and/or material while preserving all other data.

    Parameters
    ----------
    base_value : int
        Original packed value

    colour_index : int | None
        New colour index (None = unchanged)

    material_index : int | None
        New material index (None = unchanged)
    """
    value = base_value

    if colour_index is not None:
        value = set_colour(value, colour_index)

    if material_index is not None:
        value = set_material(value, material_index)

    return value
