from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from .forms import UserLoginForm
from .modules import authorise_user

import logging

logger = logging.getLogger('et_billing.accounts.views')


@csrf_protect
@ensure_csrf_cookie
def login_view(request):
    """ Authorise and login user using combination of Django credentials and 2FA authorisation """

    if request.method == 'POST':

        # Extract username and password
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Check if user exists and can be logged in:
        try:
            user = User.objects.get(username=username)

            # User exists, check if user is blocked
            if not user.is_active:
                logger.debug(f'User {username} is suspended')
                error_message = 'Authentication failed or account suspended.'
                return JsonResponse({'success': False, 'error_message': error_message}, status=401)

            # Authenticate users that are not blocked
            authenticated_user = authenticate(request, username=username, password=password)
            if authenticated_user:
                # Clear failed attempts
                if user.profile.failed_attempts != 0:
                    logger.debug(f'Resetting failed attempts count for {username}')
                    user.profile.failed_attempts = 0
                    user.profile.save()

                # Proceed to 2FA authentication
                is_authorised, message = authorise_user(user, timeout=30)
                if is_authorised:
                    login(request, user)
                    logger.debug(f'Login successful for {username}')
                    return JsonResponse({'success': True, 'message': 'Success'})
                else:
                    return JsonResponse({'success': False, 'error_message': message}, status=401)
            else:
                # User was not authenticated
                user.profile.failed_attempts += 1
                user.profile.save()
                logger.debug(
                    f'Failed django authentication for {username}. Failed attempts: {user.profile.failed_attempts}')

                # Suspend user if too many failed attempts
                if user.profile.failed_attempts == 3:
                    user.is_active = False
                    user.save()
                    error_message = 'User account suspended. Contact site administrator.'
                    return JsonResponse({'success': False, 'error_message': error_message}, status=401)

                error_message = f'Authentication failed. Remaining attempts: {3 - user.profile.failed_attempts}'
                return JsonResponse({'success': False, 'error_message': error_message}, status=401)

        except User.DoesNotExist:
            logger.debug(f'User {username} does not exist')
            error_message = 'Authentication failed or user suspended.'
            return JsonResponse({'success': False, 'error_message': error_message}, status=401)
    else:
        return render(request, 'registration/login.html', context={'form': UserLoginForm})
