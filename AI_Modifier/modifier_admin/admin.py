from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from .models import Profile


class UserRegisterForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.fields['password1'].required = False
        self.fields['password2'].required = False

@admin.register(Profile)
class ProfileAdmin(UserAdmin):
    add_form = UserRegisterForm
    search_fields = ('email', 'name',)
    ordering = ('name',)
    list_display = ('name', 'email', 'is_active', 'is_staff', 'is_superuser',)

    fieldsets = (
        (None, {'fields': ('email', 'name', 'password',)}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser')}),
    )

    add_fieldsets = (
      (None, {
          'classes': ('wide', ),
          'fields': ('email', 'name'),
      }),
    )
