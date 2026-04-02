from django.urls import path
from . import views

urlpatterns = [
    path('welcome/', views.get_welcome_scripts, name='get-welcome-scripts'),
]
