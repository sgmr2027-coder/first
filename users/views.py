from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.views import View

from .forms import LoginForm


class LoginView(View):
    """Solo técnicos activos pueden ingresar. Redirección al escáner tras éxito."""
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('operations:scanner')
        return render(request, 'users/login.html', {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            login(request, form.cleaned_data['user'], backend='django.contrib.auth.backends.ModelBackend')
            return redirect('operations:scanner')
        return render(request, 'users/login.html', {'form': form})
