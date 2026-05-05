from django.core.management.base import BaseCommand
from project.ml_service import train_and_save


class Command(BaseCommand):
    help = "Train the churn predictor and save it to ml_models/churn.pkl"

    def handle(self, *args, **opts):
        try:
            stats = train_and_save()
        except ValueError as e:
            self.stderr.write(self.style.ERROR(f"Training aborted: {e}"))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Trained on {stats['rows']} rows · accuracy={stats['accuracy']}"
        ))
        self.stdout.write("Top features:")
        sorted_feats = sorted(stats['feature_importances'].items(), key=lambda x: -x[1])
        for name, imp in sorted_feats:
            self.stdout.write(f"  {name:30s} {imp:.3f}")
