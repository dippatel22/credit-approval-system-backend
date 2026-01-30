from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from loans.models import Customer, Loan
from loans.utils import calculate_monthly_installment


class BaseAPITestCase(APITestCase):
    def create_customer(
        self,
        *,
        customer_id: int | None = None,
        first_name: str = "Test",
        last_name: str = "User",
        age: int = 30,
        phone_number: str = "9999999999",
        monthly_salary: Decimal = Decimal("50000"),
        approved_limit: Decimal = Decimal("1800000"),
        current_debt: Decimal = Decimal("0"),
    ) -> Customer:
        kwargs = dict(
            first_name=first_name,
            last_name=last_name,
            age=age,
            phone_number=phone_number,
            monthly_salary=monthly_salary,
            approved_limit=approved_limit,
            current_debt=current_debt,
        )
        if customer_id is None:
            return Customer.objects.create(**kwargs)
        return Customer.objects.create(customer_id=customer_id, **kwargs)

    def create_loan(
        self,
        *,
        customer: Customer,
        loan_id: int | None = None,
        loan_amount: Decimal = Decimal("100000"),
        tenure: int = 12,
        interest_rate: Decimal = Decimal("12.5"),
        emis_paid_on_time: int = 0,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Loan:
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today() + timedelta(days=tenure * 30)

        monthly = Decimal(
            str(calculate_monthly_installment(float(loan_amount), float(interest_rate), tenure))
        )

        kwargs = dict(
            customer=customer,
            loan_amount=loan_amount,
            tenure=tenure,
            interest_rate=interest_rate,
            monthly_repayment=monthly,
            emis_paid_on_time=emis_paid_on_time,
            start_date=start_date,
            end_date=end_date,
        )
        if loan_id is None:
            return Loan.objects.create(**kwargs)
        return Loan.objects.create(loan_id=loan_id, **kwargs)


class RegisterTests(BaseAPITestCase):
    def test_register_success(self):
        url = "/api/register"
        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "age": 30,
            "monthly_income": 50000,
            "phone_number": "9876543210",
        }
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("customer_id", resp.data)
        self.assertEqual(resp.data["name"], "John Doe")
        self.assertEqual(resp.data["age"], 30)
        self.assertEqual(resp.data["monthly_income"], 50000.0)
        self.assertEqual(resp.data["phone_number"], "9876543210")
        # 36 * 50000 = 1,800,000 (already nearest lakh)
        self.assertEqual(float(resp.data["approved_limit"]), 1800000.0)

    def test_register_missing_field(self):
        url = "/api/register"
        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "age": 30,
            "monthly_income": 50000,
            # missing phone_number
        }
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", resp.data)

    def test_register_duplicate_phone(self):
        self.create_customer(phone_number="1111111111")
        url = "/api/register"
        payload = {
            "first_name": "Jane",
            "last_name": "Doe",
            "age": 28,
            "monthly_income": 60000,
            "phone_number": "1111111111",
        }
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class EligibilityTests(BaseAPITestCase):
    def test_check_eligibility_customer_not_found(self):
        url = "/api/check-eligibility"
        payload = {"customer_id": 99999, "loan_amount": 100000, "interest_rate": 12.5, "tenure": 12}
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_check_eligibility_new_customer_default_score_allows(self):
        # New customer has no loans => default score 50 (per utils) => slab requires >12%
        c = self.create_customer(customer_id=1, phone_number="2222222222", monthly_salary=Decimal("50000"))
        url = "/api/check-eligibility"
        payload = {"customer_id": c.customer_id, "loan_amount": 100000, "interest_rate": 13.0, "tenure": 12}
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("approval", resp.data)
        self.assertTrue(resp.data["approval"])

    def test_check_eligibility_rate_too_low_gets_corrected(self):
        # New customer default score 50 => must be > 12.0. Send 8% and expect corrected > 12.
        c = self.create_customer(customer_id=2, phone_number="3333333333", monthly_salary=Decimal("50000"))
        url = "/api/check-eligibility"
        payload = {"customer_id": c.customer_id, "loan_amount": 100000, "interest_rate": 8.0, "tenure": 12}
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["approval"])
        self.assertGreater(resp.data["corrected_interest_rate"], 12.0)
        self.assertGreater(resp.data["monthly_installment"], 0.0)

    def test_check_eligibility_reject_if_total_emi_exceeds_half_salary(self):
        c = self.create_customer(customer_id=3, phone_number="4444444444", monthly_salary=Decimal("10000"))
        # Existing loan with EMI > 50% salary
        self.create_loan(
            customer=c,
            loan_amount=Decimal("500000"),
            tenure=12,
            interest_rate=Decimal("20.0"),
            emis_paid_on_time=0,
        )
        url = "/api/check-eligibility"
        payload = {"customer_id": c.customer_id, "loan_amount": 100000, "interest_rate": 20.0, "tenure": 12}
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["approval"])

    def test_check_eligibility_reject_if_debt_exceeds_approved_limit(self):
        c = self.create_customer(
            customer_id=4,
            phone_number="5555555555",
            monthly_salary=Decimal("50000"),
            approved_limit=Decimal("100000"),
            current_debt=Decimal("200000"),
        )
        url = "/api/check-eligibility"
        payload = {"customer_id": c.customer_id, "loan_amount": 50000, "interest_rate": 20.0, "tenure": 12}
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["approval"])


