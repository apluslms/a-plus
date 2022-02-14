"""
App renderers are objects that wrap an instance of an AbstractApp and the
the context where the app will be rendered into a single object. App renderers
can then passed to templates where their render method should be called to
render the html of the app.

App renderers are most useful with BasePlugin apps since they can be rendered
in many different views with different contexts. A helper function
build_plugin_renderers is provided for consistent and simple renderer building
in views.

Plugin view is a term that is used as an abstraction of the apps architecture
of A+. It consists of a name and definition of the context in that view. For
example, a in the course_instance view, plugins have the UserProfile of the
user logged in and the CourseInstance being viewed available for the plugin
renderer to use while rendering the plugin for the course_instance view. If the
plugin would for example just render a greeting for the user, it could use the
user's name in the greeting as it is available through the UserProfile object.

The available plugin views are
- submission
- exercise
- course_instance

The definition of the context of each plugin view can read from the code. The
code that calls the build_plugin_renderers is responsible of giving the
data required by the plugin view.
"""

import logging
import urllib.request

from bs4 import BeautifulSoup
from django.template.loader import get_template

from lib.helpers import update_url_params


logger = logging.getLogger("aplus.apps")


def build_plugin_renderers(plugins,
                           view_name,
                           user_profile=None,
                           submission=None,
                           exercise=None,
                           course_instance=None,
                           course=None,
                           course_module=None,
                           category=None):

    try:
        if view_name == "submission":
            context = {
                "user_profile": user_profile,
                "course_instance": course_instance,
                "exercise": exercise,
                "submission": submission,
            }
        elif view_name == "exercise":
            context = {
                "user_profile": user_profile,
                "course_instance": course_instance,
                "exercise": exercise,
            }
        #elif view_name == "course_instance":
        else:
            context = {
                "user_profile": user_profile,
                "course_instance": course_instance,
            }
        #else:
        #    raise ValueError(view_name + " is not supported for plugins.")

        plugins = plugins.filter(views__contains=view_name)

        renderers = []
        for p in plugins:
            if hasattr(p, "get_renderer_class"):
                renderers.append(p.get_renderer_class()(p, view_name, context))
            else:
                renderers.append(p)

        return renderers

    except Exception:
        # If anything goes wrong, just return an empty list so that this isn't
        # a show-stopper for the A+ core functionality.
        logger.exception("Failed to create plugin renderers.")
        return []


class ExternalIFramePluginRenderer(object):

    def __init__(self, plugin, view_name, context):
        self.plugin = plugin
        self.view_name = view_name
        self.context = context

    def _build_src(self):
        params = {
            "view_name": self.view_name
        }
        for k, v in list(self.context.items()):
            if v is not None:
                params[k + "_id"] = v.id
        return update_url_params(self.plugin.service_url, params)

    def render(self):
        try:
            t = get_template("plugins/iframe_to_service_plugin.html")
            return t.render({
                "height": self.plugin.height,
                "width": self.plugin.width,
                "src": self._build_src(),
                "title": self.plugin.title,
                "view_name": self.view_name
            })
        except Exception:
            # If anything goes wrong, just return an empty string so that this
            # isn't a show-stopper for the A+ core functionality.
            logger.exception("Failed to render an external iframe plugin.")
            return ""


class ExternalIFrameTabRenderer(object):

    def __init__(self, tab, user_profile, course_instance):
        self.tab = tab
        self.user_profile = user_profile
        self.course_instance = course_instance

    def _build_src(self):
        params = {
            "course_instance_id": self.course_instance.id,
            "user_profile_id": self.user_profile.id
        }
        return update_url_params(self.tab.content_url, params)

    def render(self):
        t = get_template("plugins/external_iframe_tab.html")
        return t.render({
            "height": self.tab.height,
            "width": self.tab.width,
            "src": self._build_src(),
        })


class TabRenderer(object):

    def __init__(self, tab, user_profile, course_instance):
        self.tab = tab
        self.user_profile = user_profile
        self.course_instance = course_instance

    def _build_src(self):
        params = {
            "course_instance_id": self.course_instance.id,
            "user_profile_id": self.user_profile.id
        }
        return update_url_params(self.tab.content_url, params)

    def render(self):
        url = self._build_src()
        opener = urllib.request.build_opener()
        content = opener.open(url, timeout=5).read()

        soup = BeautifulSoup(content)

        # If there's no element specified, use the BODY.
        if self.tab.element_id == "":
            html = str(soup.find("body"))
        else:
            html = str(soup.find(id=self.tab.element_id))

        # TODO: should make relative link addresses absolute

        return html
