import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseConnector(ABC):
    '''Abstract base class for all data connectors.'''

    def __init__(self, connector_type: str, name: str):
        self.connector_type = connector_type
        self.name = name

    @abstractmethod
    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def read(self, path: str) -> Any:
        ...

    @abstractmethod
    def write(self, path: str, data: Any) -> bool:
        ...

    @abstractmethod
    def get_schema(self, path: str = "") -> List[Dict[str, Any]]:
        ...

    def health_check(self) -> Dict[str, Any]:
        try:
            _ = self.list_objects()
            return {"status": "healthy", "type": self.connector_type, "name": self.name}
        except Exception as e:
            return {"status": "unhealthy", "type": self.connector_type, "name": self.name, "error": str(e)}
