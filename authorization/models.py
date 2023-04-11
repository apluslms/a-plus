from typing import Any, Dict, Generic, Iterable, Optional, TypeVar
from aplus_auth.payload import Payload, Permission

from django.db.models import Manager
from django.db.models.base import Model
from django.db.models.query import QuerySet

from lib.typing import AnyUser


_ModelT = TypeVar("_ModelT", bound=Model)
class JWTAccessible(Manager[_ModelT], Generic[_ModelT]):
    """
    Simple Manager base class to get an object from the A+ auth library JWT permission dict.

    Note: not an actual model but a manager
    """
    def from_jwt_permission( # pylint: disable=too-many-arguments
            self,
            user: AnyUser,
            payload: Payload,
            permission: Permission,
            kwargs: Dict[str, Any],
            disable_permission_check = False,
            ) -> Optional[Iterable[_ModelT]]:

        if permission in (Permission.WRITE, Permission.READ):
            instances = self.from_jwt_permission_dict(kwargs)
            if disable_permission_check or all(
                        self.has_access(user, payload, permission, obj)
                        for obj in instances
                    ):
                return instances
        elif permission == Permission.CREATE:
            if disable_permission_check or self.has_create_access(user, payload, kwargs):
                return []
        return None

    def from_jwt_permission_dict(self, perm: Dict[str, Any]) -> QuerySet[_ModelT]:
        """
        Return objects corresponding to a dictionary in a JWT payload's permission list.
        """
        return self.filter(**perm).all()

    # pylint: disable-next=unused-argument
    def has_create_access(self, user: AnyUser, payload: Payload, kwargs: Dict[str, Any]) -> bool:
        """
        Check that <payload> has create access to kwargs.
        """
        return False

    # pylint: disable-next=unused-argument
    def has_access(self, user: AnyUser, payload: Payload, permission: Permission, instance: _ModelT) -> bool:
        """
        Check that <payload> has <permission> access to <instance>.
        """
        return False
