from django.contrib import admin

from .models import Comment, Follow, Notification, Post, PostLike, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "location", "updated_at")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "short_content", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content", "author__username")

    @admin.display(description="Content")
    def short_content(self, obj):
        return obj.content[:60]


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    search_fields = ("follower__username", "following__username")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "post", "created_at")
    search_fields = ("content", "author__username")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "actor", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")


admin.site.register(PostLike)

admin.site.site_header = "FriendHub Administration"
admin.site.site_title = "FriendHub Admin"
admin.site.index_title = "Developed by Estiuk Arafat Arnob"
