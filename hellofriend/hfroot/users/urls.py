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


    path('gecko/score-state/', views.GeckoScoreStateView.as_view(), name='gecko-score-state'),
    path('gecko/score-state/configs/', views.GeckoScoreStateConfigsView.as_view(), name='gecko-score-state-configs'),
    path('gecko/configs/choices/', views.gecko_config_choices, name='gecko-config-choices'),
    path('gecko/points/all/ledger/', views.GeckoPointsLedgerView.as_view()),

    path('gecko/energy-log/', views.GeckoEnergyLogView.as_view(), name='gecko-energy-log'),
    # Open endpoint returning all users' GeckoEnergyLog rows. Query params:
    #   ?since=<iso>       filter recorded_at >= since (e.g. 2026-04-01T00:00:00Z)
    #   ?until=<iso>       filter recorded_at <  until
    #   ?user_id=<id>      filter to a single user
    #   ?page=<n>          paginated, 30 rows/page (MediumPagination)
    #   ?nopaginate=true   return all matching rows in one response
    path('gecko/analytics/energy-log/', views.GeckoEnergyLogAnalyticsView.as_view(), name='gecko-analytics-energy-log'),

    # Open endpoint returning all users' GeckoEnergySyncSample rows. Query params:
    #   ?since=<iso>       filter created_at >= since
    #   ?until=<iso>       filter created_at <  until
    #   ?user_id=<id>      filter to a single user
    #   ?trigger=<name>    filter to one trigger (update_gecko_data | get_score_state | flush | connect)
    #   ?page=<n>          paginated, 30 rows/page (MediumPagination)
    #   ?nopaginate=true   return all matching rows in one response
    path('gecko/analytics/energy-sync/', views.GeckoEnergySyncSampleAnalyticsView.as_view(), name='gecko-analytics-energy-sync'),

    # Plotly dashboard comparing server_energy_after vs client_energy per user.
    # Local dummy-data preview (no server needed), open in browser via PowerShell:
    #   Invoke-Item "<path-to>\hellofriendFS\hellofriend\hfroot\templates\gecko_analytics_preview.html"
    path('gecko/analytics/dashboard/', views.gecko_analytics_dashboard, name='gecko-analytics-dashboard'),
    path('gecko/energy-sync/', views.GeckoEnergySyncSampleView.as_view(), name='gecko-energy-sync'),
    path('gecko/dev/reset-energy/', views.dev_reset_energy, name='dev-reset-energy'),
    path('gecko/dev/deplete-energy/', views.dev_deplete_energy, name='dev-deplete-energy'),

    path('friend-link-code/', views.create_or_reset_friend_link_code),

    path('live-sesh/current/', views.get_current_live_sesh, name='live-sesh-current'),
    path('live-sesh/current/cancel/', views.cancel_current_live_sesh, name='live-sesh-current-cancel'),       
    path('live-sesh/invites/', views.get_live_sesh_invites, name='live-sesh-invites'),
    path('live-sesh/invites/<int:invite_id>/accept/', views.accept_live_sesh_invite, name='live-sesh-invite-accept'),
    path('live-sesh/invites/<int:invite_id>/decline/', views.decline_live_sesh_invite, name='live-sesh-invite-decline'),

    path('gecko/game-wins/', views.GeckoGameWinsList.as_view(), name='gecko-game-wins-list'),
    path('gecko/game-wins/given/', views.GeckoGameWinsGivenList.as_view(), name='gecko-game-wins-given-list'),
    path('gecko/game-wins/pending/', views.GeckoGameWinPendingDetail.as_view(), name='gecko-game-win-pending'),
    path('gecko/game-wins/match/pending/', views.GeckoGameMatchWinPendingDetail.as_view(), name='gecko-game-match-win-pending'),

]