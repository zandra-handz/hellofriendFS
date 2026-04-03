from django.urls import path
from . import views

urlpatterns = [
    path('welcome/', views.get_welcome_scripts, name='get-welcome-scripts'),
    path('ledger/', views.log_welcome_scripts, name='log-gecko-scripts'),
    path('ledger/all/', views.WelcomeScriptLedgerView.as_view(), name='view-gecko-scripts-ledger'),
]
