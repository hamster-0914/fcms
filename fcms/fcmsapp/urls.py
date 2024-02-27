from django.urls import path
from fcmsapp.views import *

urlpatterns = [
     path('', Login, name='login'),
     path('logout', Logout, name='logout'),

     # Dashboard
     path('dashboard', Dashboard, name='dashboard'),
     

     # Case features
     path('add-case', AddCase, name='add-case'),
     path('case-management',CaseManagement,name='case-management'),
     path('case-details/<str:case_no>',CaseDetails,name='case-details'),
     path('add-team/<str:case_no>', AddTeam, name='add-team'),
     path('terminate-case/<str:case_no>',TerminateCase,name='terminate-case'),

     # Evidence features
     path('evidence-management',EvidenceManagement,name='evidence-management'),
     path('add-evidence/<str:case_no>',AddEvidence,name='add-evidence'),
     path('evidence-details/<str:evidence_no>',EvidenceDetails,name='evidence-details'),
     path('evidence-result/<str:evidence_no>',EvidenceResult,name='evidence-result'),
     path('upload-evidence-image',UploadEvidenceImage,name='upload-evidence-image'),
     path('remove-evidence-image',RemoveEvidenceImage,name='remove-evidence-image'),
     path('terminate-evidence/<str:evidence_no>',TerminateEvidence,name='terminate-evidence'),
     path('register-evidence-custody/<str:evidence_no>/<str:staff_no>',RegisterEvidenceCustody,name='register-evidence-custody'),
     path('report/<str:evidence_no>', Report, name='report'),

     # Corpse features
     path('corpse-management', CorpseManagement,name='corpse-management'),
     path('add-corpse/<str:case_no>',AddCorpse,name='add-corpse'),
     path('corpse-details/<str:corpse_no>',CorpseDetails,name='corpse-details'),
     path('corpse-details-investigator/<str:corpse_no>',CorpseDetailsInvestigator,name='corpse-details-investigator'),
     path('register-corpse-custody/<str:corpse_no>/<str:staff_no>',RegisterCorpseCustody,name='register-corpse-custody'),
     path('upload-autopsy-report',UploadAutopsyReport,name='upload-autopsy-report'),
     path('remove-autopsy-report',RemoveAutopsyReport,name='remove-autopsy-report'),

     # Task features
     path('add-task',AddTask,name='add-task'),
     path('task-management',TaskManagement ,name='task-management'),
     path('task-details/<str:task_no>',TaskDetails,name='task-details'),

     # Staff features
     path('register-staff',RegisterStaff,name='register-staff'),
     path('upload-profile-pic',UploadProfilePic,name='upload-profile-pic'),
     path('remove-profile-pic',RemoveProfilePic,name='remove-profile-pic'),
     path('delete-profile-pic/<str:staff_no>',DeleteProfilePic,name='delete-profile-pic'),
     path('staff-management',StaffManagement,name='staff-management'),
     path('staff-details/<str:staff_no>',StaffDetails,name='staff-details'),
     path('terminate-staff/<str:staff_no>',TerminateStaff,name='terminate-staff'),
]