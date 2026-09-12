from django.core.management.base import BaseCommand

from apps.knowledge.evaluation.diagnostics import run_diagnostics


class Command(BaseCommand):
    help = "Inspect semantic retrieval rankings for known evaluation failures."

    def handle(self, *args, **options):
        run_diagnostics()