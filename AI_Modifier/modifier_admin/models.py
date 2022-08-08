import os
# import dotenv

# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail

from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives

from .password import random_password, temp_password
from .manager import CustomProfileManager

# Stores password
temp = temp_password()

# Create your models here.
class Profile(AbstractUser):
    username = models.CharField(max_length = 100, blank = True, null = True, unique = False)
    email = models.EmailField(max_length=250, unique=True)
    name = models.CharField(max_length=50)
    password = models.CharField(max_length=100, default=random_password)
    auto_generated = models.BooleanField(default=False)
    objects = CustomProfileManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"

@receiver(pre_save, sender=settings.AUTH_USER_MODEL)
def add_password(sender, instance, *args, **kwargs):
    
    if not instance.auto_generated:
        password = random_password()
        instance.set_password(password)
        temp.save_password(password)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def send_mail_to_user(sender, instance, created, **kwargs):
    password = temp.get_password
    print(f'\nLogin Credentials\nEmail: {instance.email}\nPassword: {password}') # Display Credentials to console
    if created:
        instance.auto_generated = True
        instance.save()
        
        # Send Email to user
        context = {
                    'user': instance,
                    'password': password,
                }
        
        subject = render_to_string('modifier_admin/subject.txt', context)
        text_message = render_to_string('modifier_admin/user_created.txt', context)
        html_message = render_to_string('modifier_admin/user_created.html', context)
        
        mail = EmailMultiAlternatives(subject=subject, from_email=settings.DEFAULT_FROM_EMAIL,
                             to=[instance.email], body=text_message)
        
        mail.attach_alternative(html_message, "text/html")
        mail.send()
        
        # send_mail(
        #             subject='Welcome to AI Modifier!',
        #             message=html_message,
        #             html_message=html_message,
        #             recipient_list=[instance.email],
        #             from_email=settings.DEFAULT_FROM_EMAIL,
        #             fail_silently=False,
        #         )