from django.http import HttpResponse
from django.urls import path

from lumen import views


def placeholder_home(request):
    return HttpResponse("Lumen Space Home")


urlpatterns = [
    path("", placeholder_home, name="projects_index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]
