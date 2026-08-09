from django.urls import path

from . import views

app_name = "social"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<str:username>/", views.profile_view, name="profile"),
    path("posts/<int:pk>/", views.post_detail, name="post_detail"),
    path("search/", views.search_view, name="search"),
    path("notifications/", views.notifications_view, name="notifications"),
    path("about/", views.about, name="about"),
]
