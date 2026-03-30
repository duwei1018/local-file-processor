from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class ConversionResult:
    output_path: str
    success: bool
    message: str = ""


class BaseConverter:
    FROM_EXT: str = ""
    TO_EXT: str = ""

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        raise NotImplementedError

    @classmethod
    def can_handle(cls, from_ext: str, to_ext: str) -> bool:
        return (
            from_ext.lower() == cls.FROM_EXT.lower()
            and to_ext.lower() == cls.TO_EXT.lower()
        )
