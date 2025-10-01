import no_mans_sky_base_builder.part as part


class MESSAGE(part.Part):
    """Capture extra "Message" attribute."""

    def __init__(self, *args, **kwargs):
        super(MESSAGE, self).__init__(*args, **kwargs)
        if "Message" not in self.object:
            self.object["Message"] = ""

    @property
    def message(self):
        return self.object.get("Message", "")

    @message.setter
    def message(self, value):
        self.object["Message"] = str(value)

    def serialise(self):
        data = super(MESSAGE, self).serialise()
        data["Message"] = self.message
        return data

    @classmethod
    def deserialise_from_data(cls, data, *args, **kwargs):
        part = super(MESSAGE, cls).deserialise_from_data(data, *args, **kwargs)
        part.message = data.get("Message", "")
        return part
