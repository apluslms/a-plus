import logging
import posixpath
import re
import requests
import time
from bs4 import BeautifulSoup
from django.conf import settings
from django.utils.http import parse_http_date_safe
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from urllib.parse import urlparse, urljoin


logger = logging.getLogger('aplus.remote_page')


class RemotePageException(Exception):
    def __init__(self, message, code=500):
        self.message = message
        self.code = code


class RemotePageNotFound(RemotePageException):
    def __init__(self, message):
        super().__init__(message, 404)


class RemotePageNotModified(Exception):

    def __init__(self, expires=None):
        self.expires = expires


def parse_expires(response):
    return parse_http_date_safe(response.headers.get("Expires", "")) or 0


def request_for_response(url, post=False, data=None, files=None, stamp=None):
    try:
        last_retry = len(settings.EXERCISE_HTTP_RETRIES) - 1
        n = 0
        while n <= last_retry:
            try:
                request_time = time.time()
                if post:
                    logger.info("POST %s", url)
                    response = requests.post(
                        url,
                        data=data,
                        files=files,
                        timeout=settings.EXERCISE_HTTP_TIMEOUT
                    )
                else:
                    logger.info("GET %s", url)
                    headers = {}
                    if stamp:
                        headers['If-Modified-Since'] = stamp
                    response = requests.get(
                        url,
                        timeout=settings.EXERCISE_HTTP_TIMEOUT,
                        headers=headers
                    )
                request_time = time.time() - request_time
                logger.info("Response %d (%d sec) %s",
                    response.status_code, request_time, url)
                if response.status_code == 200:
                    return response
                elif response.status_code == 304:
                    raise RemotePageNotModified(parse_expires(response))
                if response.status_code < 500 or n >= last_retry:
                    response.raise_for_status()
            except requests.exceptions.ConnectionError as e:
                logger.warning("ConnectionError %s", url);
                if n >= last_retry:
                    raise e
            logger.info("Sleep %d sec before retry",
                settings.EXERCISE_HTTP_RETRIES[n])
            time.sleep(settings.EXERCISE_HTTP_RETRIES[n])
            n += 1
        logger.error("HTTP request loop ended in unexpected state")
        raise RuntimeError("HTTP request loop ended in unexpected state")
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code == 404:
            raise RemotePageNotFound(_('REQUESTED_RESOURCE_NOT_FOUND_FROM_COURSE_SERVICE'))
        raise RemotePageException(format_lazy(
            _('CONNECTING_TO_COURSE_SERVICE_FAILED -- {code}'),
            code=e.response.status_code if e.response is not None else '-1',
        )) from e


