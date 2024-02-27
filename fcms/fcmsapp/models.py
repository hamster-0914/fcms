from datetime import datetime
import hashlib
import json
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext as _
from django.db.models import Count
from django.db import models

class CustomUserManager(BaseUserManager):
     def create_user(self, email, password, **extra_fields):
          if not email:
               raise ValueError(_('User must include email'))
          email = self.normalize_email(email)
          user = self.model(email=email, **extra_fields)
          user.set_password(password)
          user.save()
          return user
     
     def create_superuser(self, email, password, **extra_fields):
          extra_fields.setdefault('is_staff', True)
          extra_fields.setdefault('is_superuser', True)
          extra_fields.setdefault('is_active', True)

          if extra_fields.get('is_staff') is not True:
               raise ValueError(_('Superuser must have is_staff=True.'))
          if extra_fields.get('is_superuser') is not True:
               raise ValueError(_('Superuser must have is_superuser=True.'))
          return self.create_user(email, password, **extra_fields)
     
class CustomUser(AbstractUser):
     username = None
     email = models.EmailField(_("email_address"), unique=True)
     
     USERNAME_FIELD = 'email'
     REQUIRED_FIELDS = []

     objects = CustomUserManager()

     def __str__(self):
          return self.email

class Case(models.Model):
     case_no             = models.CharField(blank=False, null=False, max_length=50)
     title               = models.CharField(blank=False, null=False, max_length=300)
     description         = models.CharField(blank=False, null=False, max_length=5000)
     status              = models.CharField(blank=False, null=False, max_length=30)
     created_datetime    = models.DateTimeField(blank=False, null=False)
     updated_datetime    = models.DateTimeField(blank=True, null=True)
     case_type           = models.CharField(blank=False, null=False, max_length=100)
     location            = models.CharField(blank=False, null=False, max_length=500)
     priority            = models.CharField(blank=False, null=False, max_length=30)

class Evidence(models.Model):
     evidence_no         = models.CharField(blank=False, null=False, max_length=50)
     case                = models.ForeignKey(Case, on_delete=models.CASCADE)
     title               = models.CharField(blank=False, null=False, max_length=100)
     description         = models.CharField(blank=True, null=True, max_length=5000)
     evidence_type       = models.CharField(blank=False, null=False, max_length=100)
     status              = models.CharField(blank=False, null=False, max_length=30)
     created_datetime    = models.DateTimeField(blank=False, null=False)
     updated_datetime    = models.DateTimeField(blank=True, null=True)
     collection_datetime = models.CharField(blank=False, null=False, max_length=100)
     collection_location = models.CharField(blank=False, null=False, max_length=500)
     collection_method   = models.CharField(blank=False, null=False, max_length=300)
     priority            = models.CharField(blank=False, null=False, max_length=30)
     # image               = models.FileField(upload_to='Evidence/')

class EvidenceImage(models.Model):
     evidence            = models.ForeignKey(Evidence, on_delete=models.CASCADE)
     image               = models.ImageField(blank=False, null=False)

class AnalysisResult(models.Model):
     analysis_no         = models.CharField(blank=False, null=False, max_length=50)
     evidence            = models.ForeignKey(Evidence, on_delete=models.CASCADE)
     created_datetime    = models.DateTimeField(blank=False, null=False)
     updated_datetime    = models.DateTimeField(blank=True, null=True)
     analysis_techniques = models.CharField(blank=False, null=False, max_length=200)
     analysis_status     = models.CharField(blank=False, null=False, max_length=50)
     result              = models.CharField(blank=False, null=False, max_length=5000)

class Staff(models.Model):
     user                = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
     staff_no            = models.CharField(blank=False, null=False, max_length=10)
     name                = models.CharField(blank=False, null=False, max_length=50)
     gender              = models.CharField(blank=False, null=False, max_length=10)
     dob                 = models.CharField(blank=False, null=False, max_length=20)
     phone_number        = models.CharField(blank=False, null=False, max_length=30, unique=True)
     role                = models.CharField(blank=False, null=False, max_length=30)
     is_active           = models.BooleanField(blank=False, null=False, default=True)
     created_datetime    = models.DateTimeField(blank=False, null=False)
     updated_datetime    = models.DateTimeField(blank=True, null=True)

     def validate_permissions(self, blockchain):
          permissions = {
               # [] means list of name of blockchain
               'Admin': [],
               'Forensic Investigator': ['Evidence transactions', 'Corpse transactions'],
               'Chemist': ['Evidence transactions'],
               'Pathologist': ['Corpse transactions'],
          }
          # self.role means the current staff role, and it track the blockchain name and the current staff role are match with the dictionary
          return blockchain in permissions[self.role]

class ProfilePic(models.Model):
     staff               = models.ForeignKey(Staff, on_delete=models.CASCADE)
     image               = models.ImageField(blank=False, null=False)

