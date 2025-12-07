from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse


def login_view(request):
    """Handle user login and redirect to role-based landing page"""
    
    # If already logged in, redirect based on role
    if request.user.is_authenticated:
        return redirect(get_landing_redirect(request.user))
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Authenticate using username
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # Redirect to appropriate landing page
            return redirect(get_landing_redirect(user))
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')


def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


def get_landing_redirect(user):
    """Return the URL to redirect the user to based on their role"""
    
    # Mapping roles to landing page URL names
    role_landing_map = {
        'admin': 'admin_landing',
        'client': 'client_landing',
        'onboarding': 'onboarding_landing',
        'qa': 'qa_landing',
    }
    
    # Get user's role name and return corresponding URL
    role_name = user.role.name if hasattr(user, 'role') else None
    return reverse(role_landing_map.get(role_name, 'login'))