from userprofile import STUDENT_GROUP

def student_group(request):
    """
    Currently disabled. 
    
    """
    return {"active_group": request.META.get(STUDENT_GROUP, None)}
