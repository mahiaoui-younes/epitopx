"""URL configuration for EpitopX SaaS platform."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'epitopx-backend'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),

    # ── API v1 ────────────────────────────────────────────────────────────
    path('api/v1/', include('api.urls')),
    path('api/v1/msa/', include('bioinformatics.api.urls')),

    # ── JWT token endpoints ───────────────────────────────────────────────
    path('api/v1/auth/token/',         TokenObtainPairView.as_view(),  name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(),     name='token_refresh'),
    path('api/v1/auth/token/verify/',  TokenVerifyView.as_view(),      name='token_verify'),

    # ── Legacy v0 alias (backwards compat — proxied by Node frontend) ─────
    path('api/', include('api.urls')),
    path('api/msa/', include('bioinformatics.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
