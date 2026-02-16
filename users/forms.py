from django import forms
from django.contrib.auth import authenticate


class LoginForm(forms.Form):
    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    username = forms.CharField(
        label='Usuario',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Usuario',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Contraseña',
            'autocomplete': 'current-password',
        })
    )

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get('username')
        password = cleaned.get('password')
        if username and password:
            user = authenticate(self.request, username=username, password=password)
            if user is None:
                raise forms.ValidationError('Usuario o contraseña incorrectos.')
            if not getattr(user, 'activo', True):
                raise forms.ValidationError('Tu cuenta está desactivada. Contacta al supervisor.')
            cleaned['user'] = user
        return cleaned
