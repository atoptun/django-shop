from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import FormView, UpdateView, CreateView, DeleteView

from apps.orders.models import Order
from .forms import RegistrationForm, ProfileForm, AddressForm
from .models import Address


class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("products:list_home")

    def form_valid(self, form: RegistrationForm) -> HttpResponse:
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Account created successfully!")
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, UpdateView):
    template_name = "accounts/profile.html"
    form_class = ProfileForm
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user.profile  # type: ignore[attr-defined]

    def form_valid(self, form: ProfileForm) -> HttpResponse:
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


class OrderHistoryView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "accounts/order_history.html"
    context_object_name = "orders"
    paginate_by = 5

    def get_queryset(self):
        if hasattr(self.request.user, "orders"):
            return self.request.user.orders.all().order_by("-created_at")
        return Order.objects.none()


class AddressListView(LoginRequiredMixin, ListView):
    model = Address
    template_name = "accounts/address_list.html"
    context_object_name = "addresses"
    paginate_by = 5

    def get_queryset(self):
        return Address.objects.filter(profile=self.request.user.profile).order_by("-created_at")


class AddressCreateView(LoginRequiredMixin, CreateView):
    model = Address
    form_class = AddressForm
    template_name = "accounts/address_form.html"

    def form_valid(self, form):
        form.instance.profile = self.request.user.profile
        messages.success(self.request, "Address added successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("accounts:address_list")


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    model = Address
    form_class = AddressForm
    template_name = "accounts/address_form.html"

    def get_queryset(self):
        return Address.objects.filter(profile=self.request.user.profile)

    def form_valid(self, form):
        messages.success(self.request, "Address updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("accounts:address_list")


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    model = Address
    template_name = "accounts/address_confirm_delete.html"

    def get_queryset(self):
        return Address.objects.filter(profile=self.request.user.profile)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Address deleted successfully!")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("accounts:address_list")
