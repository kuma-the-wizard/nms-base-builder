from copy import copy

import no_mans_sky_base_builder.part as part
import no_mans_sky_base_builder.utils.blend_utils as blend_utils


class BONE_REPLACER(part.Part):
    """Capture extra "Message" attribute."""

    def __init__(self, *args, **kwargs):
        super(BONE_REPLACER, self).__init__(*args, **kwargs)
        if "Message" not in self.object:
            self.object["Message"] = ""

    @property
    def message(self):
        return self.object.get("Message", "")

    @message.setter
    def message(self, value):
        self.object["Message"] = str(value)

    def serialise(self):
        data = super(BONE_REPLACER, self).serialise()
        data["Message"] = self.message
        return data

    @classmethod
    def deserialise_from_data(cls, data, *args, **kwargs):
        part = super(BONE_REPLACER, cls).deserialise_from_data(data, *args, **kwargs)
        part.message = data.get("Message", "")
        if part.message:
            part.swap_object()
        return part

    def swap_object(self):
        matrix = copy(self.object.matrix_world)
        bone_id = self.message
        blend_utils.delete(self.object)
        print("SWAPPING WITH", bone_id)
        bone_part = self.builder.add_part(bone_id)
        bone_part.object.matrix_world = matrix
