import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Generator, Generic, Iterable, List, Optional, Tuple, Type, TypeVar, Union, overload

from aplus_auth import settings as auth_settings
from aplus_auth.payload import Payload, Permission, PermissionItem, PermissionItemList
from rest_framework.exceptions import AuthenticationFailed

from authorization.models import JWTAccessible
from lib.aplus_auth import audience_to_alias
from lib.typing import AnyUser

if TYPE_CHECKING:
    from course.models import Course, CourseInstance
    from exercise.exercise_models import BaseExercise
    from exercise.submission_models import Submission


logger = logging.getLogger('aplus.authentication')

_jwt_accessible_managers: Dict[str, JWTAccessible] = {}


@overload
def register_jwt_accessible_class(type_id: str) -> Callable[[Type[Any]], Type[Any]]: ...
@overload
def register_jwt_accessible_class(cls: Type[Any], type_id: str) -> Type[Any]: ...
def register_jwt_accessible_class(cls, type_id = None): # type: ignore
    """
    a decorator to register a model to be accessible through JWT

    cls.objects must inherit JWTAccessible
    """
    def wrapper(cls: Type[Any]) -> Type[Any]:
        global _jwt_accessible_managers
        if not isinstance(cls.objects, JWTAccessible):
            raise TypeError(f"{cls} does not have a JWTAccessible manager")
        _jwt_accessible_managers[type_id] = cls.objects
        return cls

    if type_id is None:
        # cls is actually type_id
        type_id = cls
        return wrapper
    else:
        return wrapper(cls)


def _get_objects_from_permission(
        user: AnyUser,
        payload: Payload,
        type: str,
        permission: Permission,
        kwargs: Dict[str, Any]
        ) -> Iterable[Any]:
    """
    Gets the objects corresponding to a permission.
    Raises AuthenticationFailed if the user doesn't have permission.
    Create permissions do not have objects, so they should return empty lists if kwargs are otherwise ok.
    """
    global _jwt_accessible_managers
    cls = _jwt_accessible_managers.get(type)
    if cls is None:
        # Fail by default
        logger.info(f"Missing jwt class for type {type}")
        raise AuthenticationFailed(f"No {permission} access to {type} with {kwargs}")

    items = cls.from_jwt_permission(user, payload, permission, kwargs, auth_settings().DISABLE_LOGIN_CHECKS)
    if items is None:
        logger.info(f"{audience_to_alias(payload.iss)}\n tried to get {permission} access to {type} with {kwargs}")
        raise AuthenticationFailed(f"No {permission} access to {type} with {kwargs}")

    return items


def _get_objects_from_permissions(
        user: AnyUser,
        payload: Payload,
        permission_items: PermissionItemList
        ) -> Tuple[
            List[Tuple[Permission, Dict[str, Any]]],
            List[Tuple[Permission, Any]]
        ]:
    return (
        list(
            (permission, obj)
            for type, permission, kwargs in permission_items
            if permission == Permission.CREATE
            for obj in _get_objects_from_permission(user, payload, type, permission, kwargs)
        ), list(
            (permission, obj)
            for type, permission, kwargs in permission_items
            if permission != Permission.CREATE
            for obj in _get_objects_from_permission(user, payload, type, permission, kwargs)
        )
    )


_objT = TypeVar("_objT")
class ObjectPermissionList(Generic[_objT]):
    def __init__(self):
        self.creates: List[PermissionItem] = []
        self.instances: List[Tuple[Permission, _objT]] = []

    def add_create(self, **kwargs: Any):
        self.creates.append((Permission.CREATE, kwargs))

    def add(self, permission: Permission, obj: _objT):
        assert permission != Permission.CREATE
        self.instances.append((permission, obj))

    def get_creates(self, **kwargs: Any) -> Generator[Union[Tuple[None, None], Tuple[Permission, Dict[str, Any]]], None, None]:
        for value in self.creates:
            for k, v in kwargs.items():
                if k not in value[1] or value[1][k] != v:
                    yield value

    def get_create(self, raise_if_multiple = False, **kwargs: Any) -> Tuple[Optional[Permission], Optional[Dict[str, Any]]]:
        g = self.get_creates(**kwargs)
        v = next(g, (None, None))
        if raise_if_multiple:
            v2 = next(g, None)
            if v2 is not None:
                raise KeyError("Multiple permissions match given conditions")
            return v
        else:
            return v

    def has(self, obj: _objT, permission: Permission = None):
        assert permission != Permission.CREATE
        if permission is None:
            return any((obj == o for _,o in self.instances))
        else:
            return (permission, obj) in self.instances

    def __contains__(self, item: Union[_objT, Tuple[Permission, _objT]]):
        if isinstance(item, tuple):
            return self.has(item[1], item[0])
        else:
            return self.has(item)

    @staticmethod
    def from_payload(user: AnyUser, payload: Payload, permission_items: PermissionItemList):
        perms = ObjectPermissionList()
        perms.creates, perms.instances = _get_objects_from_permissions(user, payload, permission_items)
        return perms

class ObjectPermissions:
    """
    Create permissions are dicts because the objects don't exist yet.
    """
    def __init__(self):
        self.courses: ObjectPermissionList["Course"] = ObjectPermissionList()
        self.instances: ObjectPermissionList["CourseInstance"] = ObjectPermissionList()
        self.submissions: ObjectPermissionList["Submission"] = ObjectPermissionList()

    @staticmethod
    def from_payload(user: AnyUser, payload: Payload):
        """
        Extracts object from JWT payload's permissions and checks access.
        Raise AuthenticationFailed if user has no access.
        """
        perms = ObjectPermissions()
        perms.courses = ObjectPermissionList.from_payload(user, payload, payload.permissions.courses)
        perms.instances = ObjectPermissionList.from_payload(user, payload, payload.permissions.instances)
        perms.submissions = ObjectPermissionList.from_payload(user, payload, payload.permissions.submissions)
        return perms
