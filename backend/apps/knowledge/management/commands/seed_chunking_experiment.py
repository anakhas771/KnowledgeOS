from django.core.management.base import BaseCommand

from apps.knowledge.evaluation.chunking import (
    CHUNKING_CONFIGS,
    get_config,
    seed_configuration,
)


class Command(BaseCommand):
    help = (
        "Seed the isolated chunking-experiment corpora. Each configuration "
        "gets its own organization; identical source documents are used for "
        "all of them."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--configs",
            nargs="+",
            type=str,
            default=None,
            help=(
                "Configuration names to seed (default: all). Available: "
                + ", ".join(config.name for config in CHUNKING_CONFIGS)
            ),
        )

    def handle(self, *args, **options):
        names = options.get("configs") or [
            config.name for config in CHUNKING_CONFIGS
        ]

        for name in names:
            config = get_config(name)

            self.stdout.write(
                f"\nSeeding '{config.name}' "
                f"(chunk_size={config.chunk_size}, "
                f"overlap={config.overlap})..."
            )

            result = seed_configuration(config)

            self.stdout.write(
                self.style.SUCCESS(
                    f"  organization={result['organization_slug']} "
                    f"(id={result['organization_id']}) "
                    f"documents={result['documents']} "
                    f"chunks={result['total_chunks']}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nChunking experiment corpora seeded successfully."
            )
        )
        self.stdout.write(
            "The real user corpus and the existing retrieval-evaluation "
            "corpus were not modified."
        )
