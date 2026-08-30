import os
from typing import Dict, Any

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpRequest
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField

from base.models import BaseModel
from users.constants import AuthProviderType
from users.managers import UserManager


def get_user_photos_dir(instance, filename):
    """
    Get photo's directories.
    """
    f_name, ext = os.path.splitext(filename)
    # Format timestamp to 'YYYY-MM-DD_HH-MM-SS'
    timestamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Create the path
    formatted_email = instance.email.replace('@', '_at_').replace('.', '_dot_')
    return os.path.join("users", "photos", formatted_email, "{}{}".format(timestamp, ext))


class Role(BaseModel):
    """Role model with dynamic permissions"""

    name = models.CharField(max_length=100, unique=True)
    permissions = models.JSONField(default=list, help_text="List of permission strings")
    description = models.TextField(blank=True, help_text="Description of the role")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def add_permission(self, permission):
        """Add a permission to this role"""
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.save()

    def remove_permission(self, permission):
        """Remove a permission from this role"""
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.save()

    def has_permission(self, permission):
        """Check if role has a specific permission"""
        return permission in self.permissions

    def to_dict(self, request: HttpRequest = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "id": self.pk,
        })
        return data

    class Meta:
        db_table = 'roles'


class AuthProvider(BaseModel):
    """Model to store authentication provider configurations"""
    name = models.CharField(max_length=50, unique=True, choices=AuthProviderType.choices)
    display_name = models.CharField(max_length=100, help_text="Human-readable name")
    backend_class = models.CharField(max_length=200, help_text="Python path to backend class")
    config = models.JSONField(default=dict, help_text="Provider-specific configuration")
    is_active = models.BooleanField(default=True)
    allow_registration = models.BooleanField(default=True, help_text="Allow new user registration via this provider")
    priority = models.IntegerField(default=0, help_text="Provider priority (higher = preferred)")

    def __str__(self):
        return f"{self.display_name} ({self.name})"

    def update_config(self, new_config):
        """Update provider configuration"""
        self.config.update(new_config)
        self.save(update_fields=['config'])

    @property
    def user_count(self):
        """Get number of users registered via this provider"""
        return self.user_auth_providers.count()

    class Meta:
        db_table = 'auth_providers'
        ordering = ['-priority', 'name']


class UserAuthProvider(BaseModel):
    """Link users to their authentication providers"""

    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='auth_providers')
    provider = models.ForeignKey(AuthProvider, on_delete=models.CASCADE, related_name='user_auth_providers')
    provider_user_id = models.CharField(max_length=200, help_text="User ID from the provider")
    provider_email = models.EmailField(blank=True, help_text="Email from provider (may differ from user.email)")
    provider_data = models.JSONField(default=dict, help_text="Additional data from provider")
    is_primary = models.BooleanField(default=False, help_text="Primary authentication method for this user")
    last_used = models.DateTimeField(null=True, blank=True, help_text="Last time this provider was used for auth")

    def __str__(self):
        return f"{self.user.email} via {self.provider.name}"

    def mark_as_used(self):
        """Mark this provider as recently used"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])

    def set_as_primary(self):
        """Set this as the primary auth method for the user"""
        # Remove primary flag from other providers for this user
        UserAuthProvider.objects.filter(user=self.user).update(is_primary=False)
        self.is_primary = True
        self.save(update_fields=['is_primary'])

    class Meta:
        db_table = 'user_auth_providers'
        unique_together = ['provider', 'provider_user_id']
        indexes = [
            models.Index(fields=['user', 'provider']),
            models.Index(fields=['provider_user_id']),
            models.Index(fields=['is_primary']),
        ]


class User(AbstractUser, BaseModel):
    """Extended User model with roles and additional fields"""

    # Core fields (matching your schema)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField(null=True, blank=True)
    # Username fields
    preferred_username = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="User's preferred display/friendly name (not used for authentication)"
    )

    # Additional fields
    profile_photo = models.ImageField(upload_to=get_user_photos_dir, null=True, blank=True)
    roles = models.ManyToManyField(Role, related_name='users', blank=True)
    church = models.CharField(max_length=200, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=100, null=True, blank=True)
    emergency_contact_phone = PhoneNumberField(null=True, blank=True)
    emergency_contact_confirmed_at = models.DateTimeField(null=True, blank=True)
    saved_partner = models.JSONField(null=True, blank=True, help_text="{name, gender, traveling_from, dietary}")
    deletion_requested_at = models.DateTimeField(null=True, blank=True, help_text="Kenya DPA deletion request — data purge handled separately, not an immediate wipe")

    # Use email as the unique identifier for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    # Use custom manager
    objects = UserManager()

    def has_permission(self, permission):
        """Check if user has a specific permission through their role"""
        if self.is_superuser:
            return True
        return self.roles.filter(permissions__contains=[permission]).exists()

    def has_any_permission(self, permissions):
        """Check if user has any of the specified permissions"""
        if self.is_superuser:
            return True
        return any(self.has_permission(perm) for perm in permissions)

    def has_all_permissions(self, permissions):
        """Check if user has all of the specified permissions"""
        if self.is_superuser:
            return True
        return all(self.has_permission(perm) for perm in permissions)

    def get_display_name(self):
        """Get user's display name (preferred_username takes priority)"""
        if self.preferred_username:
            return self.preferred_username
        elif self.first_name:
            return self.first_name.strip()
        else:
            return self.username

    def get_full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}".strip()

    def add_role(self, role_name):
        try:
            role = Role.objects.get(name=role_name)
            self.roles.add(role)
        except Role.DoesNotExist:
            raise ValidationError(f"Role '{role_name}' does not exist")

    def remove_role(self, role_name):
        self.roles.filter(name=role_name).delete()

    def set_roles(self, role_names):
        roles = Role.objects.filter(name__in=role_names)
        self.roles.set(roles)

    def get_auth_providers(self):
        """Get all authentication providers for this user"""
        return self.auth_providers.select_related('provider').all()

    def get_primary_auth_provider(self):
        """Get primary authentication provider"""
        return self.auth_providers.filter(is_primary=True).select_related('provider').first()

    def add_auth_provider(self, provider_name, provider_user_id, provider_data=None, is_primary=False):
        """Add an authentication provider to this user"""
        try:
            provider = AuthProvider.objects.get(name=provider_name, is_active=True)
            user_auth_provider, created = UserAuthProvider.objects.get_or_create(
                user=self,
                provider=provider,
                provider_user_id=provider_user_id,
                defaults={
                    'provider_data': provider_data or {},
                    'is_primary': is_primary
                }
            )

            if is_primary:
                user_auth_provider.set_as_primary()

            return user_auth_provider
        except AuthProvider.DoesNotExist:
            raise ValidationError(f"Auth provider '{provider_name}' does not exist or is inactive")

    def remove_auth_provider(self, provider_name):
        """Remove an authentication provider from this user"""
        try:
            self.auth_providers.filter(provider__name=provider_name).delete()
        except UserAuthProvider.DoesNotExist:
            pass

    def deactivate(self):
        """Deactivate user account"""
        self.is_active = False
        self.save(update_fields=['is_active'])

    def activate(self):
        """Activate user account"""
        self.is_active = True
        self.save(update_fields=['is_active'])

    def to_dict(self, request: HttpRequest = None) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "id": self.pk,
            "display_name": self.get_display_name(),
            "roles": list(self.roles.values_list('name', flat=True)),
        })
        return data

    def __str__(self):
        return f"{self.get_display_name()} ({self.email})"

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]
