import git
import datetime as dt
import uuid
import sys
import os

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from .models import ClientRequest, ChangeRequest

admin.site.unregister(Group)

@admin.register(ClientRequest)
class ClientRequestAdmin(UserAdmin):
    
    search_fields = ('url', 'profile',)
    ordering = ('profile',)
    list_display = ('profile', 'username', 'url', 'code_link', 'token', 'version_control', 'branch')
    list_filter = ('url', 'code_link', 'profile', )
    filter_horizontal =  tuple()
    
    fieldsets = (
        ('Client Details', {'fields': ('profile', 'username',)}),
        ('Code Details', {'fields': ('url', 'code_link', 'token', 'version_control', 'branch')}),
    )
    
    add_fieldsets = (
        ('Client Details', {'fields': ('profile', 'username',)}),
        ('Code Details', {'fields': ('url', 'code_link', 'token', 'version_control', 'branch')}),
    )
    
    
@admin.action(description='Push selected repositories')
def push_repository(modeladmin, request, queryset):
    for query in queryset:
        if not query.success:
            try:
                repo = git.Repo(query.repo)
                repo.git.add(update=True)
                commit_message = f"AI_MODIFIER_{uuid.uuid4().hex}"
                repo.index.commit(commit_message)
                origin = repo.remote(name='origin')
                origin.push()
                
                query.success=True
                query.error=f'Successfully Pushed comment: {commit_message}'
                # print(query.repo)
                
                
            except Exception as e:
                query.update(success=False, error=f'Error: {e}')
            
        query.save()
            
    
@admin.register(ChangeRequest)
class ChangeRequestAdmin(UserAdmin):
    
    actions = [push_repository]
    search_fields = ('repo', 'client_request', 'success', 'error',)
    ordering = ('repo',)
    list_display = ('repo', 'client_request', 'success', 'error',)
    list_filter = ('repo', 'client_request', 'success', 'error',)
    filter_horizontal =  tuple()
    
    fieldsets = (
        ('Client Details', {'fields': ('client_request',)}),
        ('Repository', {'fields': ('repo', 'success', 'error',)}),
    )
    
    add_fieldsets = (
        ('Client Details', {'fields': ('client_request',)}),
        ('Repository', {'fields': ('repo', 'success', 'error',)}),
    )
