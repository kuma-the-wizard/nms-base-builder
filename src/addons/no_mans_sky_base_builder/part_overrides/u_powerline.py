from ..part_overrides import line


class U_POWERLINE(line.Line):
    def __init__(self, *args, **kwargs):
        super(U_POWERLINE, self).__init__(*args, **kwargs)
