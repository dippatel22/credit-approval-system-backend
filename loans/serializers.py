from rest_framework import serializers
from .models import Customer, Loan
from decimal import Decimal
import math


class CustomerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    monthly_income = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['customer_id', 'name', 'age', 'monthly_income', 'approved_limit', 'phone_number']

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_monthly_income(self, obj):
        return float(obj.monthly_salary)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['approved_limit'] = float(instance.approved_limit)
        return data


class LoanEligibilityRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField(min_value=0)
    interest_rate = serializers.FloatField(min_value=0)
    tenure = serializers.IntegerField(min_value=1)


class LoanEligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.FloatField()
    corrected_interest_rate = serializers.FloatField()
    tenure = serializers.IntegerField()
    monthly_installment = serializers.FloatField()


class CreateLoanRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField(min_value=0)
    interest_rate = serializers.FloatField(min_value=0)
    tenure = serializers.IntegerField(min_value=1)


class CreateLoanResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.FloatField()


class CustomerDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['customer_id', 'first_name', 'last_name', 'phone_number', 'age']


class LoanDetailSerializer(serializers.ModelSerializer):
    customer = CustomerDetailSerializer()
    monthly_installment = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = ['loan_id', 'customer', 'loan_amount', 'interest_rate', 'monthly_installment', 'tenure']

    def get_monthly_installment(self, obj):
        return float(obj.monthly_repayment)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['loan_amount'] = float(instance.loan_amount)
        data['interest_rate'] = float(instance.interest_rate)
        return data


class CustomerLoanListSerializer(serializers.ModelSerializer):
    repayments_left = serializers.IntegerField(read_only=True)
    monthly_installment = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = ['loan_id', 'loan_amount', 'interest_rate', 'monthly_installment', 'repayments_left']

    def get_monthly_installment(self, obj):
        return float(obj.monthly_repayment)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['loan_amount'] = float(instance.loan_amount)
        data['interest_rate'] = float(instance.interest_rate)
        data['repayments_left'] = instance.repayments_left
        return data

