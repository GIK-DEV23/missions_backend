"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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

from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
]


from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from .api import api, health_check

if settings.ALLOW_ADMIN_SITE:
    urlpatterns = [path(settings.ADMIN_URL, admin.site.urls)]

urlpatterns += [
    path("api/", api.urls),
    re_path(r'^api/v1/(?P<path>.*)$', RedirectView.as_view(url='/api/%(path)s', query_string=True, permanent=False)),
    path("health/", health_check),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)