from typing import List, Protocol

from authorization.permissions import Permission
from lib.helpers import empty_at_runtime


@empty_at_runtime
class SupportsGetPermissions(Protocol):
    def get_permissions(self) -> List[Permission]: ...
