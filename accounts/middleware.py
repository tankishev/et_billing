from django.shortcuts import redirect
from django.urls import reverse


class RequireLoginMiddleware:
    """ Simple middleware to limit access to resources only after authentication """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not request.path.startswith(reverse('login')):
            return redirect('login')
        response = self.get_response(request)
        return response
