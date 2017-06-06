"""
This middleware is an easter egg! It is invoked when any request parameters
contain the string "drop table" (a potential SQL injection) and prevents the
user from loading any pages. Instead, a response with internal server error code
is returned with a "funny" error message. The SQL injection attempt is stored in
the session, so that the problem persists even if the user reloads the page.
Other users and the actual system are not affected by this middleware.

The normal behavior can be restored by giving any request parameter value with the
string "restore table" in it.
"""

from django.http import HttpResponseServerError

class SqlInjectionMiddleware(object):

    def process_request(self, request):
        for var in request.GET:
            val = request.GET.get(var).lower()
            if "drop table" in val:
                request.session["hack_attempt"] = val
            if "restore table" in val and "hack_attempt" in request.session:
                del request.session["hack_attempt"]

        if "hack_attempt" in request.session:
            return HttpResponseServerError("Traceback (most recent call last):\nFile \"egg.py\", line 1337, in aplus\nDatabaseIntegrityError: aHR0cDovL3hrY2QuY29tLzMyNy8= is not a valid base64 table identifier", content_type="text/plain")

        return None
