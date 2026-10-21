from django.urls import path

from . import views

app_name = 'listings'

urlpatterns = [
    path('', views.internship_list, name='list'),
    path('internship/<int:pk>/<slug:slug>/', views.internship_detail, name='detail'),
    path('internship/<int:pk>/', views.internship_detail, name='detail_short'),
]
