from django.shortcuts import render, redirect, reverse
from django.views.generic import TemplateView, ListView, DetailView, FormView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import Cricarcontaform
from .models import Usuario

# Create your views here.

class Homepagelogin(TemplateView):
    template_name = 'login.html'

class Perfil(LoginRequiredMixin, DetailView):
    template_name = 'perfil.html'
    model = Usuario

    def get_success_url(self):
        return reverse('financeiro:financeiro')

class Criarconta(FormView):
    template_name = 'criarconta.html'
    form_class = Cricarcontaform

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('financeiro:financeiro')

class Editarperfil(LoginRequiredMixin, UpdateView):
    template_name = 'editarperfil.html'
    model = Usuario
    fields = ['first_name', 'last_name', 'email', 'cpf']

    def get_success_url(self):
        return reverse('financeiro:financeiro')
