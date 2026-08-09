from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("social.urls")),
    path("api/", include("social.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "social.views.error_403"
handler404 = "social.views.error_404"
handler500 = "social.views.error_500"
