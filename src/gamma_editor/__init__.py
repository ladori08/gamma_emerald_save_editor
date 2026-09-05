"""Gamma Emerald save editor package."""

from .codec import GES1Container, decode_ges1, encode_ges1

__all__ = ["GES1Container", "decode_ges1", "encode_ges1"]
__version__ = "0.15.1"
