"""
URL configuration for hfroot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static

from django.contrib import admin
from django.urls import include, path
import users.views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('friends/', include('friends.urls')),
    path('users/', include('users.urls')),
    path('users/get-current/', users.views.get_current_user, name='get-current-user'),
    path('users/sign-up/', users.views.CreateUserView.as_view(), name='sign_up'),
    path('users/token/', TokenObtainPairView.as_view(), name='get_token'),
    path('users/token/refresh/', TokenRefreshView.as_view(), name='refresh_token'),
    path('users/<int:user_id>/addresses/add/', users.views.AddAddressView.as_view(), name='add-address'),
    path('users/<int:user_id>/addresses/delete/', users.views.DeleteAddressView.as_view(), name='delete-address'),
    path('api-auth/', include('rest_framework.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)