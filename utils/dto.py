from dataclasses import dataclass
from typing import Any


@dataclass
class GenericFuncResp:
    success: bool = False
    message: str = ''
    data: Any = None
