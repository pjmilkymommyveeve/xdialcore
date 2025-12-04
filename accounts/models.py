from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Role(models.Model):
    ADMIN = 'admin'
    CLIENT = 'client'
    ONBOARDING = 'onboarding'
    QA = 'qa'
    
    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (CLIENT, 'Client'),
        (ONBOARDING, 'Onboarding'),
        (QA, 'QA'),
    ]
    
    name = models.CharField(max_length=50, unique=True, choices=ROLE_CHOICES)
    
    class Meta:
        db_table = 'roles'
        indexes = [
            models.Index(fields=['name'], name='idx_roles_name'),
        ]
    
    def __str__(self):
        return self.get_name_display()


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, role=None, **extra_fields):
        if not username:
            raise ValueError('Users must have a username')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        if role:
            user.role = role
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        admin_role, _ = Role.objects.get_or_create(name=Role.ADMIN)
        return self.create_user(username, password, role=admin_role, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=100, unique=True)
    role = models.ForeignKey(Role, on_delete=models.RESTRICT, related_name='users')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['username'], name='idx_users_username'),
            models.Index(fields=['role'], name='idx_users_role_id'),
        ]
    
    def __str__(self):
        return self.username
    
    @property
    def is_admin(self):
        return self.role.name == Role.ADMIN
    
    @property
    def is_client(self):
        return self.role.name == Role.CLIENT
    
    @property
    def is_onboarding(self):
        return self.role.name == Role.ONBOARDING
    
    @property
    def is_qa(self):
        return self.role.name == Role.QA