class CreateLoanTests(BaseAPITestCase):
    def test_create_loan_customer_not_found(self):
        url = "/api/create-loan"
        payload = {"customer_id": 99999, "loan_amount": 100000, "interest_rate": 12.5, "tenure": 12}
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_loan_not_approved_returns_null_loan_id(self):
        c = self.create_customer(customer_id=10, phone_number="6666666666")
        url = "/api/create-loan"
        payload = {"customer_id": c.customer_id, "loan_amount": 100000, "interest_rate": 8.0, "tenure": 12}
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data["loan_id"])
        self.assertFalse(resp.data["loan_approved"])

    def test_create_loan_approved_creates_loan_and_updates_debt(self):
        c = self.create_customer(customer_id=11, phone_number="7777777777", current_debt=Decimal("0"))
        url = "/api/create-loan"
        payload = {"customer_id": c.customer_id, "loan_amount": 100000, "interest_rate": 13.0, "tenure": 12}
        resp = self.client.post(url, data=payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["loan_approved"])
        self.assertIsNotNone(resp.data["loan_id"])

        c.refresh_from_db()
        self.assertEqual(c.current_debt, Decimal("100000"))
        self.assertEqual(Loan.objects.filter(customer=c).count(), 1)


class ViewLoanTests(BaseAPITestCase):
    def test_view_loan_not_found(self):
        url = "/api/view-loan/999999"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_loan_success_schema(self):
        c = self.create_customer(customer_id=20, phone_number="8888888888")
        loan = self.create_loan(customer=c, loan_id=12345)
        url = f"/api/view-loan/{loan.loan_id}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["loan_id"], loan.loan_id)
        self.assertIn("customer", resp.data)
        self.assertIn("monthly_installment", resp.data)
        self.assertEqual(resp.data["customer"]["customer_id"], c.customer_id)


class ViewCustomerLoansTests(BaseAPITestCase):
    def test_view_customer_loans_customer_not_found(self):
        url = "/api/view-loans/999999"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_view_customer_loans_list_and_repayments_left(self):
        c = self.create_customer(customer_id=30, phone_number="1212121212")
        loan1 = self.create_loan(customer=c, loan_id=1, tenure=12, emis_paid_on_time=3)
        loan2 = self.create_loan(customer=c, loan_id=2, tenure=6, emis_paid_on_time=6)

        url = f"/api/view-loans/{c.customer_id}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)
        self.assertEqual(len(resp.data), 2)

        # Ensure repayments_left reflects model property
        items = {item["loan_id"]: item for item in resp.data}
        self.assertEqual(items[loan1.loan_id]["repayments_left"], 9)
        self.assertEqual(items[loan2.loan_id]["repayments_left"], 0)


