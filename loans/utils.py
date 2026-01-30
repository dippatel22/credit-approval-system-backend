from decimal import Decimal
from datetime import date, datetime
from .models import Customer, Loan
import math


def calculate_monthly_installment(principal, annual_rate, tenure_months):
    """
    Calculate monthly installment using compound interest formula.
    Formula: EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
    where P = principal, r = monthly interest rate, n = tenure in months
    """
    if annual_rate == 0:
        return principal / tenure_months
    
    monthly_rate = Decimal(str(annual_rate)) / Decimal('100') / Decimal('12')
    principal_decimal = Decimal(str(principal))
    tenure_decimal = Decimal(str(tenure_months))
    
    # Calculate (1 + r)^n
    one_plus_r_power_n = (Decimal('1') + monthly_rate) ** tenure_decimal
    
    # Calculate EMI
    if one_plus_r_power_n == Decimal('1'):
        return float(principal_decimal / tenure_decimal)
    
    emi = principal_decimal * monthly_rate * one_plus_r_power_n / (one_plus_r_power_n - Decimal('1'))
    
    return float(emi)


def calculate_credit_score(customer):
    """
    Calculate credit score (0-100) based on:
    1. Past loans paid on time
    2. Number of loans taken in past
    3. Loan activity in current year
    4. Loan approved volume
    5. If sum of current loans > approved limit, credit score = 0
    """
    # Check if current debt exceeds approved limit
    if customer.current_debt > customer.approved_limit:
        return 0
    
    # Get all loans for the customer
    all_loans = Loan.objects.filter(customer=customer)
    
    if not all_loans.exists():
        # New customer with no loan history
        return 50  # Default score for new customers
    
    # Calculate total loan volume
    total_volume = sum(loan.loan_amount for loan in all_loans)
    
    # Calculate on-time payment ratio
    total_emis = sum(loan.emis_paid_on_time for loan in all_loans)
    total_expected_emis = sum(loan.tenure for loan in all_loans)
    on_time_ratio = total_emis / total_expected_emis if total_expected_emis > 0 else 0
    
    # Number of loans
    num_loans = all_loans.count()
    
    # Loan activity in current year
    current_year = date.today().year
    current_year_loans = all_loans.filter(start_date__year=current_year).count()
    
    # Calculate score components (weighted)
    score = 0
    
    # On-time payment ratio (40 points max)
    score += min(40, on_time_ratio * 40)
    
    # Number of loans (20 points max) - more loans = better (up to a point)
    score += min(20, (num_loans / 10) * 20) if num_loans > 0 else 0
    
    # Current year activity (20 points max)
    score += min(20, (current_year_loans / 5) * 20) if current_year_loans > 0 else 0
    
    # Loan volume (20 points max) - normalized by approved limit
    if customer.approved_limit > 0:
        volume_ratio = min(1.0, float(total_volume / customer.approved_limit))
        score += volume_ratio * 20
    
    return min(100, max(0, int(score)))


def get_interest_rate_slab(credit_score):
    """
    Determine interest rate slab based on credit score.
    Returns minimum interest rate for the slab (exclusive).
    - If credit_rating > 50, approve loan (any rate)
    - If 50 > credit_rating > 30, approve loans with interest rate > 12%
    - If 30 > credit_rating > 10, approve loans with interest rate > 16%
    - If 10 > credit_rating, don't approve any loans
    """
    if credit_score > 50:
        return 0.0  # Can approve any rate
    elif credit_score > 30:
        return 12.0  # Must be > 12% (strictly greater)
    elif credit_score > 10:
        return 16.0  # Must be > 16% (strictly greater)
    else:
        return None  # No approval


def check_loan_eligibility(customer, loan_amount, interest_rate, tenure):
    """
    Check if loan is eligible based on credit score and other criteria.
    Returns: (approval, corrected_interest_rate, monthly_installment)
    """
    # Calculate credit score
    credit_score = calculate_credit_score(customer)
    
    # Get interest rate slab
    min_interest_rate = get_interest_rate_slab(credit_score)
    
    if min_interest_rate is None:
        return False, interest_rate, 0.0
    
    # Check if sum of all current EMIs > 50% of monthly salary
    current_loans = Loan.objects.filter(customer=customer)
    total_current_emi = sum(loan.monthly_repayment for loan in current_loans)
    
    if total_current_emi > customer.monthly_salary * Decimal('0.5'):
        return False, interest_rate, 0.0
    
    # Calculate monthly installment for new loan
    monthly_installment = calculate_monthly_installment(loan_amount, interest_rate, tenure)
    
    # Check if total EMIs (including new loan) > 50% of monthly salary
    if total_current_emi + Decimal(str(monthly_installment)) > customer.monthly_salary * Decimal('0.5'):
        return False, interest_rate, monthly_installment
    
    # Check interest rate against credit score slab
    corrected_interest_rate = interest_rate
    if min_interest_rate > 0 and interest_rate <= min_interest_rate:
        # Set to minimum + 0.1% increment (lowest of slab)
        corrected_interest_rate = min_interest_rate + 0.1
        # Recalculate EMI with corrected rate
        monthly_installment = calculate_monthly_installment(loan_amount, corrected_interest_rate, tenure)
    
    # Final approval check
    if min_interest_rate is None:
        approval = False
    elif min_interest_rate == 0:
        approval = credit_score > 50  # Can approve any rate if score > 50
    else:
        # For slabs, interest rate must be strictly greater than the minimum
        approval = credit_score > 10 and interest_rate > min_interest_rate
    
    return approval, corrected_interest_rate, monthly_installment

