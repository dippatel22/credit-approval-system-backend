from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from decimal import Decimal
import math

from .models import Customer, Loan
from .serializers import (
    CustomerSerializer,
    LoanEligibilityRequestSerializer,
    LoanEligibilityResponseSerializer,
    CreateLoanRequestSerializer,
    CreateLoanResponseSerializer,
    LoanDetailSerializer,
    CustomerLoanListSerializer
)
from .utils import (
    calculate_monthly_installment,
    check_loan_eligibility,
    calculate_credit_score
)


@api_view(['POST'])
def register_customer(request):
    """
    Register a new customer.
    approved_limit = 36 * monthly_salary (rounded to nearest lakh)
    """
    # Validate required fields
    required_fields = ['first_name', 'last_name', 'age', 'monthly_income', 'phone_number']
    missing_fields = [field for field in required_fields if field not in request.data]
    
    if missing_fields:
        return Response(
            {'error': f'Missing required fields: {", ".join(missing_fields)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Calculate approved limit
        monthly_salary = Decimal(str(request.data['monthly_income']))
        approved_limit = monthly_salary * Decimal('36')
        
        # Round to nearest lakh (100,000)
        approved_limit = round(approved_limit / Decimal('100000')) * Decimal('100000')
        
        # Create customer
        customer = Customer.objects.create(
            first_name=request.data['first_name'],
            last_name=request.data['last_name'],
            age=int(request.data['age']),
            phone_number=str(request.data['phone_number']),
            monthly_salary=monthly_salary,
            approved_limit=approved_limit,
            current_debt=Decimal('0')
        )
        
        response_serializer = CustomerSerializer(customer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
def check_eligibility(request):
    """
    Check loan eligibility based on credit score.
    """
    serializer = LoanEligibilityRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    customer_id = request.data['customer_id']
    loan_amount = request.data['loan_amount']
    interest_rate = request.data['interest_rate']
    tenure = request.data['tenure']
    
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    approval, corrected_interest_rate, monthly_installment = check_loan_eligibility(
        customer, loan_amount, interest_rate, tenure
    )
    
    response_data = {
        'customer_id': customer_id,
        'approval': approval,
        'interest_rate': interest_rate,
        'corrected_interest_rate': corrected_interest_rate,
        'tenure': tenure,
        'monthly_installment': monthly_installment
    }
    
    serializer = LoanEligibilityResponseSerializer(data=response_data)
    if serializer.is_valid():
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def create_loan(request):
    """
    Process a new loan based on eligibility.
    """
    serializer = CreateLoanRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    customer_id = request.data['customer_id']
    loan_amount = request.data['loan_amount']
    interest_rate = request.data['interest_rate']
    tenure = request.data['tenure']
    
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    approval, corrected_interest_rate, monthly_installment = check_loan_eligibility(
        customer, loan_amount, interest_rate, tenure
    )
    
    if not approval:
        response_data = {
            'loan_id': None,
            'customer_id': customer_id,
            'loan_approved': False,
            'message': 'Loan not approved based on eligibility criteria',
            'monthly_installment': monthly_installment
        }
        serializer = CreateLoanResponseSerializer(data=response_data)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Calculate dates
    from datetime import date, timedelta
    start_date = date.today()
    end_date = start_date + timedelta(days=tenure * 30)  # Approximate months as 30 days
    
    # Create loan
    loan = Loan.objects.create(
        customer=customer,
        loan_amount=Decimal(str(loan_amount)),
        tenure=tenure,
        interest_rate=Decimal(str(corrected_interest_rate)),
        monthly_repayment=Decimal(str(monthly_installment)),
        emis_paid_on_time=0,
        start_date=start_date,
        end_date=end_date
    )
    
    # Update customer's current debt
    customer.current_debt += Decimal(str(loan_amount))
    customer.save()
    
    response_data = {
        'loan_id': loan.loan_id,
        'customer_id': customer_id,
        'loan_approved': True,
        'message': 'Loan approved and created successfully',
        'monthly_installment': monthly_installment
    }
    
    serializer = CreateLoanResponseSerializer(data=response_data)
    if serializer.is_valid():
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def view_loan(request, loan_id):
    """
    View loan details and customer details.
    """
    try:
        loan = Loan.objects.select_related('customer').get(loan_id=loan_id)
    except Loan.DoesNotExist:
        return Response(
            {'error': 'Loan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = LoanDetailSerializer(loan)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def view_customer_loans(request, customer_id):
    """
    View all current loan details by customer id.
    """
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    loans = Loan.objects.filter(customer=customer)
    serializer = CustomerLoanListSerializer(loans, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

