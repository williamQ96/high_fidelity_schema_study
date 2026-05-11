from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import DatasetSchema


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, path: str) -> DatasetSchema:
        raise NotImplementedError
