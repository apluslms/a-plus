from django.urls import path

from . import views

urlpatterns = [
    path('', views.ExamStartView.as_view()),
    path('<int:pk>', views.ExamDetailView.as_view(), name='exam_details'),
]
