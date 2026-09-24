from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class ParsedEntity:
    id: str
    name: str
    entity_type: str  # "file", "module", "class", "function", "method", "variable", "package", "api_endpoint"
    file_path: str
    line_number: Optional[int] = None
    language: Optional[str] = None
    module: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedRelation:
    source_id: str
    target_id: str
    rel_type: str  # "CONTAINS", "IMPORTS", "EXPORTS", "CALLS", "EXTENDS", "IMPLEMENTS", "DEPENDS_ON", "DEFINES", "USES", "EXPOSES", "ROUTES_TO"
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    @abstractmethod
    def supports(self, file_path: str) -> bool:
        """Returns True if this parser can handle the given file."""
        pass

    @abstractmethod
    def parse_file(
        self,
        file_path: str,
        content: str,
        project_root: str = ""
    ) -> Tuple[List[ParsedEntity], List[ParsedRelation]]:
        """Parses source code into entities and relations."""
        pass
