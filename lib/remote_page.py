import logging
import posixpath
import requests
import time
import urllib.parse
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


logger = logging.getLogger("aplus.remote_page")


class RemotePageException(Exception):

    def __init__(self, message):
        self.message = message


class RemotePage:
    """
    Represents a page that can be loaded over HTTP for further processing.
    """
    def __init__(self, url, post=False, data=None, files=None):
        self.url = urllib.parse.urlparse(url)
        try:
            self.response = self._request(url, post, data, files)
        except requests.exceptions.RequestException:
            raise RemotePageException(
                _("Connecting to the course service failed!"))
        self.response.encoding = "utf-8"
        self.soup = BeautifulSoup(self.response.text)

    def _request(self, url, post=False, data=None, files=None):
        last_retry = len(settings.EXERCISE_HTTP_RETRIES) - 1
        n = 0
        while n <= last_retry:
            try:
                if post:
                    response = requests.post(url, data=data, files=files,
                        timeout=settings.EXERCISE_HTTP_TIMEOUT)
                else:
                    response = requests.get(url,
                        timeout=settings.EXERCISE_HTTP_TIMEOUT)
                if response.status_code == 200:
                    return response
                elif response.status_code >= 500 and n < last_retry:
                    logger.warning("Retrying: Server error {:d} at {}".format(
                        response.status_code, url))
                else:
                    response.raise_for_status()
            except requests.exceptions.ConnectionError as e:
                if n >= last_retry:
                    raise e
                logger.warning("Retrying: ConnectionError to {}".format(url));
            time.sleep(settings.EXERCISE_HTTP_RETRIES[n])
            n += 1
        logger.error("HTTP request loop ended in unexpected state")
        assert False

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

    def head_aplus(self):
        if self.soup and self.soup.head:
            return "\n".join(str(tag) for tag in
                self.soup.head.find_all({'data-aplus':True}))
        return ""

    def body(self):
        if self.soup and self.soup.body:
            return self.soup.body.renderContents()
        return ""

    def element_or_body(self, search_attributes):
        if self.soup:
            for attr in search_attributes:
                element = self.soup.find(**attr)
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
            if value and not (value.startswith("http://")
                    or value.startswith("https://")
                    or value.startswith("#")):
                element[attr_name] = "".join((
                    base_url,
                    "/" if (value[0] != "/" and (not base_url or base_url[-1] != "/")) else "",
                    value
                ))

    def meta(self, name):
        if self.soup:
            element = self.soup.find("meta", {"name": name})
            if element:
                return element.get("value",
                    default=element.get("content", default=None))
        return None
