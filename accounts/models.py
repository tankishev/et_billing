from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinLengthValidator
from django.db import models


class UserProfile(models.Model):
    """
    UserProfile model represents the profile details associated with a User.
    """

    phone_regex = RegexValidator(
        regex=r'^\+?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    pid_regex = RegexValidator(
        regex=r'^\d{9,13}$',
        message="PID must be 9 to 13 digits"
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    country = models.CharField(validators=[MinLengthValidator(2)], max_length=2, blank=True, null=True)
    pid = models.CharField(max_length=13, validators=[pid_regex], blank=True, null=True)
    phone_number = models.CharField(max_length=16, validators=[phone_regex], blank=True, null=True)
    failed_attempts = models.IntegerField(default=0)
