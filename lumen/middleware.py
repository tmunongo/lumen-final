from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class LumenAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_disabled = getattr(settings, "LUMEN_AUTH_DISABLED", False)
        expected_password = getattr(settings, "LUMEN_PASSWORD", "")

        if auth_disabled or not expected_password:
            return self.get_response(request)

        path = request.path_info
        login_url = reverse("login")
        logout_url = reverse("logout")

        if path.startswith("/static/") or path == login_url or path == logout_url:
            return self.get_response(request)

        if request.session.get("authenticated") is True:
            return self.get_response(request)

        return redirect(f"{login_url}?return_to={path}")
