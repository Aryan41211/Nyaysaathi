from django.urls import path

from . import auth_routes

urlpatterns = [
    path("signup", auth_routes.signup, name="auth-signup"),
    path("login", auth_routes.login, name="auth-login"),
]
