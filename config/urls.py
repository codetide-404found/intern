from django.contrib import admin
from django.conf import settings
from django.urls import include, path

urlpatterns = [
    # The admin needs a login and lives at /manage/ unless DJANGO_ADMIN_URL says otherwise.
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('listings.urls')),
]
