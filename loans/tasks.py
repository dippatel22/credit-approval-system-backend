from celery import shared_task
from django.core.management import call_command
import pandas as pd
from decimal import Decimal
from datetime import datetime
from .models import Customer, Loan
import os
import re


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize excel column names to snake_case-ish lowercase tokens so we can
    support variations like:
    - 'Customer ID' / 'customer_id' / 'customer id'
    - 'Monthly payment' / 'monthly repayment'
    - 'Date of Approval' / 'start date'
    """
    def norm(col: str) -> str:
        col = str(col).strip().lower()
        col = re.sub(r"[^a-z0-9]+", "_", col)
        return col.strip("_")

    df = df.copy()
    df.columns = [norm(c) for c in df.columns]
    return df


@shared_task
def ingest_customer_data():
    """
    Background task to ingest customer data from Excel file.
    """
    try:
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'customer_data.xlsx')
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return {"status": "error", "message": f"File not found: {file_path}"}
        
        df = _normalize_columns(pd.read_excel(file_path))
        
        customers_created = 0
        customers_updated = 0
        
        for _, row in df.iterrows():
            customer_id = int(row.get('customer_id', 0))
            first_name = str(row.get('first_name', ''))
            last_name = str(row.get('last_name', ''))
            phone_number = str(row.get('phone_number', ''))
            monthly_salary = Decimal(str(row.get('monthly_salary', 0)))
            approved_limit = Decimal(str(row.get('approved_limit', 0)))
            current_debt = Decimal(str(row.get('current_debt', 0)))
            age = int(row.get('age', 25))

            if not customer_id:
                continue
            
            # Try to get or create customer
            customer, created = Customer.objects.update_or_create(
                customer_id=customer_id,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone_number,
                    'monthly_salary': monthly_salary,
                    'approved_limit': approved_limit,
                    'current_debt': current_debt,
                    'age': age,
                }
            )
            
            if created:
                customers_created += 1
            else:
                customers_updated += 1
        
        return {
            "status": "success",
            "message": f"Customer data ingested successfully",
            "customers_created": customers_created,
            "customers_updated": customers_updated
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@shared_task
def ingest_loan_data():
    """
    Background task to ingest loan data from Excel file.
    """
    try:
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'loan_data.xlsx')
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return {"status": "error", "message": f"File not found: {file_path}"}
        
        df = _normalize_columns(pd.read_excel(file_path))
        
        loans_created = 0
        loans_updated = 0
        errors = []
        
        for _, row in df.iterrows():
            try:
                customer_id = int(row.get('customer_id', 0))
                loan_id = int(row.get('loan_id', 0))
                loan_amount = Decimal(str(row.get('loan_amount', 0)))
                tenure = int(row.get('tenure', 0))
                interest_rate = Decimal(str(row.get('interest_rate', 0)))

                # In provided sheet this column is "Monthly payment"
                monthly_repayment = Decimal(str(row.get('monthly_payment', row.get('monthly_repayment', 0))))

                # In provided sheet this column is "EMIs paid on Time"
                emis_paid_on_time = int(row.get('emis_paid_on_time', 0))

                # In provided sheet start is "Date of Approval"
                start_date_col = row.get('date_of_approval', row.get('start_date'))
                end_date_col = row.get('end_date')

                if not customer_id or not loan_id:
                    continue

                if pd.isna(start_date_col) or pd.isna(end_date_col):
                    errors.append(f"Missing dates for loan_id={loan_id}")
                    continue

                start_date = pd.to_datetime(start_date_col).date()
                end_date = pd.to_datetime(end_date_col).date()
                
                # Get customer
                try:
                    customer = Customer.objects.get(customer_id=customer_id)
                except Customer.DoesNotExist:
                    errors.append(f"Customer {customer_id} not found for loan {loan_id}")
                    continue
                
                # Try to get or create loan
                loan, created = Loan.objects.update_or_create(
                    loan_id=loan_id,
                    defaults={
                        'customer': customer,
                        'loan_amount': loan_amount,
                        'tenure': tenure,
                        'interest_rate': interest_rate,
                        'monthly_repayment': monthly_repayment,
                        'emis_paid_on_time': emis_paid_on_time,
                        'start_date': start_date,
                        'end_date': end_date
                    }
                )
                
                if created:
                    loans_created += 1
                else:
                    loans_updated += 1
                    
            except Exception as e:
                errors.append(f"Error processing row {_}: {str(e)}")
                continue
        
        # Update customer current_debt based on active loans
        for customer in Customer.objects.all():
            active_loans = Loan.objects.filter(customer=customer)
            total_debt = sum(loan.loan_amount for loan in active_loans)
            customer.current_debt = total_debt
            customer.save()
        
        return {
            "status": "success",
            "message": f"Loan data ingested successfully",
            "loans_created": loans_created,
            "loans_updated": loans_updated,
            "errors": errors
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@shared_task
def ingest_all_data():
    """
    Ingest both customer and loan data.
    """
    customer_result = ingest_customer_data()
    loan_result = ingest_loan_data()
    
    return {
        "customer_ingestion": customer_result,
        "loan_ingestion": loan_result
    }

