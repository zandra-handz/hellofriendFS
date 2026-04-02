from django.core.management.base import BaseCommand
from geckoscripts.models import Welcome


# Usage:
#   python manage.py create_welcome_script --label "my_label" --body "Hi {user_name}, welcome!"
#
# All type flags default to True (universal — applies to everyone).
# Pass --no-<flag> to exclude a specific type.
#
# Example — only for curious personality, night hours:
#   python manage.py create_welcome_script \
#       --label "curious_night_welcome" \
#       --body "Hi {user_name}, welcome back!" \
#       --no-personality-scientific --no-personality-brave \
#       --no-hours-day --no-hours-random
#
# Optional flags:
#   --experimental    marks the script as experimental (default: False)
#   --easter-egg      marks the script as an easter egg (default: False)


class Command(BaseCommand):
    help = 'Create a Welcome script'

    def add_arguments(self, parser):
        parser.add_argument('--label', required=True, help='Short internal label for this script')
        parser.add_argument('--body', required=True, help='Script text. Use {user_name} as a placeholder for the user\'s name')
        parser.add_argument('--personality-curious', action='store_true', default=True)
        parser.add_argument('--no-personality-curious', dest='personality_curious', action='store_false')
        parser.add_argument('--personality-scientific', action='store_true', default=True)
        parser.add_argument('--no-personality-scientific', dest='personality_scientific', action='store_false')
        parser.add_argument('--personality-brave', action='store_true', default=True)
        parser.add_argument('--no-personality-brave', dest='personality_brave', action='store_false')
        parser.add_argument('--memory-amnesiac', action='store_true', default=True)
        parser.add_argument('--no-memory-amnesiac', dest='memory_amnesiac', action='store_false')
        parser.add_argument('--memory-remembersome', action='store_true', default=True)
        parser.add_argument('--no-memory-remembersome', dest='memory_remembersome', action='store_false')
        parser.add_argument('--memory-remembermany', action='store_true', default=True)
        parser.add_argument('--no-memory-remembermany', dest='memory_remembermany', action='store_false')
        parser.add_argument('--hours-day', action='store_true', default=True)
        parser.add_argument('--no-hours-day', dest='hours_day', action='store_false')
        parser.add_argument('--hours-night', action='store_true', default=True)
        parser.add_argument('--no-hours-night', dest='hours_night', action='store_false')
        parser.add_argument('--hours-random', action='store_true', default=True)
        parser.add_argument('--no-hours-random', dest='hours_random', action='store_false')
        parser.add_argument('--story-learner', action='store_true', default=True)
        parser.add_argument('--no-story-learner', dest='story_learner', action='store_false')
        parser.add_argument('--story-nommer', action='store_true', default=True)
        parser.add_argument('--no-story-nommer', dest='story_nommer', action='store_false')
        parser.add_argument('--story-escaper', action='store_true', default=True)
        parser.add_argument('--no-story-escaper', dest='story_escaper', action='store_false')
        parser.add_argument('--experimental', action='store_true', default=False)
        parser.add_argument('--easter-egg', action='store_true', default=False)

    def handle(self, *args, **options):
        script = Welcome.objects.create(
            label=options['label'],
            body=options['body'],
            personality_curious=options['personality_curious'],
            personality_scientific=options['personality_scientific'],
            personality_brave=options['personality_brave'],
            memory_amnesiac=options['memory_amnesiac'],
            memory_remembersome=options['memory_remembersome'],
            memory_remembermany=options['memory_remembermany'],
            activity_hours_day=options['hours_day'],
            activity_hours_night=options['hours_night'],
            activity_hours_random=options['hours_random'],
            story_learner=options['story_learner'],
            story_nommer=options['story_nommer'],
            story_escaper=options['story_escaper'],
            is_experimental=options['experimental'],
            is_easter_egg=options['easter_egg'],
        )
        self.stdout.write(self.style.SUCCESS(f'Created Welcome script [{script.id}]: {script.label}'))
