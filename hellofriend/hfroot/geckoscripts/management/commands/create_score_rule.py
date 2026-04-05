from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from geckoscripts.models import ScoreRule


# Usage:
#   python manage.py create_score_rule --code "FEED_GECKO" --points 10
#   python manage.py create_score_rule --code "FEED_GECKO" --label "Fed the gecko" --points 10 --version 2


class Command(BaseCommand):
    help = 'Create a ScoreRule'

    def add_arguments(self, parser):
        parser.add_argument('--code', required=True, help='Unique code per version (sent by front end)')
        parser.add_argument('--label', default='', help='Human-readable label')
        parser.add_argument('--points', type=int, required=True, help='Points awarded for this code')
        parser.add_argument('--version', type=int, default=1, help='Rule version (default: 1)')

    def handle(self, *args, **options):
        try:
            rule = ScoreRule.objects.create(
                code=options['code'],
                label=options['label'],
                points=options['points'],
                version=options['version'],
            )
        except IntegrityError:
            raise CommandError(
                f"ScoreRule with code='{options['code']}' and version={options['version']} already exists."
            )

        self.stdout.write(self.style.SUCCESS(
            f'Created ScoreRule [{rule.id}]: {rule.code} v{rule.version} = {rule.points}'
        ))
