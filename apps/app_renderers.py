# TODO: rename this file to app_renderers.py

# Django
from django.template import Context
from django.template.loader import get_template

# A+
from apps.models import *
from lib.BeautifulSoup import BeautifulSoup
from lib.helpers import update_url_params


def build_app_renderers(plugins,
                           view_name,
                           user_profile=None,
                           submission=None,
                           exercise=None,
                           course_instance=None,
                           course=None,
                           course_module=None,
                           category=None):

    if view_name == "submission":
        context = {
            "user_profile": user_profile,
            "submission": submission,
        }
    elif view_name == "exercise":
        context = {
            "user_profile": user_profile,
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
        t = get_template("plugins/iframe_to_service_plugin.html")
        return t.render(Context({
            "height": self.plugin.height,
            "width": self.plugin.width,
            "src": self._build_src(),
            "title": self.plugin.title,
            "view_name": self.view_name
        }))


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
        opener      = urllib2.build_opener()
        content     = opener.open(self._build_src(), timeout=5).read()

        # Save the page in cache
        # cache.set(self.content_url, content)

        soup            = BeautifulSoup(content)

        # TODO: Disabled. Add GET parameter support and enable.
        # Make links absolute, quoted from http://stackoverflow.com/a/4468467:
        #for tag in soup.findAll('a', href=True):
        #    tag['href'] = urlparse.urljoin(self.content_url, tag['href'])

        # If there's no element specified, use the BODY.
        # Otherwise find the element with given id.
        if self.tab.element_id == "":
            html        = soup.find("body").renderContents()
        else:
            html        = str(soup.find(id=self.element_id))

        return html

