import git
import datetime as dt
import uuid
import sys
import os
import ftplib

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
    list_display = ('profile', 'username', 'url', 'code_link', 'token', 'version_control', 'branch', 'port')
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
    

def uploadThis(ftp, path):
    files = os.listdir(path)
    os.chdir(path)
    for f in files:
        if os.path.isfile(f'{path}/{f}'):
            fh = open(f, 'rb')
            ftp.storbinary('STOR %s' % f, fh)
            fh.close()
        elif os.path.isdir(f'{path}/{f}'):
            try:
                ftp.mkd(f)
            except:
                pass
            ftp.cwd(f)
            uploadThis(ftp, f'{path}/{f}')
    ftp.cwd('..')
    os.chdir('..')
    
    
@admin.action(description='Push selected repositories')
def push_repository(modeladmin, request, queryset):
    for query in queryset:
        if not query.success:
            try:
                
                if query.client_request.version_control.lower() == 'ftp':
                    
                    code_link = query.client_request.code_link
                    username = query.client_request.username
                    token = query.client_request.token
                    branch = query.client_request.branch
                    port = query.client_request.port
                    
                    # create FTP instance 
                    ftp = ftplib.FTP()
                    
                    # connect to ftp server
                    ftp.connect(host=code_link, port=int(port))
                    
                    # Login to server
                    ftp.login(username, token)
                    
                    try:
                        ftp.mkd(branch)
                    except:
                        pass
                    
                    # change to location to source
                    ftp.cwd(branch)
                    
                    uploadThis(ftp, query.repo)
                    
                    ftp.quit()
                    
                    commit_message = f"AI_MODIFIER_{uuid.uuid4().hex}"
                    
                    query.success=True
                    query.error=f'Successfully Pushed comment: {commit_message}'
                
                else:
                    repo = git.Repo(query.repo)
                    repo.git.add(all=True)
                    commit_message = f"AI_MODIFIER_{uuid.uuid4().hex}"
                    repo.index.commit(commit_message)
                    # repo.commit(commit_message)
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
    list_filter = ('client_request', 'success',)
    filter_horizontal =  tuple()
    
    fieldsets = (
        ('Client Details', {'fields': ('client_request',)}),
        ('Repository', {'fields': ('repo', 'success', 'error',)}),
    )
    
    add_fieldsets = (
        ('Client Details', {'fields': ('client_request',)}),
        ('Repository', {'fields': ('repo', 'success', 'error',)}),
    )
