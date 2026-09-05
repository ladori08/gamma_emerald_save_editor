class GammaEditorError(Exception):
    """Base error for user-facing save editor failures."""


class ContainerError(GammaEditorError):
    """The GES1 wrapper is malformed or failed integrity validation."""


class GvasError(GammaEditorError):
    """The inner Unreal GVAS payload is malformed or unsupported."""


class SafetyError(GammaEditorError):
    """A save operation was refused because a safety invariant failed."""

