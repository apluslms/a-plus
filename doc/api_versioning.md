API versioning
==============

Why not Accept header?
----------------------

We mark api versions in url prefix, even though this is not considered best
practice.

It's often argued that addidn v2/ in url breaks the REST paradigm. that is
the case, but as we already have api/ in the url we already broke the REST
paradigm. If idea of REST we should implement api as different representation
if normal resource urls.

Thus path course/test_course/test_instance/ should return the web page with
accept header html and "api" json or xml entry with those Acceopt headers.
If API would be implemented that way, then we would use accept header for
requesting specific version of resource representation. Of course that could
use query parameters as fallback.

Version numbers
---------------

To keep urls as static as possible, we will update the api version number only
when new version is not backwards compatible with the old. For cases where
client is updated and is communicating with old version of a-plus, client
should check api version from content type header. A-plus should return error
of client requests newer version of API than what it currently supports.

This process should not come up in normal operation, but in the testing pahse
of client app and some a-plus installation. Also old clients should break when
old API urls are removed, thus indicating they are too old.