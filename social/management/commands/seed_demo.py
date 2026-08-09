"""Create deterministic demo content for FriendHub."""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from social.models import Comment, Follow, Notification, Post, PostLike


PRIMARY_DEMO_USERNAME = "estiuk_arnob"
DEMO_PASSWORD = "Arnob1234*"

PEOPLE = [
    (PRIMARY_DEMO_USERNAME, "Estiuk", "Arafat Arnob", "Dhaka", "Full-stack developer building thoughtful digital experiences."),
    ("demo_nabil", "Nabil", "Hasan", "Chattogram", "Developer, photographer, and lifelong learner."),
    ("demo_samira", "Samira", "Khan", "Sylhet", "Collecting recipes, stories, and beautiful sunsets."),
    ("demo_rafi", "Rafi", "Ahmed", "Rajshahi", "Building small ideas into useful things."),
    ("demo_nusrat", "Nusrat", "Jahan", "Khulna", "Books, coffee, and thoughtful conversations."),
    ("demo_tanvir", "Tanvir", "Islam", "Barishal", "Weekend traveler and community volunteer."),
    ("demo_mehjabin", "Mehjabin", "Sultana", "Rangpur", "Sharing everyday creativity and good energy."),
    ("demo_farhan", "Farhan", "Kabir", "Cumilla", "Music enthusiast and friendly neighborhood foodie."),
]

POSTS = [
    "A quiet morning, a clear plan, and a fresh cup of tea. Ready for the day.",
    "Small progress still counts. What is one thing you are proud of today?",
    "Found a beautiful corner of the city today. Sometimes the best moments are unplanned.",
    "Trying a new recipe tonight. The kitchen smells amazing already!",
    "A good conversation can completely change the shape of a difficult day.",
    "Weekend goal: fewer screens, more sunlight, and time with good people.",
    "Learning something new always feels awkward before it feels exciting. Keep going.",
    "Grateful for friends who check in without needing a reason.",
    "Today’s playlist is doing all the heavy lifting. Share a song recommendation!",
    "Finished a project I have been putting off for weeks. That feeling is unmatched.",
    "A reminder to celebrate the ordinary moments too—they become the memories we miss.",
    "What is your favorite place to reset after a busy week?",
    "Community is built one helpful gesture at a time.",
    "Taking a slow walk and noticing how much the neighborhood has changed.",
    "Shared laughter is still the fastest way to make a room feel like home.",
    "Working on a tiny idea that might become something useful. More soon.",
    "The sunset looked like a painting today. I hope everyone got a moment to see it.",
    "Books are proof that you can travel without packing a bag.",
    "Made time for an old friend today. Some connections pick up exactly where they paused.",
    "Kindness does not have to be complicated. Start with listening.",
    "A productive day does not always mean a busy day.",
    "Trying to be more consistent, not perfect. That feels like a healthier goal.",
    "The best part of sharing good news is seeing your friends celebrate with you.",
    "Here’s to more curiosity, more courage, and more reasons to stay connected.",
]

COMMENTS = [
    "This is such a good reminder!",
    "Love this energy.",
    "Could not agree more.",
    "Thanks for sharing this with us!",
    "This made my day a little brighter.",
    "Count me in next time!",
    "Beautifully said.",
    "Exactly what I needed to read today.",
]


class Command(BaseCommand):
    help = "Create eight demo users and a complete sample FriendHub network."

    @transaction.atomic
    def handle(self, *args, **options):
        # Preserve demo content when upgrading from the original primary username.
        legacy_user = User.objects.filter(
            username="demo_ayesha", email="demo_ayesha@example.test"
        ).first()
        current_primary = User.objects.filter(username=PRIMARY_DEMO_USERNAME).first()
        if legacy_user and not current_primary:
            legacy_user.username = PRIMARY_DEMO_USERNAME
            legacy_user.email = f"{PRIMARY_DEMO_USERNAME}@example.test"
            legacy_user.save(update_fields=["username", "email"])
        elif legacy_user and current_primary:
            legacy_user.delete()

        users = []
        for username, first_name, last_name, location, bio in PEOPLE:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"{username}@example.test",
                },
            )
            user.first_name = first_name
            user.last_name = last_name
            user.email = f"{username}@example.test"
            user.set_password(DEMO_PASSWORD)
            user.save()
            user.profile.location = location
            user.profile.bio = bio
            user.profile.save()
            users.append(user)

        demo_usernames = [user.username for user in users]
        Notification.objects.filter(recipient__username__in=demo_usernames).delete()
        Post.objects.filter(author__username__in=demo_usernames).delete()
        Follow.objects.filter(follower__username__in=demo_usernames, following__username__in=demo_usernames).delete()

        for index, follower in enumerate(users):
            for offset in (1, 2, 4):
                Follow.objects.get_or_create(follower=follower, following=users[(index + offset) % len(users)])

        posts = []
        for index, content in enumerate(POSTS):
            posts.append(Post.objects.create(author=users[index % len(users)], content=content))

        for post_index, post in enumerate(posts):
            for offset in range(1, 5):
                liker = users[(post_index + offset) % len(users)]
                if liker != post.author:
                    PostLike.objects.get_or_create(user=liker, post=post)
                    Notification.objects.get_or_create(
                        recipient=post.author,
                        actor=liker,
                        notification_type=Notification.Type.LIKE,
                        post=post,
                    )
            for offset in range(2):
                commenter = users[(post_index + offset + 2) % len(users)]
                comment = Comment.objects.create(
                    author=commenter,
                    post=post,
                    content=COMMENTS[(post_index + offset) % len(COMMENTS)],
                )
                if commenter != post.author:
                    Notification.objects.create(
                        recipient=post.author,
                        actor=commenter,
                        notification_type=Notification.Type.COMMENT,
                        post=post,
                    )

        self.stdout.write(self.style.SUCCESS("FriendHub demo data created successfully."))
        self.stdout.write(f"Login: {PRIMARY_DEMO_USERNAME} / {DEMO_PASSWORD}")
        self.stdout.write("Developed by Estiuk Arafat Arnob")
