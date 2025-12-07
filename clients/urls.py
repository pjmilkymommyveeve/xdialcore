from django.urls import path
from . import views

urlpatterns = [
    path('landing/', views.client_landing, name='client_landing'),
]