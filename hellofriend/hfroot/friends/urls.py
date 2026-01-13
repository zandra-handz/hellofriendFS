from django.urls import path
from . import views
import users.views

urlpatterns = [
    path('', views.index, name='index'),
    #path('nextmeets/', views.NextMeetsAllView.as_view()),
    path('upcoming/', views.UpcomingMeetsLightView.as_view()),
    path('upcoming/', views.UpcomingMeetsQuickView.as_view()), # swapping this to test speed; just returns all next meets after checking if they'be been updated for the day
    path('upcoming/comprehensive/', views.UpcomingMeetsView.as_view()),
    path('all/', views.FriendsView.as_view()),
    path('upcoming/friends-included/', views.CombinedFriendsUpcomingView.as_view()),
    path('create/', views.FriendCreateView.as_view()),
    path('update-app-setup/', views.UpdateAppSetupComplete.as_view()),
    path('<int:friend_id>/', views.FriendProfile.as_view()),
    path('<int:friend_id>/info/', views.FriendDetail.as_view()),
    path('<int:friend_id>/dashboard/', views.FriendDashboardView.as_view()),
    path('<int:friend_id>/settings/', views.FriendSuggestionSettingsDetail.as_view()),
    path('<int:friend_id>/settings/update/', views.FriendSuggestionSettingsDetail.as_view()),
    # path('<int:friend_id>/category-limit/', views.FriendSuggestionSettingsCategoryLimit.as_view()),
    path('<int:friend_id>/faves/', views.FriendFavesDetail.as_view()),
    path('<int:friend_id>/faves/add/location/', views.FriendFavesLocationAdd.as_view()),
    path('<int:friend_id>/faves/remove/location/', views.FriendFavesLocationRemove.as_view()),
    path('<int:friend_id>/next-meet/', views.NextMeetView.as_view()),
    path('remix/all/', views.remix_all_next_meets, name='remix-all-next-meets'),
    path('<int:friend_id>/thoughtcapsules/', views.ThoughtCapsulesAll.as_view()),
    # path('<int:friend_id>/thoughtcapsules/by-category/', views.ThoughtCapsulesByCategory.as_view()),
    path('<int:friend_id>/thoughtcapsules/add/', views.ThoughtCapsuleCreate.as_view()),
    path('<int:friend_id>/thoughtcapsule/<uuid:pk>/', views.ThoughtCapsuleDetail.as_view()),
    path('<int:friend_id>/thoughtcapsules/coords-update/', views.ThoughtCapsuleBulkUpdateCoords.as_view()),
    path('<int:friend_id>/thoughtcapsules/batch-update/', views.ThoughtCapsulesUpdateMultiple.as_view()),
    path('<int:friend_id>/thoughtcapsules/completed/', views.CompletedThoughtCapsulesAll.as_view()),
    path('<int:friend_id>/images/', views.ImagesAll.as_view()),
    path('<int:friend_id>/images/by-category/', views.ImagesByCategoryView.as_view()),
    path('<int:friend_id>/images/add/', views.ImageCreate.as_view()),
    path('<int:friend_id>/image/<int:pk>/', views.ImageDetail.as_view()),
    # path('<int:friend_id>/categories/', views.CategoriesView.as_view()),
    path('<int:friend_id>/combinedhelloes/summary/', views.CombinedHelloesLightAll.as_view()),
    path('<int:friend_id>/voidedhelloes/summary/', views.VoidedHelloesLightAll.as_view()),
    path('<int:friend_id>/helloes/summary/', views.HelloesLightAll.as_view()),
    path('<int:friend_id>/helloes/', views.HelloesAll.as_view()),
    path('<int:friend_id>/helloes/add/', views.HelloCreate.as_view()),
    path('<int:friend_id>/helloes/<uuid:pk>/', views.HelloDetail.as_view()),
    path('places/', views.consider_the_drive, name='consider-the-drive'),
    path('places/near-midpoint/', views.consider_midpoint_locations, name='consider-midpoint-locations'),
    path('places/get-details/', views.place_details, name='get_nearby_places'),
    path('places/get-id/', views.place_id, name='get_place_id'),


    path('locations/all/', views.UserLocationsAll.as_view()),
    path('locations/validated/', views.UserLocationsValidated.as_view()),
    path('location/validate-only/', views.ValidateLocation.as_view(), name='validate-location-only'),
    path('locations/add/', views.UserLocationCreate.as_view()),
    path('location/<int:pk>/', views.LocationDetail.as_view()),

    # What is this being used for?
    path('<int:pk>/', views.FriendDetail.as_view()),

    # Friend addresses, currently React Native only
    path('<int:friend_id>/addresses/all/', views.FriendAddressesAll.as_view()),
    path('<int:friend_id>/addresses/validated/', views.FriendAddressesValidated.as_view()),  
    path('<int:friend_id>/addresses/add/', views.FriendAddressCreate.as_view()),
    path('<int:friend_id>/address/<int:pk>/', views.FriendAddressDetail.as_view()),

    # History/stats
    path('<int:friend_id>/categories/history/', users.views.UserCategoriesFriendHistoryAll.as_view()),

    path('categories/history/capsules/', views.CompletedCapsulesHistoryView.as_view()),



    path('dropdown/location-parking-type-choices/', views.LocationParkingTypeChoices.as_view(), name='location-parking-type-choices'),
    path('dropdown/hello-type-choices/', views.HelloTypeChoices.as_view(), name='hello-type-choices'),
    path('dropdown/all-user-locations/', views.UserLocationsAll.as_view()),
    path('dropdown/validated-user-locations/', views.UserLocationsValidated.as_view()),

    # Using to debug a 404 issue in React Native app
    path('addresses/all/', users.views.UserAddressesAll.as_view()),
    path('addresses/validated/', users.views.UserAddressesValidated.as_view()),  
    path('addresses/add/', users.views.UserAddressCreate.as_view()),
    path('address/<int:pk>/', users.views.UserAddressDetail.as_view()),

    # app-wide
    path('notifications/upcoming/48hrs/', views.UpcomingMeetsAll48.as_view(), name='notifications-all-upcoming-48hrs'),
    path('notifications/upcoming/36hrs/', views.UpcomingMeetsAll36.as_view(), name='notifications-all-upcoming-36hrs'),
    path('notifications/upcoming/24hrs/', views.UpcomingMeetsAll24.as_view(), name='notifications-all-upcoming-24hrs'),

]
