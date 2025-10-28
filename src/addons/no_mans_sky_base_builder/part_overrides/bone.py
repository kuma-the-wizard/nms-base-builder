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
