from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django import forms


class UserLoginForm(AuthenticationForm):
    """ A simple login form used for authentication of users to the application """

    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)

    username = UsernameField(widget=forms.TextInput(
        attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'id': 'username'}
    ))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'id': 'password',
        }
    ))
