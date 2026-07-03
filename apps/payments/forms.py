from django import forms


class CardPaymentForm(forms.Form):
    card_number = forms.CharField(
        max_length=19,
        label="Card Number",
        widget=forms.TextInput(attrs={"placeholder": "4000 0000 0000 0002", "class": "Input"}),
    )
    cvv = forms.CharField(
        max_length=4,
        label="CVV Code",
        widget=forms.TextInput(attrs={"placeholder": "123", "class": "Input"}),
    )


class PayPalPaymentForm(forms.Form):
    email = forms.EmailField(
        label="PayPal Email Address",
        widget=forms.EmailInput(attrs={"placeholder": "your-email@paypal.com", "class": "Input"}),
    )


class BankTransferPaymentForm(forms.Form):
    sender_name = forms.CharField(
        max_length=100,
        label="Sender Name (for transfer verification)",
        widget=forms.TextInput(attrs={"placeholder": "Jane Doe", "class": "Input"}),
    )


class CashOnDeliveryForm(forms.Form):
    pass


def get_payment_form_class(code: str):
    registry = {
        "debit": CardPaymentForm,
        "wallet": PayPalPaymentForm,
        "bank": BankTransferPaymentForm,
        "cod": CashOnDeliveryForm,
    }
    return registry.get(code.lower(), CardPaymentForm)
