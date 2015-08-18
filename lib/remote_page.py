import requests
import logging
import urllib.parse
import posixpath
from bs4 import BeautifulSoup
from django.utils.translation import ugettext_lazy as _


logger = logging.getLogger("aplus.remotepage")


class RemotePageException(Exception):

    def __init__(self, message):
        self.message = message


class RemotePage:
    """
    Represents a page that can be loaded over HTTP for further processing.
    """
    def __init__(self, url, timeout=20, post=False, data=None, files=None):
        self.url = urllib.parse.urlparse(url)
        try:
            if post:
                self.response = requests.post(url, data=data, files=files,
                    timeout=timeout)
            else:
                self.response = requests.get(url, timeout=timeout)
            if self.response.status_code != 200:
                self.response.raise_for_status()
            self.response.encoding = "utf-8"
            self.soup = BeautifulSoup(self.response.text)
        except requests.exceptions.RequestException:
            logger.exception("Failed to load external page: %s", url)
            raise RemotePageException(
                _("Connecting to the course service failed!"))

    def base_url(self):
        return urllib.parse.urlunparse((
            self.url.scheme,
            self.url.netloc,
            posixpath.dirname(self.url.path),
            self.url.params,
            self.url.query,
            self.url.fragment
        ))

    def title(self):
        if self.soup and self.soup.title:
            return self.soup.title.contents
        return ""

    def body(self):
        if self.soup and self.soup.body:
            return self.soup.body.renderContents()
        return ""

    def element_or_body(self, search_id):
        if self.soup:
            element = self.soup.find(id=search_id)
            if element:
                return element.renderContents()
        return self.body()

    def fix_relative_urls(self):
        base_url = self.base_url()
        self._fix_relative_urls(base_url, "img", "src")
        self._fix_relative_urls(base_url, "script", "src")
        self._fix_relative_urls(base_url, "link", "href")
        self._fix_relative_urls(base_url, "a", "href")

    def _fix_relative_urls(self, base_url, tag_name, attr_name):
        for element in self.soup.findAll(tag_name, {attr_name: True}):
            value = element[attr_name]
            if not value.startswith("http://"):
                element[attr_name] = "".join((
                    base_url,
                    "/" if value[0] != "/" else "",
                    value
                ))

    def meta(self, name):
        if self.soup:
            element = self.soup.find("meta", {"name": name})
            if element:
                return element.get("value",
                    default=element.get("content", default=None))
        return None
