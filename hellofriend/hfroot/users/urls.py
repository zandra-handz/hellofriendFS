from django.urls import path
from . import views

urlpatterns = [
    path('<int:user_id>/addresses/add/', views.AddAddressView.as_view()),
    path('<int:user_id>/addresses/delete/', views.DeleteAddressView.as_view()),
    path('<int:user_id>/settings/', views.UserSettingsDetail.as_view()),
    path('<int:user_id>/settings/update/', views.UserSettingsDetail.as_view()),
    path('<int:user_id>/profile/', views.UserProfileDetail.as_view()),
    path('<int:user_id>/profile/update/', views.UserProfileDetail.as_view()),
    path('<int:user_id>/subscription/update/', views.UpdateSubscriptionView.as_view()),
    path('<int:user_id>/categories/', views.UserCategoriesView.as_view()), 
    path('<int:user_id>/categories/add/', views.UserCategoriesView.as_view()), 

    

    path('addresses/all/', views.UserAddressesAll.as_view()),
    path('addresses/validated/', views.UserAddressesValidated.as_view()),  
    path('addresses/add/', views.UserAddressCreate.as_view()),
    path('address/<int:pk>/', views.UserAddressDetail.as_view()),
]