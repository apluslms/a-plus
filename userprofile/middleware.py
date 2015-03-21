from django.middleware.common import CommonMiddleware
from django.shortcuts import redirect
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.contrib.auth.models import User

from userprofile import STUDENT_GROUP, STUDENT_GROUP_ID

class StudentGroupMiddleware(object):
    
    def process_request(self, request):
        """
        This function checks if the user is authenticated and if he/she has selected a student
        group which to use for submitting exercises. If there is a group selected (and stored 
        in the session) this middleware will load the group from database and add it to the 
        request as a meta header.
        """
        request.META[STUDENT_GROUP] = None
        
        if request.user.is_authenticated():
            
            # Check if this request is made to change the active group
            group_to_use = request.REQUEST.get("change_to_group", None)
            if group_to_use != None:
                # Save the group in session
                request.session[STUDENT_GROUP_ID] = group_to_use
                # Redirect to the same URL without the group changing parameter
                return redirect(request.path)
            
            group_id = request.session.get(STUDENT_GROUP_ID, None)
            
            if group_id != None:
                try:
                    group = request.user.userprofile.groups.get(id=group_id)
                    request.META[STUDENT_GROUP] = group
                except:
                    # The group does not exist or the user is not a member in it
                    # so we remove the group id from session
                    request.session[STUDENT_GROUP_ID] = None
                return None # HttpResponseBadRequest("Reading signature failed.")
