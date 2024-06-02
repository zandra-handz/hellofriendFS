from django.urls import path
from . import views

urlpatterns = [
    path('<int:user_id>/addresses/add/', views.AddAddressView.as_view()),
    path('<int:user_id>/addresses/delete/', views.DeleteAddressView.as_view()),
    path('<int:user_id>/settings/', views.UserSettingsDetail.as_view()),
    path('<int:user_id>/settings/update/', views.UserSettingsDetail.as_view()),
    path('<int:user_id>/profile/', views.UserProfileDetail.as_view()),
    path('<int:user_id>/profile/update/', views.UserProfileDetail.as_view()),
    path('<int:user_id>/profile/update/addresses/add/', views.AddAddressToUserProfile.as_view()),
]