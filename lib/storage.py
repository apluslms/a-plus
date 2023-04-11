import os.path
from django.conf import settings
from django.contrib.staticfiles.storage import StaticFilesStorage


class BumpStaticFilesStorage(StaticFilesStorage):
    # pylint: disable-next=keyword-arg-before-vararg
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        super().__init__(location, base_url, *args, **kwargs)
        self.bump = self.create_bump()

    def create_bump(self):
        git_dir = os.path.join(settings.BASE_DIR, ".git")
        if os.path.isdir(git_dir):
            bump = self._read_file(os.path.join(git_dir, "HEAD"))
            if bump.startswith("ref: "):
                bump = self._read_file(os.path.join(git_dir, bump[5:].strip()))
            return bump
        return None

    def _read_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def url(self, name):
        url = super().url(name)
        if self.bump:
            return url + "?" + self.bump
        return url
