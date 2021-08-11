from typing import List

from authorization.permissions import Permission
from lib.helpers import empty_at_runtime


@empty_at_runtime
class SupportsGetPermissions:
    def get_permissions(self) -> List[Permission]: ...
