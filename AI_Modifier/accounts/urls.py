from django.contrib.auth import views as auth_views
from django.urls import path, include
from . import views


# app_name = 'accounts'

urlpatterns = [
    
    path('', 
        views.index, 
        name='home'),
    
    path('', 
        views.index, 
        name='index'),
    
    path('login/', 
        views.signin, 
        name='login'),
    
    path('signout/', 
        views.signout,
        name='signout'),
    
    path('add_request/', 
        views.add_request,
        name='add_request'),
    
    path('change_request/', 
        views.change_request,
        name='change_request'),
    
    path('logout/', 
        auth_views.LogoutView.as_view(template_name='accounts/signin.html'),
        name='logout'),
    
    path('password_change/', 
        auth_views.PasswordChangeView.as_view(template_name='accounts/password_change.html'),
        name='password_change'),
    
     path('password_change/done/', 
         auth_views.PasswordChangeView.as_view(template_name='accounts/password_change_done.html'), 
         name='password_change_done'),
    
    path('password_reset/',
        auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html',
                                             email_template_name='accounts/password_reset_email.html',
                                             subject_template_name='accounts/password_reset_subject.txt'),
        name='password_reset'),

    # path('reset_password/',
    #     views.password_reset_request,
    #     name='password_reset'),
    
    path('password_reset/done/', 
        auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), 
        name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), 
        name='password_reset_confirm'),
    
    path('reset/done/', 
        auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), 
        name='password_reset_complete'),

]