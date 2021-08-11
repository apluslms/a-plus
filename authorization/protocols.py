from typing import List, Protocol

from authorization.permissions import Permission
from lib.helpers import object_at_runtime


@object_at_runtime
class SupportsGetPermissions(Protocol):
    def get_permissions(self) -> List[Permission]: ...
