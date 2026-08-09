def friendhub_context(request):
    if not request.user.is_authenticated:
        return {"unread_notification_count": 0, "header_notifications": []}
    notifications = request.user.notifications.select_related("actor", "actor__profile", "post")
    return {
        "unread_notification_count": notifications.filter(is_read=False).count(),
        "header_notifications": notifications[:5],
    }
