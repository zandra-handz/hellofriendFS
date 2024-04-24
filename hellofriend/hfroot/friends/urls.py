from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('nextmeets/', views.NextMeetsAllView.as_view()),
    path('upcoming/', views.UpcomingMeetsView.as_view()),
    path('all/', views.FriendsView.as_view()),
    path('create/', views.FriendCreateView.as_view()),
    path('<int:friend_id>/', views.FriendDetail.as_view()),
    path('<int:friend_id>/settings/', views.FriendSuggestionSettingsDetail.as_view()),
    path('<int:friend_id>/settings/update/', views.FriendSuggestionSettingsDetail.as_view()),
    path('<int:friend_id>/faves/', views.FriendFavesDetail.as_view()),
    path('<int:friend_id>/next-meet/', views.NextMeetView.as_view()),
    path('<int:friend_id>/thoughtcapsules/', views.ThoughtCapsulesAll.as_view()),
    path('<int:friend_id>/thoughtcapsules/by-category/', views.ThoughtCapsulesByCategory.as_view()),
    path('<int:friend_id>/thoughtcapsules/add/', views.ThoughtCapsuleCreate.as_view()),
    path('<int:friend_id>/thoughtcapsule/<uuid:pk>/', views.ThoughtCapsuleDetail.as_view()),
    path('<int:friend_id>/images/', views.ImagesAll.as_view()),
    path('<int:friend_id>/images/by-category/', views.ImagesByCategoryView.as_view()),
    path('<int:friend_id>/images/add/', views.ImageCreate.as_view()),
    path('<int:friend_id>/image/<int:pk>/', views.ImageDetail.as_view()),
    path('<int:friend_id>/categories/', views.CategoriesView.as_view()),
    path('<int:friend_id>/helloes/', views.HelloesAll.as_view()),
    path('<int:friend_id>/helloes/add/', views.HelloCreate.as_view()),
    path('<int:friend_id>/helloes/<uuid:pk>/', views.HelloDetail.as_view()),
    path('places/', views.consider_the_drive, name='consider-the-drive'),
    path('locations/all/', views.UserLocationsAll.as_view()),
    path('locations/validated/', views.UserLocationsValidated.as_view()),
    path('location/validate-only/', views.ValidateLocation.as_view(), name='validate-location-only'),
    path('locations/add/', views.UserLocationCreate.as_view()),
    path('location/<int:pk>/', views.LocationDetail.as_view()),

    # What is this being used for?
    path('<int:pk>/', views.FriendDetail.as_view()),

    path('dropdown/hello-type-choices/', views.HelloTypeChoices.as_view(), name='hello-type-choices'),
    path('dropdown/all-user-locations/', views.UserLocationsAll.as_view()),
    path('dropdown/validated-user-locations/', views.UserLocationsValidated.as_view()),
]
