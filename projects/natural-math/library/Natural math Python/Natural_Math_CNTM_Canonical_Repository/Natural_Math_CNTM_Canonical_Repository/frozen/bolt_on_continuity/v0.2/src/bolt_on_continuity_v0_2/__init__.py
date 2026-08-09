"""Bolt-On Continuity for Docker v0.2 product scaffold."""

PRODUCT_NAME = "Bolt-On Continuity for Docker"
PRODUCT_EDITION = "Local Operator Edition"
PRODUCT_VERSION = "0.2"
STAGE = 1
ALLOWED_ACTIONS = ("NO_ACTION", "HOLD", "RELEASE")

__all__ = [
    "ALLOWED_ACTIONS",
    "PRODUCT_EDITION",
    "PRODUCT_NAME",
    "PRODUCT_VERSION",
    "STAGE",
]
