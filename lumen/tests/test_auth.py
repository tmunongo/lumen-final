import pytest


@pytest.mark.django_db
class TestAuthenticationMiddlewareAndViews:
    def test_auth_bypassed_when_disabled(self, client, settings):
        settings.LUMEN_AUTH_DISABLED = True
        response = client.get("/")
        # Should not redirect to login when auth is disabled
        assert response.status_code != 302 or response.url != "/login/?return_to=%2F"

    def test_login_flow(self, client, settings):
        settings.LUMEN_AUTH_DISABLED = False
        settings.LUMEN_USERNAME = "admin"
        settings.LUMEN_PASSWORD = "secretpassword"

        # Unauthenticated request redirects to login
        response = client.get("/")
        assert response.status_code == 302
        assert "/login" in response.url

        # Invalid credentials
        login_resp = client.post("/login/", {"username": "admin", "password": "wrong"})
        assert login_resp.status_code == 200
        assert "Invalid username or password" in login_resp.content.decode()

        # Valid credentials
        valid_resp = client.post(
            "/login/", {"username": "admin", "password": "secretpassword"}
        )
        assert valid_resp.status_code == 302
        assert valid_resp.url == "/"

        # Now logged in, accessing root succeeds
        root_resp = client.get("/")
        assert root_resp.status_code == 200

    def test_logout(self, client, settings):
        settings.LUMEN_AUTH_DISABLED = False
        settings.LUMEN_USERNAME = "admin"
        settings.LUMEN_PASSWORD = "secretpassword"

        client.post("/login/", {"username": "admin", "password": "secretpassword"})
        logout_resp = client.get("/logout/")
        assert logout_resp.status_code == 302
        assert logout_resp.url == "/login/"

        # Subsequent request requires login again
        assert client.get("/").status_code == 302
