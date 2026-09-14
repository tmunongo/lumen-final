import hmac

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse


def login_view(request):
    if request.session.get("authenticated") is True:
        return redirect("projects_index")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        expected_username = getattr(settings, "LUMEN_USERNAME", "lumen")
        expected_password = getattr(settings, "LUMEN_PASSWORD", "")

        user_ok = hmac.compare_digest(username.lower(), expected_username.lower())
        pass_ok = hmac.compare_digest(password, expected_password)

        if user_ok and pass_ok:
            request.session.flush()
            request.session["authenticated"] = True
            request.session["username"] = username
            return_to = request.GET.get("return_to", reverse("projects_index"))
            return redirect(return_to if return_to.startswith("/") else "/")
        else:
            messages.error(request, "Invalid username or password.")
            return render(
                request,
                "sessions/new.html",
                {"error": "Invalid username or password."},
                status=200,
            )

    return render(request, "sessions/new.html")


def logout_view(request):
    request.session.flush()
    messages.info(request, "Signed out successfully.")
    return redirect("login")
