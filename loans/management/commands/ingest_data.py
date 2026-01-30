from django.core.management.base import BaseCommand
from loans.tasks import ingest_all_data


class Command(BaseCommand):
    help = 'Ingest customer and loan data from Excel files'

    def handle(self, *args, **options):
        self.stdout.write('Starting data ingestion...')
        result = ingest_all_data()
        
        if result['customer_ingestion']['status'] == 'success':
            self.stdout.write(
                self.style.SUCCESS(
                    f"Customer data ingested: {result['customer_ingestion']['customers_created']} created, "
                    f"{result['customer_ingestion']['customers_updated']} updated"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"Customer ingestion error: {result['customer_ingestion']['message']}")
            )
        
        if result['loan_ingestion']['status'] == 'success':
            self.stdout.write(
                self.style.SUCCESS(
                    f"Loan data ingested: {result['loan_ingestion']['loans_created']} created, "
                    f"{result['loan_ingestion']['loans_updated']} updated"
                )
            )
            if result['loan_ingestion'].get('errors'):
                self.stdout.write(
                    self.style.WARNING(f"Errors: {len(result['loan_ingestion']['errors'])}")
                )
                # Print first few errors to help debugging
                for msg in result['loan_ingestion']['errors'][:10]:
                    self.stdout.write(self.style.WARNING(f"- {msg}"))
        else:
            self.stdout.write(
                self.style.ERROR(f"Loan ingestion error: {result['loan_ingestion']['message']}")
            )

