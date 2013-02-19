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

# Python
import logging

# Django
from django.template import Context
from django.template.loader import get_template

# A+
from apps.models import *
from lib.BeautifulSoup import BeautifulSoup
from lib.helpers import update_url_params


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
        elif view_name == "course_instance":
            context = {
                "user_profile": user_profile,
                "course_instance": course_instance,
            }
        else:
            raise ValueError(view_name + " is not supported for plugins.")

        plugins = plugins.filter(views__contains=view_name)

        renderers = []
        for p in plugins:
            p = p.as_leaf_class()
            if hasattr(p, "get_renderer_class"):
                renderers.append(p.get_renderer_class()(p, view_name, context))
            else:
                # TODO: use some general renderer instead which supports the old
                # rendering style where plugin's render method is called
                renderers.append(p)

        return renderers
    except Exception as e:
        # TODO: Better error handling.
        # If anything goes wrong, just return an empty list so that this isn't
        # a show-stopper for the A+ core functionality.
        logging.exception(e)
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

        for k, v in self.context.items():
            params[k + "_id"] = v.encode_id()

        return update_url_params(self.plugin.service_url, params)

    def render(self):
        try:
            t = get_template("plugins/iframe_to_service_plugin.html")
            return t.render(Context({
                "height": self.plugin.height,
                "width": self.plugin.width,
                "src": self._build_src(),
                "title": self.plugin.title,
                "view_name": self.view_name
            }))
        except Exception as e:
            # TODO: Better error handling.
            # If anything goes wrong, just return an empty string so that this
            # isn't a show-stopper for the A+ core functionality.
            logging.exception(e)
            return ""


class ExternalIFrameTabRenderer(object):
    def __init__(self, tab, user_profile, course_instance):
        self.tab = tab
        self.user_profile = user_profile
        self.course_instance = course_instance

    def _build_src(self):
        params = {
            "course_instance_id": self.course_instance.encode_id(),
            "user_profile_id": self.user_profile.encode_id()
        }

        return update_url_params(self.tab.content_url, params)

    def render(self):
        t = get_template("plugins/external_iframe_tab.html")
        return t.render(Context({
            "height": self.tab.height,
            "width": self.tab.width,
            "src": self._build_src(),
        }))


class TabRenderer(object):
    def __init__(self, tab, user_profile, course_instance):
        self.tab = tab
        self.user_profile = user_profile
        self.course_instance = course_instance

    def _build_src(self):
        params = {
            "course_instance_id": self.course_instance.encode_id(),
            "user_profile_id": self.user_profile.encode_id()
        }

        return update_url_params(self.tab.content_url, params)

    def render(self):
        opener = urllib2.build_opener()
        content = opener.open(self._build_src(), timeout=5).read()

        # Save the page in cache
        # cache.set(self.content_url, content)

        soup = BeautifulSoup(content)

        # TODO: Disabled. Add GET parameter support and enable.
        # Make links absolute, quoted from http://stackoverflow.com/a/4468467:
        #for tag in soup.findAll('a', href=True):
        #    tag['href'] = urlparse.urljoin(self.content_url, tag['href'])

        # If there's no element specified, use the BODY.
        # Otherwise find the element with given id.
        if self.tab.element_id == "":
            html = soup.find("body").renderContents()
        else:
            html = str(soup.find(id=self.element_id))

        return html

