import importlib
import logging
from typing import List, Tuple

from django.conf import settings


logger = logging.getLogger('aplus.course')

class StudentInfoSystem:
    """Base class for university-specific SIS system extensions, such as SISU at Aalto."""

    def get_instances(self, _course: str) -> List[Tuple[str, str]]:
        """
        Get active course instances from SIS based on the course code.

        Parameters
        ----------
        course
            Course code for which instances are fetched

        Returns
        -------
        List of tuples representing instances. The first part of the tuple is an
        identifier by which specific instance data can be found in the API. The second part
        is an instance description shown to the user.
        """
        return []

    def get_course_data(self, _id: str) -> dict:
        """
        Get course data (teachers, start/end times) from the SIS system.

        Parameters
        ----------
        id
            SIS identifier of the course instance

        Returns
        -------
        Dictionary of course data. Currently possible keys are 'starting_time',
        'ending_time' and 'teachers' (list of teacher usernames).
        """
        return {}

    def get_participants(self, _id: str) -> List[str]:
        """
        Get participating students from the SIS system.

        Parameters
        ----------
        id
            SIS identifier of the course instance

        Returns
        -------
        List of student identifiers.
        """
        return []


def get_sis_configuration() -> StudentInfoSystem:
    '''
    Loads the proper SIS plugin based on settings.

    Returns
    -------
    StudentInfoSystem - inherited object that implements university-specific
    functionality and APIs for SIS interactions.
    '''
    if not hasattr(settings, 'SIS_PLUGIN_MODULE') or not hasattr(settings, 'SIS_PLUGIN_CLASS'):
        logger.debug(
            '"course.sis.get_sis_configuration()" called but SIS settings are missing. '
            'Check "settings.SIS_PLUGIN_MODULE" and "settings.SIS_PLUGIN_CLASS".'
        )
        return None

    mod = importlib.import_module(settings.SIS_PLUGIN_MODULE, package='course')

    pluginclass = getattr(mod, settings.SIS_PLUGIN_CLASS)
    if pluginclass is None:
        raise NameError(
            f'SIS plugin module "{settings.SIS_PLUGIN_MODULE}" does not define '
            f'the class "{settings.SIS_PLUGIN_CLASS}". '
            'Check "settings.SIS_PLUGIN_MODULE" and "settings.SIS_PLUGIN_CLASS".',
        )
    plugin = pluginclass()

    return plugin
