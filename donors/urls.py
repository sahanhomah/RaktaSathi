from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView

from . import views
from .forms import DonorLoginForm

app_name = 'donors'

urlpatterns = [
    path('register/', views.register_donor, name='register'),
    path('profile/', views.profile, name='profile'),
    path('incoming-requests/', views.incoming_requests, name='incoming_requests'),
    path(
        'login/',
        LoginView.as_view(
            template_name='donors/login.html',
            redirect_authenticated_user=True,
            authentication_form=DonorLoginForm,
        ),
        name='login',
    ),
    path('logout/', LogoutView.as_view(next_page='requests:request'), name='logout'),
]
