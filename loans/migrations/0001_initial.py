# Generated migration file
from django.db import migrations, models
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('customer_id', models.AutoField(primary_key=True, serialize=False)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('age', models.IntegerField(validators=[django.core.validators.MinValueValidator(18)])),
                ('phone_number', models.CharField(max_length=15, unique=True)),
                ('monthly_salary', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('approved_limit', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('current_debt', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
            ],
            options={
                'db_table': 'customers',
                'ordering': ['customer_id'],
            },
        ),
        migrations.CreateModel(
            name='Loan',
            fields=[
                ('loan_id', models.AutoField(primary_key=True, serialize=False)),
                ('loan_amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('tenure', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('interest_rate', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('monthly_repayment', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))])),
                ('emis_paid_on_time', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loans', to='loans.customer')),
            ],
            options={
                'db_table': 'loans',
                'ordering': ['-created_at'],
            },
        ),
    ]