class Corpse(models.Model):
     case                = models.ForeignKey(Case, on_delete=models.CASCADE)
     corpse_no           = models.CharField(blank=False, null=False, max_length=50)
     date_of_discovery   = models.CharField(blank=False, null=False, max_length=100)
     discovery_location  = models.CharField(blank=False, null=False, max_length=500)
     created_datetime    = models.DateTimeField(blank=False, null=False)
     updated_datetime    = models.DateTimeField(blank=True, null=True)
     status              = models.CharField(blank=False, null=False, max_length=30)
     staff               = models.ForeignKey(Staff, on_delete=models.CASCADE)
     
class CorpseInfo(models.Model):
     corpse              = models.ForeignKey(Corpse, on_delete=models.CASCADE)
     name                = models.CharField(blank=False, null=False, max_length=50)
     estimate_age        = models.IntegerField(blank=False, null=False)
     gender              = models.CharField(blank=False, null=False, max_length=10)
     cause_death         = models.CharField(blank=False, null=False, max_length=1000)
     condition           = models.CharField(blank=False, null=False, max_length=5000)
     updated_datetime    = models.DateTimeField(blank=True, null=True)
     
class AutopsyReport(models.Model):
     corpse              = models.ForeignKey(Corpse, on_delete=models.CASCADE)
     pdf                 = models.FileField(blank=False, null=False)

class CaseTeamMapping(models.Model):
     case                = models.ForeignKey(Case, on_delete=models.CASCADE)
     staff               = models.ForeignKey(Staff, on_delete=models.CASCADE)
     is_head             = models.BooleanField(blank=False, null=False, default=False)

class Task(models.Model):
     task_no             = models.CharField(blank=False, null=False, max_length=50)
     title               = models.CharField(blank=False, null=False, max_length=100)
     description         = models.CharField(blank=False, null=False, max_length=5000)
     created_datetime    = models.DateTimeField(blank=False, null=False)
     updated_datetime    = models.DateTimeField(blank=True, null=True)
     due_date            = models.CharField(blank=False, null=False, max_length=100)
     status              = models.CharField(blank=False, null=False, max_length=30)
     priority            = models.CharField(blank=False, null=False, max_length=30)
     case_team_mapping   = models.ForeignKey(CaseTeamMapping, on_delete=models.CASCADE)

class Notification(models.Model):
     title               = models.CharField(blank=False, null=False, max_length=100)
     content             = models.CharField(blank=False, null=False, max_length=5000)
     is_read             = models.BooleanField(blank=False, null=False, default=False)
     created_datetime    = models.DateTimeField(blank=False, null=False)
     case_team_mapping   = models.ForeignKey(CaseTeamMapping, on_delete=models.CASCADE)

class EvidenceBlockData(models.Model):
     index               = models.IntegerField(blank=False, null=False)
     timestamp           = models.CharField(blank=False, null=False, max_length=100)
     previous_hash       = models.CharField(blank=False, null=False, max_length=100)
     data                = models.JSONField(blank=False, null=False)
     hash                = models.CharField(max_length=500, editable=False)

     def calculate_hash(self):
          data_string = json.dumps(self.data, sort_keys=True)
          return hashlib.sha256((str(self.timestamp) + str(self.previous_hash) + str(data_string)).encode('utf-8')).hexdigest()
     
     def save(self, *args, **kwargs):
          if not self.pk:
               last_block = self.__class__.objects.order_by('index').last()
               if last_block is None:
                    genesis_data = {"evidence_no": "0", "staff_no": "0"} 
                    genesis_block = EvidenceBlockData(index=0, timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), previous_hash='0', data=genesis_data)
                    genesis_block.hash = genesis_block.calculate_hash()
                    super(EvidenceBlockData, genesis_block).save(*args, **kwargs)

                    self.previous_hash = genesis_block.hash
                    self.index = 1
               else:
                    self.previous_hash = last_block.hash
                    self.index = last_block.index + 1
               self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
               hash = self.calculate_hash()
               self.hash = hash
          super().save(*args, **kwargs)

class CorpseBlockData(models.Model):
     index               = models.IntegerField(blank=False, null=False)
     timestamp           = models.CharField(blank=False, null=False, max_length=100)
     previous_hash       = models.CharField(blank=False, null=False, max_length=100)
     data                = models.JSONField(blank=False, null=False)
     hash                = models.CharField(max_length=500, editable=False)

     def calculate_hash(self):
          data_string = json.dumps(self.data, sort_keys=True)
          return hashlib.sha256((str(self.timestamp) + str(self.previous_hash) + str(data_string)).encode('utf-8')).hexdigest()
     
     def save(self, *args, **kwargs):
          if not self.pk:
               last_block = self.__class__.objects.order_by('index').last()
               if last_block is None:
                    genesis_data = {"corpse_no": "0", "staff_no": "0"} 
                    genesis_block = CorpseBlockData(index=0, timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), previous_hash='0', data=genesis_data)
                    genesis_block.hash = genesis_block.calculate_hash()
                    super(CorpseBlockData, genesis_block).save(*args, **kwargs)

                    self.previous_hash = genesis_block.hash
                    self.index = 1
               else:
                    self.previous_hash = last_block.hash
                    self.index = last_block.index + 1
               self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
               hash = self.calculate_hash()
               self.hash = hash
          super().save(*args, **kwargs)

