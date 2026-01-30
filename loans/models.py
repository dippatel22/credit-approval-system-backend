from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Customer(models.Model):
    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField(validators=[MinValueValidator(18)])
    phone_number = models.CharField(max_length=15, unique=True)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    approved_limit = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    current_debt = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))])

    class Meta:
        db_table = 'customers'
        ordering = ['customer_id']

    def __str__(self):
        return f"{self.first_name} {self.last_name} (ID: {self.customer_id})"


class Loan(models.Model):
    loan_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    tenure = models.IntegerField(validators=[MinValueValidator(1)])
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    monthly_repayment = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    emis_paid_on_time = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loans'
        ordering = ['-created_at']

    def __str__(self):
        return f"Loan {self.loan_id} - Customer {self.customer.customer_id}"

    @property
    def repayments_left(self):
        """Calculate remaining EMIs"""
        # Calculate based on tenure and EMIs paid
        remaining = self.tenure - self.emis_paid_on_time
        return max(0, remaining)

