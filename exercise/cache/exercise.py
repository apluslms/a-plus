import logging
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from django.conf import settings
from django.http.request import HttpRequest

from lib.cache import CachedAbstract
from lib.remote_page import RemotePageNotModified

if TYPE_CHECKING:
    from course.models import CourseInstance
    from userprofile.models import UserProfile
    from ..models import BaseExercise

logger = logging.getLogger('aplus.cached')

try:
    from lz4.block import compress as _compress, decompress
    def compress(data):
        return _compress(data, compression=1)
except ImportError:
    logger.warning("Unable to import lz4, using a slower zlib instead")
    from zlib import compress as _compress, decompress
    def compress(data):
        return _compress(data, level=1)


class ExerciseCache(CachedAbstract):
    """ Exercise HTML content """
    KEY_PREFIX = "exercise"

    def __init__( # pylint: disable=too-many-arguments
            self,
            exercise: 'BaseExercise',
            language: str,
            request: HttpRequest,
            students: List['UserProfile'],
            url_name: str,
            ordinal: Optional[int] = None,
            ) -> None:
        self.exercise = exercise
        self.load_args = [language, request, students, url_name, ordinal]
        super().__init__(exercise, modifiers=[language])

    def _needs_generation(self, data: Dict[str, Any]) -> bool:
        expires = data['expires'] if data else None
        return not expires or time.time() > expires
    # pylint: disable-next=arguments-differ
    def _generate_data(self, exercise: 'BaseExercise', data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            page = exercise.load_page(
                *self.load_args,
                last_modified=data['last_modified'] if data else None
            )

            content = compress(page.content.encode('utf-8'))

            return {
                'head': page.head,
                'content': content,
                'last_modified': page.last_modified,
                'expires': page.expires if page.is_loaded else 0,
            }
        except RemotePageNotModified as e:
            if e.expires:
                data['expires'] = e.expires
            return data

    def head(self) -> str:
        return self.data['head']

    def content(self) -> str:
        content = decompress(self.data['content']).decode('utf-8')
        return content


def invalidate_instance(instance: 'CourseInstance') -> None:
    for module in instance.course_modules.all():
        for exercise in module.learning_objects.all():
            for language,_ in settings.LANGUAGES:
                ExerciseCache.invalidate(exercise, modifiers=[language])
