from django.urls import path
from . import views
import friends.views

urlpatterns = [
    path('<int:user_id>/addresses/add/', views.AddAddressView.as_view()),
    path('<int:user_id>/addresses/delete/', views.DeleteAddressView.as_view()),
    path('settings/', views.UserSettingsDetail.as_view()),
    path('settings/update/', views.UserSettingsDetail.as_view()),
    path('gecko/totals/', views.GeckoCombinedDataDetail.as_view()),
    path('gecko/sessions/', views.GeckoCombinedDataSessionsAll.as_view()), 
    path('gecko/sessions/range/', views.GeckoCombinedDataSessionsTimeRange.as_view()), 
    
    
    path('<int:user_id>/profile/', views.UserProfileDetail.as_view()),
    path('<int:user_id>/profile/update/', views.UserProfileDetail.as_view()),
    path('<int:user_id>/subscription/update/', views.UpdateSubscriptionView.as_view()),
    path('<int:user_id>/categories/', views.UserCategoriesView.as_view()), 
    path('<int:user_id>/categories/add/', views.UserCategoriesView.as_view()), 
    path('<int:user_id>/category/<int:pk>/', views.UserCategoryDetail.as_view()), 
    path('categories/history/', views.UserCategoriesHistoryAll.as_view()),
    path('categories/history/summary/', views.UserCategoriesHistoryCapsuleIdsOnly.as_view()),
    path('categories/history/count/', views.UserCategoriesHistoryCountOnly.as_view()),


    path('points/add/', views.AddPointsView.as_view()),
    path('points/ledger/', views.PointsLedgerView.as_view()),
   # this one is in friends app views because capsules belong to that app:
   # path('categories/history/capsules/', views.UserCapsulesHistoryView.as_view()),



    

    path('addresses/all/', views.UserAddressesAll.as_view()),
    path('addresses/validated/', views.UserAddressesValidated.as_view()),  
    path('addresses/add/', views.UserAddressCreate.as_view()),
    path('address/<int:pk>/', views.UserAddressDetail.as_view()),

    path('gecko/configs/', views.GeckoConfigsView.as_view(), name='gecko-configs'),
    path('gecko/score-state/', views.GeckoScoreStateView.as_view(), name='gecko-score-state'),
    path('gecko/configs/choices/', views.gecko_config_choices, name='gecko-config-choices'),
    path('gecko/points/all/ledger/', views.GeckoPointsLedgerView.as_view()),

    path('gecko/energy-log/', views.GeckoEnergyLogView.as_view(), name='gecko-energy-log'),
    path('gecko/energy-sync/', views.GeckoEnergySyncSampleView.as_view(), name='gecko-energy-sync'),
    path('gecko/dev/reset-energy/', views.dev_reset_energy, name='dev-reset-energy'),
    path('gecko/dev/deplete-energy/', views.dev_deplete_energy, name='dev-deplete-energy'),

    path('friend-link-code/', views.create_or_reset_friend_link_code),

    path('live-sesh/current/', views.get_current_live_sesh, name='live-sesh-current'),
    path('live-sesh/current/cancel/', views.cancel_current_live_sesh, name='live-sesh-current-cancel'),       
    path('live-sesh/invites/', views.get_live_sesh_invites, name='live-sesh-invites'),
    path('live-sesh/invites/<int:invite_id>/accept/', views.accept_live_sesh_invite, name='live-sesh-invite-accept'),
 
]