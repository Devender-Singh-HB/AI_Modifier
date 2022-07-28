from tabnanny import verbose
from django.db import models
from modifier_admin.models import Profile

# Create your models here.
class ClientRequest(models.Model):
    url = models.URLField(verbose_name='URL', unique=True)
    code_link = models.TextField(verbose_name='Code')
    username = models.CharField(max_length=150, verbose_name='Username')
    token = models.CharField(max_length=200, verbose_name='Access Token')
    version_control = models.CharField(max_length=50, verbose_name='Version Control')
    branch = models.CharField(max_length=50, null=True, blank=True, verbose_name='Branch')
    port = models.PositiveIntegerField(default=0, verbose_name='Port')
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='client_request')
    
    def __str__(self):
        return self.url
    
    class Meta:
        verbose_name = "Request"
        verbose_name_plural = "Requests"
    
    
class ChangeRequest(models.Model):
    client_request = models.ForeignKey(ClientRequest, on_delete=models.CASCADE, related_name='change_request', verbose_name='Client')
    repo = models.CharField(max_length=150, verbose_name='Repository')
    success = models.BooleanField(default=False, verbose_name='Pushed')
    error = models.TextField(default='', verbose_name='Message')
    
    def __str__(self):
        return self.repo
    
    class Meta:
        verbose_name = "Change Request"
        verbose_name_plural = "Change Requests"