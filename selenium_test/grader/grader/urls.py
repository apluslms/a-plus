from django.urls import path

from exercises import views

urlpatterns = [
    path('first_exercise/', views.first),
    path('file_exercise/', views.file),
    path('ajax_exercise/', views.ajax, name="ajax"),
]