class RemotePage:
    """
    Represents a page that can be loaded over HTTP for further processing.
    """
    def __init__(self, url, post=False, data=None, files=None, stamp=None):
        self.url = urlparse(url)
        self.response = request_for_response(url, post, data, files, stamp)
        self.response.encoding = "utf-8"
        self.soup = BeautifulSoup(self.response.text, 'html5lib')

    def base_address(self):
        path = posixpath.dirname(self.url.path).rstrip('/') + '/'
        url = self.url._replace(path=path, params='', query='', fragment='')
        if settings.REMOTE_PAGE_HOSTS_MAP:
            auth, sep, domain = url.netloc.rpartition('@')
            domain = settings.REMOTE_PAGE_HOSTS_MAP.get(domain, domain)
            url = url._replace(netloc=auth+sep+domain)
        return url

    def meta(self, name):
        if self.soup:
            element = self.soup.find("meta", {"name": name})
            if element:
                return element.get("value",
                    default=element.get("content", default=None))
        return None

    def header(self, name):
        return self.response.headers.get(name, "")

    def last_modified(self):
        return self.header('Last-Modified')

    def expires(self):
        return parse_expires(self.response)

    def title(self):
        if self.soup and self.soup.title:
            return self.soup.title.contents
        return ""

    def head(self, search_attribute):
        if self.soup and self.soup.head:
            return "\n".join(str(tag) for tag in
                self.soup.head.find_all(True, search_attribute))
        return ""

    def select_element_or_body(self, search_attributes):
        if self.soup:
            for attr in search_attributes:
                element = self.soup.find(**attr)
                if element:
                    return element
            return self.soup.body
        return None

    def element_or_body(self, search_attributes):
        element = self.select_element_or_body(search_attributes)
        return str(element) if element else ""

    def clean_element_or_body(self, search_attributes):
        element = self.select_element_or_body(search_attributes)
        if element:
            for once in element.find_all(True, {'data-aplus-once':True}):
                once.extract()
        return str(element) if element else ""

    def body(self):
        return self.element_or_body([])

    def fix_relative_urls(self):
        url = self.base_address()
        for tag,attr in [
            ("img","src"),
            ("script","src"),
            ("iframe","src"),
            ("link","href"),
            ("a","href"),
            ("video","poster"),
            ("source","src"),
        ]:
            self._fix_relative_urls(url, tag, attr)

    def _fix_relative_urls(self, url, tag_name, attr_name):
        # Starts with "#", "//" or "https:".
        test = re.compile('^(#|\/\/|\w+:)', re.IGNORECASE)
        # Ends with filename extension ".html" and possibly "#anchor".
        chapter = re.compile('.*\.html(#.+)?$', re.IGNORECASE)
        # Starts with at least one "../".
        start_dotdot_path = re.compile(r"^(../)+")
        # May end with the language suffix _en or _en/#anchor or _en#anchor.
        lang_suffix = re.compile(r'(?P<lang>_[a-z]{2})?(?P<slash>/)?(?P<anchor>#.+)?$')
        # Detect certain A+ exercise info URLs so that they are not broken by
        # the transformations: "../../module1/chapter/module1_chapter_exercise/info/model/".
        # URLs /plain, /info, /info/model, /info/template.
        exercise_info = re.compile(r'/((plain)|(info(/model|/template)?))/?(#.+)?$')

        for element in self.soup.find_all(tag_name, {attr_name:True}):
            value = element[attr_name]
            if not value:
                continue

            # Custom transform for RST chapter to chapter links.
            if element.has_attr('data-aplus-chapter'):
                m = chapter.match(value)
                if m:
                    i = m.start(1)
                    if i > 0:
                        without_html_suffix = value[:i-5] + value[i:] # Keep #anchor in the end.
                    else:
                        without_html_suffix = value[:-5]
                elif not value.startswith('/'):
                    without_html_suffix = value
                else:
                    continue
                # Remove all ../ from the start and prepend exactly "../../".
                # a-plus-rst-tools modifies chapter links so that the URL path
                # begins from the html build root directory (_build/html).
                # The path starts with "../" to match the directory depth and
                # there are as many "../" as needed to reach the root.
                # Chapter html files are located under module directories in
                # the _build/html directory and some courses use subdirectories
                # under the module directories too.
                # In A+, the URL path must start with "../../" so that it
                # removes the current chapter and module from the A+ chapter
                # page URL: /course/course_instance/module/chapter/
                # (A+ URLs do not have the same "subdirectories" as
                # the real subdirectories in the course git repo.)
                new_val = '../../' + start_dotdot_path.sub("", without_html_suffix)

                split_path = new_val.split('/')
                if len(split_path) > 4 and not exercise_info.search(new_val):
                    # If the module directory has subdirectories in the course
                    # git repo, the subdirectory must be modified in the A+ URL.
                    # The subdirectory slash / is converted to underscore _.
                    # Convert "../../module1/subdir/chapter2_en" into "../../module1/subdir_chapter2_en".
                    # Do not convert if the URL points to an A+ page such as
                    # "../../module1/chapter2/info/model/".
                    chapter_key = '_'.join(split_path[3:])
                    new_val = '/'.join(split_path[:3]) + '/' + chapter_key

                # Remove lang suffix in chapter2_en#anchor without modifying the #anchor.
                # Add slash / to the end before the #anchor.
                m = lang_suffix.search(new_val)
                if m:
                    anchor = m.group('anchor')
                    if anchor is None:
                        anchor = ''
                    new_val = new_val[:m.start()] + '/' + anchor

                element[attr_name] = new_val

            elif value and not test.match(value):

                # Custom transform for RST generated exercises.
                if element.has_attr('data-aplus-path'):
                    # If the exercise description HTML has links to static files such as images,
                    # their links can be fixed with the data-aplus-path="/static/{course}" attribute.
                    # A+ converts "{course}" into the course key used by the backend based on
                    # the exercise service URL. For example, in the MOOC-Grader, exercise service URLs
                    # follow this scheme: "http://grader.local/coursekey/exercisekey".
                    # In the exercise HTML, image <img data-aplus-path="/static/{course}" src="../_images/image.png">
                    # gets the correct URL "http://grader.local/static/coursekey/_images/image.png".
                    fix_path = element['data-aplus-path'].replace(
                        '{course}',
                        url.path.split('/', 2)[1]
                    )
                    fix_value = start_dotdot_path.sub("/", value)
                    value = fix_path + fix_value

                # url points to the exercise service, e.g., MOOC-Grader.
                # This fixes links to static files (such as images) in RST chapters.
                # The image URL must be absolute and refer to the grader server
                # instead of the A+ server. A relative URL with only path
                # "/static/course/image.png" would target the A+ server when
                # it is included in the A+ page. The value should be a relative
                # path in the course build directory so that it becomes the full
                # correct URL to the target file.
                # E.g., urljoin('http://localhost:8080/static/default/module1/chapter.html', "../_images/image.png")
                # -> 'http://localhost:8080/static/default/_images/image.png'
                element[attr_name] = urljoin(url.geturl(), value)

    def find_and_replace(self, attr_name, list_of_attributes):
        l = len(list_of_attributes)
        if l == 0:
            return
        i = 0
        for element in self.soup.find_all(True, {attr_name:True}):
            for name,value in list_of_attributes[i].items():
                if name.startswith('?'):
                    if name[1:] in element:
                        element[name[1:]] = value
                else:
                    element[name] = value
            i += 1
            if i >= l:
                return
