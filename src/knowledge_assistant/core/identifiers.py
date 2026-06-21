"""Typed identifiers for knowledge-base entities."""

from typing import NewType

DocumentId = NewType("DocumentId", str)
ChunkId = NewType("ChunkId", str)
