from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Generates API Auth Tokens for all existing users who do not have one.'
    )

    def handle(self, *args, **options):
        users_without_tokens = User.objects.filter(auth_token__isnull=True)
        count = users_without_tokens.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    'All users already possess an active API token.'
                )
            )
            return

        self.stdout.write(
            f'Found {count} user(s) missing tokens. Generating...'
        )

        # Prepare all Token instances in memory
        new_tokens = [Token(user=user) for user in users_without_tokens]

        Token.objects.bulk_create(new_tokens)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated {count} new API tokens!'
            )
        )
