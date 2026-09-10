from copy import copy

from .. import part


class BONE(part.Part):
    """Capture extra "Message" attribute."""

    def __init__(self, *args, **kwargs):
        super(BONE, self).__init__(*args, **kwargs)
        if "Message" not in self.object:
            self.object["Message"] = ""

        self.shuffle_ids()

    @property
    def message(self):
        return self.object.get("Message", "")

    @message.setter
    def message(self, value):
        self.object["Message"] = str(value)

    def serialise(self):
        data = super(BONE, self).serialise()
        data["Message"] = self.message
        return data

    @classmethod
    def deserialise_from_data(cls, data, *args, **kwargs):
        part = super(BONE, cls).deserialise_from_data(data, *args, **kwargs)
        part.message = data.get("Message", "")
        return part

    def retrieve_object_from_id(self, object_id):
        """Build the bone out of the high res library when it has one.

        A bone is the one part that never arrives under its own id - the save
        holds a FOS_SKULL/FOS_BODY placeholder carrying the real bone id in its
        Message, and BONE_REPLACER swaps it for one of these. So this is the
        only place the actual fossil mesh gets created, and it has to ask for
        the high res asset itself; add_part never sees the bone id.

        All 143 bone models are in the library, so the fbx proxy below is only
        the fallback for a library that hasn't been built yet.
        """
        # imported here rather than at the top: builder_v2 pulls in the override
        # table, which pulls in this module
        from .. import builder_v2

        bpy_object = builder_v2.new_high_res_object(object_id)
        if bpy_object is not None:
            return bpy_object

        return super(BONE, self).retrieve_object_from_id(object_id)

    def shuffle_ids(self):
        """Move the object ID into the Message field, and then strip the suffix from the ID itself"""
        self.message = copy(self.object_id)
        stripped = "_".join(copy(self.object_id).split("_")[:-1])
        if "FOS_HEAD" in stripped:
            stripped = stripped.replace("FOS_HEAD", "FOS_SKULL")
        if "FOS_BI_TAIL" in stripped:
            stripped = stripped.replace("FOS_BI_TAIL", "FOS_TAIL")
        if "FOS_BI_BODY" in stripped:
            stripped = stripped.replace("FOS_BI_BODY", "FOS_BODY")
        self.object_id = stripped
        self.snap_id = stripped
