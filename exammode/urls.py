from django.urls import path
from django.conf.urls import url

from . import views

urlpatterns = [
    path('', views.ExamStartView.as_view(), name='exam_start'),
    path('<int:pk>', views.ExamDetailView.as_view(), name='exam_details'),
    path('<int:pk>/finish', views.ExamEndView.as_view(), name='exam_end'),
    path('exam_final_info', views.ExamFinalView.as_view(), name='exam_final_info'),
    path('exam_module_not_defined', views.ExamModuleNotDefined.as_view(),
         name="exam_module_not_defined")
]
