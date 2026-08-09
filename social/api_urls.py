from django.urls import path

from . import api_views

app_name = "social_api"

urlpatterns = [
    path("auth/register/", api_views.api_register, name="register"),
    path("auth/login/", api_views.api_login, name="login"),
    path("auth/logout/", api_views.api_logout, name="logout"),
    path("me/", api_views.api_me, name="me"),
    path("feed/", api_views.api_feed, name="feed"),
    path("profiles/<str:username>/", api_views.api_profile, name="profile"),
    path("profiles/<str:username>/<str:kind>/", api_views.api_connections, name="connections"),
    path("users/<int:user_id>/follow/", api_views.api_follow, name="follow"),
    path("posts/", api_views.api_posts, name="posts"),
    path("posts/<int:post_id>/", api_views.api_post_detail, name="post-detail"),
    path("posts/<int:post_id>/like/", api_views.api_like, name="like"),
    path("posts/<int:post_id>/comments/", api_views.api_comments, name="comments"),
    path("comments/<int:comment_id>/", api_views.api_comment_detail, name="comment-detail"),
    path("search/", api_views.api_search, name="search"),
    path("notifications/", api_views.api_notifications, name="notifications"),
    path("notifications/read-all/", api_views.api_notifications_read_all, name="notifications-read-all"),
    path("notifications/<int:notification_id>/read/", api_views.api_notification_read, name="notification-read"),
]
