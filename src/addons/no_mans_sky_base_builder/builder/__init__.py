from .builder import Builder

# one builder shared by the whole addon, so every tool sees the same part cache
BUILDER = Builder()
