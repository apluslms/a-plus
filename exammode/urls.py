from django.urls import path
from django.conf.urls import url

from . import views
from exercise.urls import EXERCISE_URL_PREFIX

EXAM_EXERCISE_URL = EXERCISE_URL_PREFIX[1:] if EXERCISE_URL_PREFIX[0] == '^' else EXERCISE_URL_PREFIX

urlpatterns = [
    url( r'^exam/' + EXAM_EXERCISE_URL + r'$',
        views.ExamsStudentView.as_view(),
        name="exam_chapter"),
    path('', views.ExamStartView.as_view(), name='exam_start'),
    path('<int:pk>', views.ExamDetailView.as_view(), name='exam_details'),
    path('<int:pk>/finish', views.ExamEndView.as_view(), name='exam_end'),
    path('<int:pk>/report', views.ExamReportView.as_view(), name='exam_report'),
    path('exam_final_info', views.ExamFinalView.as_view(), name='exam_final_info'),
    path('exam_module_not_defined', views.ExamModuleNotDefined.as_view(),
         name="exam_module_not_defined")
]
