from django.urls import path
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$',
        views.ExamStartView.as_view(),
        name='home'),
    path('exam/', views.ExamStartView.as_view(), name='exam_start'),
    path('<int:pk>', views.ExamDetailView.as_view(), name='exam_details'),
]
