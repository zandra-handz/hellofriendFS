from django.urls import path
from . import views
import friends.views

urlpatterns = [
    path('<int:user_id>/addresses/add/', views.AddAddressView.as_view()),
    path('<int:user_id>/addresses/delete/', views.DeleteAddressView.as_view()),
    path('settings/', views.UserSettingsDetail.as_view()),
    path('settings/update/', views.UserSettingsDetail.as_view()),
    path('<int:user_id>/profile/', views.UserProfileDetail.as_view()),
    path('<int:user_id>/profile/update/', views.UserProfileDetail.as_view()),
    path('<int:user_id>/subscription/update/', views.UpdateSubscriptionView.as_view()),
    path('<int:user_id>/categories/', views.UserCategoriesView.as_view()), 
    path('<int:user_id>/categories/add/', views.UserCategoriesView.as_view()), 
    path('<int:user_id>/category/<int:pk>/', views.UserCategoryDetail.as_view()), 
    path('categories/history/', views.UserCategoriesHistoryAll.as_view()),
    path('categories/history/summary/', views.UserCategoriesHistoryCapsuleIdsOnly.as_view()),
    path('categories/history/count/', views.UserCategoriesHistoryCountOnly.as_view()),
   # this one is in friends app views because capsules belong to that app:
   # path('categories/history/capsules/', views.UserCapsulesHistoryView.as_view()),



    

    path('addresses/all/', views.UserAddressesAll.as_view()),
    path('addresses/validated/', views.UserAddressesValidated.as_view()),  
    path('addresses/add/', views.UserAddressCreate.as_view()),
    path('address/<int:pk>/', views.UserAddressDetail.as_view()),
]