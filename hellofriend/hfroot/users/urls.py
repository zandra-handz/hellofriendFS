from django.urls import path
from . import views

urlpatterns = [
    path('<int:user_id>/settings/', views.UserSettingsDetail.as_view()),
    path('<int:user_id>/settings/update/', views.UserSettingsDetail.as_view()),
    path('<int:user_id>/profile/', views.UserProfileDetail.as_view()),
    path('<int:user_id>/profile/update/', views.UserProfileDetail.as_view()),
]