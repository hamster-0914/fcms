from datetime import datetime
from io import BytesIO
import json
import os
from xhtml2pdf import pisa
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.core.serializers import serialize
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.db import IntegrityError
from sequences import *
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.http import FileResponse

from fcmsapp.blockchain import *
from fcmsapp.models import *
from fcmsapp.serializers import *

# Create your views here.

def Login(request):
     if request.method == "POST":
          email = request.POST['email']
          password = request.POST['password']
          user = authenticate(request, email=email, password=password)

          if user is not None: 
               # objects is a manager used to create data or retrieve data 
               staff = Staff.objects.get(user=user)
               if user.is_superuser:
                    login(request, user)
                    return redirect('fcmsapp:register-staff')
               elif not staff.is_active:
                    messages.error(request, 'Your account has been terminated')
                    return redirect('fcmsapp:login')
               else:
                    login(request, user)
                    return redirect('fcmsapp:dashboard')
          else:
               messages.error(request, 'Invalid email or password')
               return redirect('fcmsapp:login')
     return render(request, "Login.html")

def Logout(request):
     logout(request)
     return redirect('fcmsapp:login')

# Dashboard
@login_required(login_url='fcmsapp:login')
def Dashboard(request):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     # b if a else c (if a is true, return b, else return c))
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     notifications = Notification.objects.filter(case_team_mapping__staff=currentStaff, is_read=False)
     taskList = Task.objects.filter(case_team_mapping__staff=currentStaff)
     task = []
     count = {
          'New Task': 0,
          'In Progress': 0,
          'Completed': 0,
          'Overdue': 0
     }
     for t in taskList:
          serializer = json.loads(serialize('json', [t]))
          serializer[0]['fields'].update({
               'id': t.id,
               'case_no': t.case_team_mapping.case.case_no,
               'staff_no': t.case_team_mapping.staff.staff_no
          })
          task.append(serializer[0]['fields'])

          if t.status == 'New Task':
               count['New Task'] += 1
          elif t.status == 'In Progress':
               count['In Progress'] += 1
          elif t.status == 'Completed':
               count['Completed'] += 1
          elif t.status == 'Overdue':
               count['Overdue'] += 1
     
     # To filter out the team collaboration
     cases = {}
     # case_team_mapping_id selects the id of the case team mapping of the current staff
     case_team_mapping_id = CaseTeamMapping.objects.filter(staff=currentStaff).values('case__id')
     # getCases selects all the cases object that the current staff is in
     getCases = Case.objects.filter(id__in=case_team_mapping_id)
     for case in getCases:
          # getTeam selects all the staff_no of the staff in the case
          getTeam = CaseTeamMapping.objects.filter(case=case).values('staff__staff_no').exclude(is_head=True)
          getTeamHead = CaseTeamMapping.objects.filter(case=case, is_head=True).values('staff__staff_no')
          # getMembers selects all the staff object of the staff in the case
          members = []
          getMembers = Staff.objects.filter(staff_no__in=getTeam)
          for mem in getMembers:
               serializer = json.loads(serialize('json', [mem]))
               serializer[0]['fields'].update({
                    'id': mem.id,
                    'profile_pic': ProfilePic.objects.get(staff=mem).image.url if ProfilePic.objects.filter(staff=mem) else None
               })
               members.append(serializer[0]['fields'])
          members = Paginator(members, 4)
          getHead = Staff.objects.filter(staff_no__in=getTeamHead)
          # case_no is the key, getMembers is the value
          cases[case.case_no] = {
               'head': getHead,
               'members': members,
          }
     
     # To filter out the high priority task
     case_team_mapping_id = CaseTeamMapping.objects.filter(staff=currentStaff).values('id')
     highPriority = Task.objects.filter(case_team_mapping__id__in=case_team_mapping_id, priority='High')
     
     highPriorityTask = []
     for h in highPriority:
          serializer = json.loads(serialize('json', [h]))
          serializer[0]['fields'].update({
               'id': h.id,
               'case_no': h.case_team_mapping.case.case_no,
               'title': h.title,
               'description': h.description,
               'due_date': h.due_date,
          })
          highPriorityTask.append(serializer[0]['fields'])
     

     dueTask = Task.objects.filter(case_team_mapping__id__in=case_team_mapping_id, due_date__gte=datetime.now().strftime('%Y-%m-%d')).order_by('due_date')[:3]
     dueTaskList = []
     for d in dueTask:
          serializer = json.loads(serialize('json', [d]))
          serializer[0]['fields'].update({
               'id': d.id,
               'case_no': d.case_team_mapping.case.case_no,
               'title': d.title,
               'due_date': datetime.strptime(d.due_date, '%Y-%m-%d').strftime('%d-%b-%Y'),
          })
          dueTaskList.append(serializer[0]['fields'])


     context={
          'task': task,
          'count': count,
          'teammember': cases,
          'currentStaff': currentStaff,
          'highPriorityTask': highPriorityTask,
          'notifications': notifications,
          'dueTask': dueTaskList,
          'currentProfilePic': profilePic if profilePic else None
     }
     return render(request, 'Dashboard.html', context)

def check_in_team(model, staff):
     cases = Case.objects.filter(id__in=CaseTeamMapping.objects.filter(staff=staff).values('case__id'))
     if model == Case:
          return cases
     else:
          return model.objects.filter(case__in=cases)

# Case features
@login_required(login_url='fcmsapp:login')
def CaseManagement(request):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     getCase = check_in_team(Case, currentStaff)
     cases = []
     count = {
          'New Case': 0,
          'In Progress': 0,
          'Completed': 0
     }
     for c in getCase:
          serializer = json.loads(serialize('json', [c]))
          serializer[0]['fields'].update({
               'id': c.id
          })
          cases.append(serializer[0]['fields'])

          if c.status == 'New Case':
               count['New Case'] += 1
          elif c.status == 'In Progress':
               count['In Progress'] += 1
          elif c.status == 'Completed':
               count['Completed'] += 1

     paginator = Paginator(cases, 4)

     context = {
          'cases': paginator,
          'count': count,
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None
     }
     
     if request.method == "POST":
          query = request.POST['search-input'].strip()
          matched_cases = Case.objects.filter(title__icontains=query)
          filtered_cases = []
          for c in matched_cases:
               serializer = json.loads(serialize('json', [c]))
               serializer[0]['fields'].update({
                    'id': c.id
               })
               filtered_cases.append(serializer[0]['fields'])
          filtered_cases = Paginator(filtered_cases, 4)
          context['cases'] = filtered_cases
          context['query'] = query
          return render(request, "Case/CaseManagement.html", context)
     
     return render(request,'Case/CaseManagement.html', context)

@login_required(login_url='fcmsapp:login')
def AddCase(request):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     last_case_sequence = get_last_value('case')
     if last_case_sequence is None:
          next_case_no = "CA00001"
     else:
          next_case_no = "CA" + str(last_case_sequence + 1).zfill(5)

     if request.method == "POST":
          title = request.POST['title']
          description = request.POST['description']
          created_datetime = datetime.now()
          updated_datetime = datetime.now()
          case_type = request.POST['case_type']
          location = request.POST['location']
          priority = request.POST['priority']
          case_no =  "CA" + str(get_next_value('case')).zfill(5)

          new_case = Case.objects.create(
               case_no = case_no,
               title = title,
               description = description,
               status = "New Case",
               created_datetime = created_datetime,
               updated_datetime = updated_datetime,
               case_type = case_type,
               location = location,
               priority = priority
          )
          new_case.save()

          new_case_team_mapping = CaseTeamMapping(
               case=new_case,
               staff=currentStaff,
               is_head=True
          )
          new_case_team_mapping.save()
          
          messages.success(request, 'Case registered successfully')
          return redirect('fcmsapp:case-management')
     
     context = {
          'next_case_no': next_case_no,
          'created_datetime': datetime.strftime(datetime.now().date(), '%d-%b-%Y'),
          'status': 'New Case',
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None
     }
     return render(request, "Case/AddCase.html", context)

@login_required(login_url='fcmsapp:login')
def CaseDetails(request, case_no):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     case = Case.objects.get(case_no=case_no)
     all_evidence_completed = all(evi.status == 'Completed' for evi in Evidence.objects.filter(case=case).exclude(status='Terminated'))
     all_corpse_status = all(corpse.status == 'Completed' for corpse in Corpse.objects.filter(case=case).exclude(status='Terminated'))

     if request.method == 'POST':
          if case.status == 'Terminated':
               messages.error(request, 'Case has already been terminated')
               return redirect('fcmsapp:case-details', case_no=case_no)
          elif case.status == 'Completed':
               messages.error(request, 'Case has already been completed')
               return redirect('fcmsapp:case-details', case_no=case_no)
          
          editMode = request.POST['editMode']
          if editMode == 'False':
               messages.error(request, 'Please click on the edit button to edit the case details')
               return redirect('fcmsapp:case-details', case_no=case_no)
          title = request.POST['title']
          description = request.POST['description']
          status = request.POST['status']
          updated_datetime = datetime.now()
          case_type = request.POST['case_type']
          location = request.POST['location']
          priority = request.POST['priority']

          case.title = title
          case.description = description
          case.status = status
          case.updated_datetime = updated_datetime
          case.case_type = case_type
          case.location = location
          case.priority = priority
          case.save()
          messages.success(request, 'Case updated successfully')
          return redirect('fcmsapp:case-details', case_no=case_no)
     
     serializer = json.loads(serialize('json', [case]))
     serializer[0]['fields'].update({
          'id': case.id,
          'last_updated': datetime.strftime(case.updated_datetime.date(), '%d-%b-%Y'),
     })

     context = {
          'case': serializer[0]['fields'],
          'currentStaff': currentStaff,
          'all_evidence_completed': all_evidence_completed,
          'all_corpse_status': all_corpse_status,
          'currentProfilePic': profilePic if profilePic else None
     }
     return render(request,"Case/CaseDetails.html", context)

@login_required(login_url='fcmsapp:login')
def AddTeam(request, case_no):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     if request.method == "POST":
          selected_staff = request.POST['selected'].split(',') # splt every team member from the string to list
          if currentStaff.staff_no not in selected_staff:
               messages.error(request, 'Please select yourself as a team member')
               return redirect('fcmsapp:add-team', case_no=case_no)
          head = request.POST['head']
          if head == "" :
               messages.error(request, 'Please select a head')
               return redirect('fcmsapp:add-team', case_no=case_no)
          elif len(selected_staff) == 0:
               messages.error(request, 'Please select at least one team member')
               return redirect('fcmsapp:add-team', case_no=case_no)
          
          if head in selected_staff:
               selected_staff.remove(head)
          existing_team = [ctm['staff__staff_no'] for ctm in CaseTeamMapping.objects.filter(case=Case.objects.get(case_no=case_no)).values('staff__staff_no')] 
          # staff__staff_no is a list of staff no from query set
          
          # ctm is a dictionary, so we need to access the staff_no using ctm['staff__staff_no']


          for s in selected_staff:
               staff = Staff.objects.get(staff_no=s)
               new_ctm = None
               if not (staff.staff_no in existing_team):
                    new_ctm = CaseTeamMapping(
                         case=Case.objects.get(case_no=case_no),
                         staff=staff,
                         is_head=False
                    )
                    new_ctm.save()
               else:
                    ctm = CaseTeamMapping.objects.get(case=Case.objects.get(case_no=case_no), staff=staff)
                    ctm.is_head = False
                    ctm.save()

               if new_ctm:
                    new_notification = Notification(
                         case_team_mapping=new_ctm,
                         title='Added to a case team',
                         content='You are added as a member to a new case team: Case {case_no}. Start adding tasks to the case now!'.format(case_no=case_no),
                         created_datetime=datetime.now()
                    )
                    new_notification.save()

               if s in existing_team:
                    existing_team.remove(s)

          staff = Staff.objects.get(staff_no=head)
          new_ctm = None
          if not (staff.staff_no in existing_team):
               new_ctm = CaseTeamMapping(
                    case=Case.objects.get(case_no=case_no),
                    staff=staff,
                    is_head=True
               )
               new_ctm.save()
          else:
               ctm = CaseTeamMapping.objects.get(case=Case.objects.get(case_no=case_no), staff=staff)
               ctm.is_head = True
               ctm.save()

          # Receive notification
          if new_ctm:
               new_notification = Notification(
                    case_team_mapping=new_ctm,
                    title='Added to a case team',
                    content='You are added as a head to a new case team: Case {case_no}. Start adding tasks to the case now!'.format(case_no=case_no),
                    created_datetime=datetime.now()
               )
               new_notification.save()
          
          if head in existing_team:
               existing_team.remove(head)

          for rem in existing_team:
               staff = Staff.objects.get(staff_no=rem)
               ctm = CaseTeamMapping.objects.get(case=Case.objects.get(case_no=case_no), staff=staff)
               ntf = Notification.objects.get(case_team_mapping=ctm)
               if not ntf.is_read:
                    ntf.delete()
               ctm.delete()

          messages.success(request, 'Team added successfully')
          return redirect('fcmsapp:case-details', case_no=case_no)
               
     case = Case.objects.get(case_no=case_no)
     user = request.user
     staff = Staff.objects.filter(is_active=True).exclude(role='Admin')
     team = CaseTeamMapping.objects.filter(case=case)
     context = {
          'case': case,
          'staff': staff,
          'currentStaff': currentStaff,
          'team': team if team else None,
          'currentProfilePic': profilePic if profilePic else None
     }

     return render(request, 'Case/AddTeam.html',context)

def TerminateCase(request, case_no):
     case = Case.objects.get(case_no=case_no)
     case.status = 'Terminated'
     case.save()
     messages.success(request, 'Case terminated successfully')
     return redirect('fcmsapp:case-management')

# Evidence features
@login_required(login_url='fcmsapp:login')
def EvidenceManagement(request):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     getEvidence = check_in_team(Evidence, currentStaff)
     evidences=[]
     count = {
          'New Evidence': 0,
          'In Progress': 0,
          'Completed': 0,
     }
     for e in getEvidence:
          serializers = json.loads(serialize('json', [e]))
          serializers[0]['fields'].update({
               'id': e.id,
               'case_no': e.case.case_no
          })
          evidences.append(serializers[0]['fields'])

          if e.status == 'New Evidence':
               count['New Evidence'] += 1
          elif e.status == 'Processing':
               count['In Progress'] += 1
          elif e.status == 'Completed':
               count['Completed'] += 1
               
     paginator = Paginator(evidences, 4)
     context={
          'evidences': paginator,
          'count': count,
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None
     }

     if request.method == "POST":
          query = request.POST['search-input'].strip()
          matched_evidences = Evidence.objects.filter(title__icontains=query)
          filtered_evidences = []
          for e in matched_evidences:
               serializer = json.loads(serialize('json', [e]))
               serializer[0]['fields'].update({
                    'id': e.id,
                    'case_no': e.case.case_no
               })
               filtered_evidences.append(serializer[0]['fields'])
          filtered_evidences = Paginator(filtered_evidences, 4)
          context['evidences'] = filtered_evidences
          context['query'] = query
          return render(request, "Evidence/EvidenceManagement.html", context)
     
     return render(request,"Evidence/EvidenceManagement.html",context)

@login_required(login_url='fcmsapp:login')
def AddEvidence(request, case_no):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     last_evidence_sequence = get_last_value('evidence')
     if last_evidence_sequence is None:
          next_evidence_no = "EVI00001"
     else:
          next_evidence_no = "EVI" + str(last_evidence_sequence + 1).zfill(5)

     case = Case.objects.get(case_no=case_no)
     if request.method == "POST":
          title = request.POST['title']
          evidence_no = "EVI" + str(get_next_value('evidence')).zfill(5)
          evidence_type = request.POST['evidence_type']
          description = request.POST['description']
          created_datetime = datetime.now()
          updated_datetime = datetime.now()
          collection_datetime = request.POST['collection_datetime']
          collection_method = request.POST['collection_method']
          collection_location = request.POST['collection_location']
          priority = request.POST['priority']

          new_evidence = Evidence(
               title=title,
               evidence_no=evidence_no,
               case=case,
               description=description,
               evidence_type=evidence_type,
               created_datetime=created_datetime,
               updated_datetime=updated_datetime,
               collection_datetime=collection_datetime,
               collection_location=collection_location,
               collection_method=collection_method,
               priority=priority,
               status='New Evidence'
          )
          new_evidence.save()

          image = request.POST.get('filename', None)
          
          if image:
               path = os.path.join(settings.MEDIA_ROOT, 'Evidence', image) # get the path of the image
               evidence_path = os.path.join(settings.MEDIA_ROOT, 'Evidence', evidence_no) # add a new folder for the evidence folder
               os.makedirs(evidence_path, exist_ok=True) # create the folder if it does not exist

               if not os.path.exists(os.path.join(evidence_path, image)):
                    os.rename(path, os.path.join(evidence_path, image)) # move the image to the new path
               else:
                    messages.error(request, 'A file with the same name already exists') 
                    return redirect('fcmsapp:add-evidence', case_no=case_no)

               new_evidence_image = EvidenceImage(
                    evidence=new_evidence,
                    image=os.path.join('Evidence', evidence_no, image)
               )
               new_evidence_image.save()

          else:
               messages.error(request, 'Please upload an image')
               return redirect('fcmsapp:add-evidence', case_no=case_no)

          messages.success(request, 'Evidence registered successfully')
          return redirect('fcmsapp:case-details', case_no=case_no)
     
     context = {
          'case': case,
          'created_date': datetime.strftime(datetime.now().date(), '%d-%b-%Y'),
          'next_evidence_no': next_evidence_no,
          'status': 'New Evidence',
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None

     }

     return render(request,"Evidence/AddEvidence.html", context)

def UploadEvidenceImage(request):
     if request.method == 'POST':
          image = request.FILES.get('evidenceImage')
          filename = image.name

          os.makedirs(os.path.join(settings.MEDIA_ROOT, 'Evidence'), exist_ok=True)

          with open(os.path.join(settings.MEDIA_ROOT, 'Evidence', filename), 'wb+') as destination:
               for chunk in image.chunks():
                    destination.write(chunk)
          
          return JsonResponse({'filename': filename})

def RemoveEvidenceImage(request):
     if request.method == 'POST':
          filename = request.POST['filename']
          if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'Evidence', filename)):
               os.remove(os.path.join(settings.MEDIA_ROOT, 'Evidence', filename))
               return JsonResponse({'filename': filename})
          else:
               return JsonResponse({'filename': None})

def get_evidence_blockchain():
    # Go to Blockchain class ("model","name")
    evidence_blockchain = Blockchain(EvidenceBlockData, "Evidence transactions")
    # called object and load the method
    load_error = evidence_blockchain.load_from_db()
    if load_error is not None:
        raise Exception("Blockchain " + evidence_blockchain.name + " load error at block " + str(load_error))
    else:
        print("Blockchain " + evidence_blockchain.name + " loaded successfully")
    return evidence_blockchain

@login_required(login_url='fcmsapp:login')
def EvidenceDetails(request,evidence_no):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     evidence = Evidence.objects.get(evidence_no=evidence_no)
     analysis_status = AnalysisResult.objects.filter(evidence=evidence).values('analysis_status')
     case_status = evidence.case.status

     # go to model to validate the permission
     has_permission = currentStaff.validate_permissions('Evidence transactions')
     # if true 
     if has_permission:
          blockchain = get_evidence_blockchain()
          has_custody = False
          for block in reversed(blockchain.chain):
               if block.data['evidence_no'] == evidence_no:
                    if block.data['staff_no'] == currentStaff.staff_no:
                         has_custody = True
                    break
     else:
          messages.error(request, 'You do not have permission to view this evidence')
          return redirect('fcmsapp:evidence-management')
     
     if request.method == 'POST':
          editMode = request.POST['editMode']
          if evidence.status == 'Completed':
               messages.error(request, 'Evidence has already been completed')
               return redirect('fcmsapp:evidence-details', evidence_no=evidence_no)
          
          if case_status == 'Completed':
               messages.error(request, 'Case has already been completed')
               return redirect('fcmsapp:evidence-details', evidence_no=evidence_no)
          
          if evidence.status == 'Terminated':
               messages.error(request, 'Evidence has already been terminated')
               return redirect('fcmsapp:evidence-details', evidence_no=evidence_no)

          if case_status == 'Terminated':
               messages.error(request, 'Case has already been terminated')
               return redirect('fcmsapp:evidence-details', evidence_no=evidence_no)
          
          if editMode == 'False':
               messages.error(request, 'Please click on the edit button to edit the evidence details')
               return redirect('fcmsapp:evidence-details', evidence_no=evidence_no)
          
          title = request.POST['title']
          description = request.POST['description']
          evidence_type = request.POST['evidence_type']
          collection_datetime = request.POST['collection_datetime']
          collection_method = request.POST['collection_method']
          collection_location = request.POST['collection_location']
          priority = request.POST['priority']
          status = request.POST['status']
          updated_datetime = datetime.now()

          evidence.title = title
          evidence.description = description
          evidence.evidence_type = evidence_type
          evidence.collection_datetime = collection_datetime
          evidence.collection_method = collection_method
          evidence.collection_location = collection_location
          evidence.priority = priority
          evidence.status = status
          evidence.updated_datetime = updated_datetime
          evidence.save()
          messages.success(request, 'Evidence updated successfully')
          return redirect('fcmsapp:evidence-details', evidence_no=evidence_no)
     
     serializers = json.loads(serialize('json', [evidence]))
     serializers[0]['fields'].update({
          'id': evidence.id,
          'case_no': evidence.case.case_no,
          'last_updated': datetime.strftime(evidence.updated_datetime.date(), '%d-%b-%Y'),
          'image': EvidenceImage.objects.get(evidence=evidence).image.url if EvidenceImage.objects.filter(evidence=evidence) else '-'     
     })
     context={
          'evidence': serializers[0]['fields'],
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None,
          'has_custody': has_custody,
          'case_status': case_status,
          'analysis_status': analysis_status[0]['analysis_status'] if analysis_status else None

     }
     return render(request,"Evidence/EvidenceDetails.html",context)

@login_required(login_url='fcmsapp:login')
def EvidenceResult(request,evidence_no):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     evidence = Evidence.objects.get(evidence_no=evidence_no)
     
     case_status = evidence.case.status

     last_analysis_sequence = get_last_value('analysis')
     if last_analysis_sequence is None:
          next_analysis_no = "ANL00001"
     else:
          next_analysis_no = "ANL" + str(last_analysis_sequence + 1).zfill(5)
     
     evidence = Evidence.objects.get(evidence_no=evidence_no)

     has_permission = currentStaff.validate_permissions('Evidence transactions')
     if has_permission:
          blockchain = get_evidence_blockchain()
          has_custody = False
          for block in reversed(blockchain.chain):
               if block.data['evidence_no'] == evidence_no:
                    if block.data['staff_no'] == currentStaff.staff_no:
                         has_custody = True
                    break
     else:
          messages.error(request, 'You do not have permission to view this evidence')
          return redirect('fcmsapp:evidence-management')
     
     analysis_result = AnalysisResult.objects.get(evidence=evidence) if AnalysisResult.objects.filter(evidence=evidence) else None
     current_analysis_status = analysis_result.analysis_status if analysis_result else None
     if request.method == "POST":
          if  current_analysis_status == 'Completed':
               messages.error(request, 'Analysis has already been completed')
               return redirect('fcmsapp:evidence-result', evidence_no=evidence_no)
          
          if case_status == 'Terminated':
               messages.error(request, 'Case has already been terminated')
               return redirect('fcmsapp:evidence-result', evidence_no=evidence_no)
          
          if evidence.status == 'Terminated':
               messages.error(request, 'Evidence has already been terminated')
               return redirect('fcmsapp:evidence-result', evidence_no=evidence_no)
          
          editMode = request.POST['editMode']
          if editMode == 'False':
               messages.error(request, 'Please click on the edit button to edit the evidence details')
               return redirect('fcmsapp:evidence-result', evidence_no=evidence_no)
          analysis_status = request.POST['analysis_status']
          analysis_techniques = request.POST['analysis_techniques']
          result = request.POST['result']
          created_datetime = datetime.now()
          updated_datetime = datetime.now()

          # existing_analysis_no = [ad['analysis_no'] for ad in AnalysisResult.objects.filter(evidence=evidence).values('analysis_no')]

          if not analysis_result:
               new_analysis_result = AnalysisResult( 
                    analysis_no=next_analysis_no,
                    evidence=evidence,
                    created_datetime=created_datetime,
                    updated_datetime=created_datetime,
                    analysis_techniques=analysis_techniques,
                    analysis_status=analysis_status,
                    result=result
               )
               new_analysis_result.save()
               messages.success(request, 'Analysis result added successfully')
               return redirect('fcmsapp:evidence-result', evidence_no=evidence_no)
          else:
               analysis_result.evidence = evidence
               analysis_result.updated_datetime = updated_datetime
               analysis_result.analysis_techniques = analysis_techniques
               analysis_result.analysis_status = analysis_status
               analysis_result.result = result

               analysis_result.save()
               messages.success(request, 'Analysis result updated successfully')
               return redirect('fcmsapp:evidence-result', evidence_no=evidence_no)

     serializers = json.loads(serialize('json', [evidence]))
     serializers[0]['fields'].update({
          'id': evidence.id,
          'case_no': evidence.case.case_no,
          'analysis_no': analysis_result.analysis_no if analysis_result else next_analysis_no,
          'analysis_techniques': analysis_result.analysis_techniques if analysis_result else "",
          'analysis_status': analysis_result.analysis_status if analysis_result else "",
          'result': analysis_result.result if analysis_result else "-",
          'updated_datetime': datetime.strftime(analysis_result.updated_datetime.date(), '%d-%b-%Y') if analysis_result else "-",
     })

     context={
          user: request.user,
          'analysis_no': analysis_result.analysis_no if analysis_result else next_analysis_no,
          'analysis_techniques': analysis_result.analysis_techniques if analysis_result else "",
          'analysis_status': analysis_result.analysis_status if analysis_result else "",
          'result': analysis_result.result if analysis_result else "",
          'last_updated': datetime.strftime(analysis_result.updated_datetime.date(), '%d-%b-%Y') if analysis_result else "-",
          'next_analysis_no': next_analysis_no,
          'evidence': serializers[0]['fields'],
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None,
          'has_custody': has_custody,
          'case_status': case_status,
     }
     return render(request,"Evidence/EvidenceResult.html",context)

def TerminateEvidence(request, evidence_no):
     evidence = Evidence.objects.get(evidence_no=evidence_no)
     evidence.status = 'Terminated'
     evidence.save()
     messages.success(request, 'Evidence terminated successfully')
     return redirect('fcmsapp:evidence-management')

@login_required(login_url='fcmsapp:login')
def RegisterEvidenceCustody(request, evidence_no, staff_no):
     staff = Staff.objects.get(staff_no=staff_no)
     role = staff.role
     case = Evidence.objects.get(evidence_no=evidence_no).case
     in_team = CaseTeamMapping.objects.filter(case=case, staff=staff).exists()
     if staff.validate_permissions('Evidence transactions') and in_team:
          data = {
               'evidence_no': evidence_no,
               'staff_no': staff_no
          }
          new_evidence_custody = EvidenceBlockData(
               data=data
          )
          new_evidence_custody.save()
          messages.success(request, 'Evidence custody registered successfully')

     else:
          messages.error(request, 'You do not have the permission to register evidence custody for evidence ' + evidence_no)
          
     if role == 'Forensic Investigator':
          return redirect('fcmsapp:evidence-details', evidence_no=evidence_no)
     elif role == 'Chemist':
          return redirect('fcmsapp:evidence-result', evidence_no=evidence_no)


# def Terminate(request, model, entity_no, redirect_page):
#      entity = model.objects.get(entity_no=entity_no)
#      entity.status = 'Terminated'
#      entity.save()
#      messages.success(request, 'Entity terminated successfully')
#      return redirect('fcmsapp:'+ redirect_page)

# Corpse Features
@login_required(login_url='fcmsapp:login')
def CorpseManagement(request):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     getCorpse = check_in_team(Corpse, currentStaff)
     corpse = []
     for c in getCorpse:
          getCorpseInfo = CorpseInfo.objects.get(corpse=c) if CorpseInfo.objects.filter(corpse=c) else None
          serializer = json.loads(serialize('json', [c]))
          serializer[0]['fields'].update({
               'id': c.id,
               'case_no': c.case.case_no,
               'name': getCorpseInfo.name if getCorpseInfo else '-',
               'estimate_age': getCorpseInfo.estimate_age if getCorpseInfo else '-',
               'gender': getCorpseInfo.gender if getCorpseInfo else '-',
               'cause_death': getCorpseInfo.cause_death if getCorpseInfo else '-',
               'condition': getCorpseInfo.condition if getCorpseInfo else '-',
          })
          corpse.append(serializer[0]['fields'])

     paginator = Paginator(corpse, 6)
     context={
          'corpse': paginator,
          'currentStaff': currentStaff,
          'date_of_discovery': datetime.strftime(datetime.now().date(), '%d-%b-%Y'),
          'currentProfilePic': profilePic if profilePic else None
     }

     if request.method == "POST":
          query = request.POST['search-input'].strip()
          matched_corpse = Corpse.objects.filter(case__case_no__icontains=query)
          filtered_corpse = []
          for c in matched_corpse:
               getCorpseInfo = CorpseInfo.objects.get(corpse=c) if CorpseInfo.objects.filter(corpse=c) else None
               serializer = json.loads(serialize('json', [c]))
               serializer[0]['fields'].update({
                    'id': c.id,
                    'case_no': c.case.case_no,
                    'name': getCorpseInfo.name if getCorpseInfo else '-',
                    'estimate_age': getCorpseInfo.estimate_age if getCorpseInfo else '-',
                    'gender': getCorpseInfo.gender if getCorpseInfo else '-',
                    'cause_death': getCorpseInfo.cause_death if getCorpseInfo else '-',
                    'condition': getCorpseInfo.condition if getCorpseInfo else '-',
               })
               filtered_corpse.append(serializer[0]['fields']) 
          filtered_corpse = Paginator(filtered_corpse, 4)
          context['corpse'] = filtered_corpse
          context['query'] = query
          return render(request, "Corpse/CorpseManagement.html", context)

     return render(request,"Corpse/CorpseManagement.html", context)

@login_required(login_url='fcmsapp:login')
def AddCorpse(request, case_no):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     last_corpse_sequence = get_last_value('corpse')
     if last_corpse_sequence is None:
          next_corpse_no = "COP00001"
     else:
          next_corpse_no = "COP" + str(last_corpse_sequence + 1).zfill(5)

     case = Case.objects.get(case_no=case_no)
     staff_involved = CaseTeamMapping.objects.filter(case=case).values('staff__id')
     staff_pathologist = Staff.objects.filter(id__in = staff_involved, role='Pathologist', is_active=True)

     if request.method == "POST":
          corpse_no = "COP" + str(get_next_value('corpse')).zfill(5)
          status = 'New Corpse'
          date_of_discovery = request.POST['date_of_discovery']
          discovery_location = request.POST['discovery_location']
          pathologist_selection = request.POST['pathologist_selection']
          staff_selection = Staff.objects.get(id=pathologist_selection)
          created_datetime = datetime.now()
          updated_datetime = datetime.now()

          new_Corpse = Corpse(
               case = case,
               corpse_no = corpse_no,
               status = status,
               date_of_discovery = date_of_discovery,
               discovery_location   = discovery_location,
               staff = staff_selection,
               created_datetime=created_datetime,
               updated_datetime=updated_datetime
          )
          new_Corpse.save()
          messages.success(request, 'Corpse registered successfully')
          return redirect('fcmsapp:case-details', case_no=case_no)

     context={
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None,
          'pathologist_selection': staff_pathologist,
          'next_corpse_no': next_corpse_no,
          'case': case,
          'date_of_discovery': datetime.strftime(datetime.now().date(), '%d-%b-%Y'),
          'autopsy_date': datetime.strftime(datetime.now().date(), '%d-%b-%Y'),
          'created_datetime': datetime.strftime(datetime.now().date(), '%d-%b-%Y'),
          'staff_pathologist': staff_pathologist,
          'status': 'New Corpse'
     }
     return render(request,"Corpse/AddCorpse.html", context)


def get_corpse_blockchain():
    corpse_blockchain = Blockchain(CorpseBlockData, "Corpse transactions")
    load_error = corpse_blockchain.load_from_db()
    if load_error is not None:
        raise Exception("Blockchain " + corpse_blockchain.name + " load error at block " + str(load_error))
    else:
        print("Blockchain " + corpse_blockchain.name + " loaded successfully")
    return corpse_blockchain

@login_required(login_url='fcmsapp:login')
def CorpseDetails(request, corpse_no):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     corpse = Corpse.objects.get(corpse_no=corpse_no)
     case = corpse.case
     case_status = case.status
     allow_edit = Corpse.objects.get(corpse_no=corpse_no).staff == currentStaff
     corpse_details = CorpseInfo.objects.get(corpse=corpse) if CorpseInfo.objects.filter(corpse=corpse) else None

     has_permission = currentStaff.validate_permissions('Corpse transactions')
     if has_permission:
          blockchain = get_corpse_blockchain()
          has_custody = False
          for block in reversed(blockchain.chain):
               if block.data['corpse_no'] == corpse_no:
                    if block.data['staff_no'] == currentStaff.staff_no:
                         has_custody = True
                    break
     else:
          messages.error(request, 'You do not have permission to view this corpse')
          return redirect('fcmsapp:corpse-management')

     if request.method == 'POST':
          if corpse.status == 'Completed':
               messages.error(request, 'Corpse has already been completed')
               return redirect('fcmsapp:corpse-details', corpse_no=corpse_no)
          
          if case_status == 'Terminated':
               messages.error(request, 'Case has already been terminated')
               return redirect('fcmsapp:corpse-details', corpse_no=corpse_no)
          
          editMode = request.POST['editMode']
          if editMode == 'False':
               messages.error(request, 'Please click on the edit button to edit the corpse details')
               return redirect('fcmsapp:corpse-details', corpse_no=corpse_no)
          
          name = request.POST['name']
          age = request.POST['estimate_age']
          gender = request.POST['gender']
          cause_death = request.POST['cause_death']
          condition = request.POST['condition']
          created_datetime = datetime.now()
          updated_datetime = datetime.now()
          status = request.POST['status']
          
          corpse.status = status
          corpse.save()

          #existing_corpse_details = [ecd['corpse__corpse_no'] for ecd in CorpseInfo.objects.filter(corpse=corpse).values('corpse__corpse_no')]
          
          autopsy_report = request.POST.get('filename', None)

          if autopsy_report:
               path = os.path.join(settings.MEDIA_ROOT, 'AutopsyReport', autopsy_report)
               autopsy_report_path = os.path.join(settings.MEDIA_ROOT, 'AutopsyReport', corpse_no)
               os.makedirs(autopsy_report_path, exist_ok=True)

               if not os.path.exists(os.path.join(autopsy_report_path, autopsy_report)):
                    os.rename(path, os.path.join(autopsy_report_path, autopsy_report))
               else:
                    messages.error(request, 'A file with the same name already exists')
                    return redirect('fcmsapp:corpse-details', corpse_no=corpse_no)

               new_autopsy_report = AutopsyReport(
                    corpse=corpse,
                    pdf=os.path.join('AutopsyReport', corpse_no, autopsy_report)
               )
               new_autopsy_report.save()

          if not corpse_details:
               new_corpse_details = CorpseInfo(
                    corpse = corpse,
                    name = name,
                    estimate_age = age,
                    gender = gender,
                    cause_death = cause_death,
                    condition = condition,
                    updated_datetime=created_datetime
               )
               new_corpse_details.save()

               messages.success(request, 'Corpse updated successfully')
               return redirect('fcmsapp:corpse-details', corpse_no=corpse_no)
          else:
               corpse_details = CorpseInfo.objects.get(corpse=corpse)
               corpse_details.corpse = corpse
               corpse_details.name = name
               corpse_details.estimate_age = age
               corpse_details.gender = gender
               corpse_details.cause_death = cause_death
               corpse_details.condition = condition
               corpse_details.updated_datetime = updated_datetime

               corpse_details.save()
               messages.success(request, 'Corpse details updated successfully')
               return redirect('fcmsapp:corpse-details', corpse_no=corpse_no)

     serializers = json.loads(serialize('json', [corpse]))
     serializers[0]['fields'].update({
          'id': corpse.id,
          'case_no': corpse.case.case_no,
          'staff_name': corpse.staff.name,
          'name': corpse_details.name if corpse_details else '',
          'gender': corpse_details.gender if corpse_details else '',
          'estimate_age': corpse_details.estimate_age if corpse_details else '',
          'cause_death': corpse_details.cause_death if corpse_details else '',
          'condition': corpse_details.condition if corpse_details else '',
          'last_updated': datetime.strftime(corpse_details.updated_datetime.date(), '%d-%b-%Y') if corpse_details else "-",
          'autopsy_report': AutopsyReport.objects.get(corpse=corpse).pdf.url if AutopsyReport.objects.filter(corpse=corpse) else None
     })
     context={
          'corpse': serializers[0]['fields'],
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None,
          'name': corpse_details.name if corpse_details else '',
          'estimate_age': corpse_details.estimate_age if corpse_details else '',
          'cause_death': corpse_details.cause_death if corpse_details else '',
          'condition': corpse_details.condition if corpse_details else '',
          'last_updated': datetime.strftime(corpse_details.updated_datetime.date(), '%d-%b-%Y')  if corpse_details else "-",
          'has_custody': has_custody,
          'allow_edit': allow_edit,
          'case_status': case_status,
     }
     return render(request,"Corpse/CorpseDetails.html",context)

def RegisterCorpseCustody(request, corpse_no, staff_no):
     staff = Staff.objects.get(staff_no=staff_no)
     role = staff.role
     case = Corpse.objects.get(corpse_no=corpse_no).case
     in_team = CaseTeamMapping.objects.filter(case=case, staff=staff).exists()
     if staff.validate_permissions('Corpse transactions') and in_team:
          data = {
               'corpse_no': corpse_no,
               'staff_no': staff_no
          }
          new_corpse_custody = CorpseBlockData(
               data=data
          )
          new_corpse_custody.save()
          messages.success(request, 'Corpse custody registered successfully')

     else:
          messages.error(request, 'You do not have the permission to register corpse custody for corpse ' + corpse_no)
          
     if role == 'Forensic Investigator':
          return redirect('fcmsapp:corpse-details-investigator', corpse_no=corpse_no)
     elif role == 'Pathologist':
          return redirect('fcmsapp:corpse-details', corpse_no=corpse_no)

@login_required(login_url='fcmsapp:login')
def CorpseDetailsInvestigator(request, corpse_no):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     corpse = Corpse.objects.get(corpse_no=corpse_no)
     case = corpse.case
     case_status = case.status
     staff_involved = CaseTeamMapping.objects.filter(case=case).values('staff__id')
     staff_pathologist = Staff.objects.filter(id__in = staff_involved, role='Pathologist', is_active=True)

     has_permission = currentStaff.validate_permissions('Corpse transactions')
     if has_permission:
          blockchain = get_corpse_blockchain()
          has_custody = False
          for block in reversed(blockchain.chain):
               if block.data['corpse_no'] == corpse_no:
                    if block.data['staff_no'] == currentStaff.staff_no:
                         has_custody = True
                    break
     else:
          messages.error(request, 'You do not have permission to view this corpse')
          return redirect('fcmsapp:corpse-management')

     if request.method == 'POST':
          if corpse.status == 'Completed':
               messages.error(request, 'Corpse has already been completed')
               return redirect('fcmsapp:corpse-details-investigator', corpse_no=corpse_no)
          
          if case_status == 'Terminated':
               messages.error(request, 'Case has already been terminated')
               return redirect('fcmsapp:corpse-details-investigator', corpse_no=corpse_no)
          
          editMode = request.POST['editMode']
          if editMode == 'False':
               messages.error(request, 'Please click on the edit button to edit the corpse details')
               return redirect('fcmsapp:corpse-details-investigator', corpse_no=corpse_no)

          
          date_of_discovery = request.POST['date_of_discovery']
          discovery_location = request.POST['discovery_location']
          pathologist_selection = request.POST['pathologist_selection']
          staff_selection = Staff.objects.get(id=pathologist_selection)
          updated_datetime = datetime.now()

          corpse.corpse_no = corpse_no
          corpse.date_of_discovery = date_of_discovery
          corpse.discovery_location = discovery_location
          corpse.updated_datetime = updated_datetime
          corpse.staff = staff_selection
          corpse.save()
          messages.success(request, 'Corpse updated successfully')
          return redirect('fcmsapp:corpse-details-investigator', corpse_no=corpse_no)
     
     serializers = json.loads(serialize('json', [corpse]))
     serializers[0]['fields'].update({
          'id': corpse.id,
          'case_no': corpse.case.case_no,
          'staff_pathologist': staff_pathologist,
          'name': corpse.staff.name,
          'last_updated': datetime.strftime(corpse.updated_datetime.date(), '%d-%b-%Y'),
     })

     context={
          'corpse': serializers[0]['fields'],
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None,
          'staff_pathologist': staff_pathologist,
          'last_updated': datetime.strftime(corpse.updated_datetime.date(), '%d-%b-%Y'),
          'has_custody': has_custody,
          'case_status': case_status,
     }
     return render(request,'Corpse/CorpseDetailsInvestigator.html', context)

def UploadAutopsyReport(request):
     if request.method == 'POST':
          file = request.FILES.get('autopsyReport')
          filename = file.name

          os.makedirs(os.path.join(settings.MEDIA_ROOT, 'AutopsyReport'), exist_ok=True)

          with open(os.path.join(settings.MEDIA_ROOT, 'AutopsyReport', filename), 'wb+') as destination:
               for chunk in file.chunks():
                    destination.write(chunk)
          
          return JsonResponse({'filename': filename})
     
def RemoveAutopsyReport(request):
     if request.method == 'POST':
          filename = request.POST['filename']
          if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'AutopsyReport', filename)):
               os.remove(os.path.join(settings.MEDIA_ROOT, 'AutopsyReport', filename))
               return JsonResponse({'filename': filename})
          else:
               return JsonResponse({'filename': None})

# Task Features
@login_required(login_url='fcmsapp:login')
def AddTask(request):
     notif_id = request.GET.get('notif_id', None)
     case_no = request.GET.get('case_no', None)
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     case_team_mapping_list = CaseTeamMapping.objects.filter(staff=currentStaff)
     case_list = []

     if case_team_mapping_list:
          for ctm in case_team_mapping_list:
               case = Case.objects.get(id=ctm.case.id)
               if case.status != 'Completed' and case.status != 'Terminated':
                    case_list.append(case)

     if notif_id:
          notification = Notification.objects.get(id=notif_id)
          case_no = notification.case_team_mapping.case.case_no

          notification.is_read = True
          notification.save()

          return redirect(reverse('fcmsapp:add-task') + '?case_no=' + case_no)
     context = {
          'case_no': case_no,
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None,
          'case_list': case_list,
          'created_date': datetime.strftime(datetime.now().date(), '%d-%b-%Y'),
          'status': 'New Task'
     }

     if request.method == "POST":
          title = request.POST['title']
          description = request.POST['description']
          due_date = request.POST['duedate']
          status = 'New Task'
          priority = request.POST['priority']
          case_no = request.POST['case_no']

          new_task = Task(
               task_no = "TAS" + str(get_next_value('task')).zfill(5),
               title = title,
               description = description,
               created_datetime = datetime.now(),
               updated_datetime = datetime.now(),
               due_date = due_date,
               status = status,
               priority = priority,
               case_team_mapping = CaseTeamMapping.objects.get(case=Case.objects.get(case_no=case_no), staff=currentStaff)
          )
          new_task.save()
          messages.success(request, 'Task created successfully')
          return redirect('fcmsapp:task-management')

     return render(request,"Task/AddTask.html", context)

@login_required(login_url='fcmsapp:login')
def TaskManagement(request):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     getTasks = Task.objects.filter(case_team_mapping__staff=currentStaff)
     tasks = []
     for t in getTasks:
          if t.due_date < datetime.now().strftime('%Y-%m-%d'):
               t.status = 'Overdue'
               t.save()
          serializer = json.loads(serialize('json', [t]))
          serializer[0]['fields'].update({
               'id': t.id,
               'case_no': t.case_team_mapping.case.case_no,
               'staff_no': t.case_team_mapping.staff.staff_no
          })
          tasks.append(serializer[0]['fields'])
     paginator = Paginator(tasks, 6)
     context={
          'tasks': paginator,
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None
     }
     if request.method == "POST":
          query = request.POST['search-input'].strip()
          matched_cases = Task.objects.filter(title__icontains=query)
          filtered_tasks = []
          for c in matched_cases:
               serializer = json.loads(serialize('json', [c]))
               serializer[0]['fields'].update({
                    'id': c.id,
                    'case_no': t.case_team_mapping.case.case_no,
                    'staff_no': t.case_team_mapping.staff.staff_no
               })
               filtered_tasks.append(serializer[0]['fields'])
          filtered_tasks = Paginator(filtered_tasks, 6)
          context['tasks'] = filtered_tasks
          context['query'] = query
          return render(request, "Task/TaskManagement.html", context)

     return render(request,"Task/TaskManagement.html",context)

@login_required(login_url='fcmsapp:login')
def TaskDetails(request,task_no):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     task = Task.objects.get(task_no=task_no)
     duedateString = task.due_date
     duedate = datetime.strptime(duedateString, '%Y-%m-%d')

     if duedate.date() <= datetime.now().date():
          task.status = 'Overdue'
          task.save()

     case = Case.objects.get(id=task.case_team_mapping.case.id)
     if request.method == "POST":
          if task.status == 'Completed':
               messages.error(request, 'Task has already been completed')
               return redirect('fcmsapp:task-details', task_no=task_no)
          
          status = request.POST.get('status', None)
          statusOverdue = request.POST.get('statusHidden', None)
          if statusOverdue:
               if statusOverdue == 'Overdue':
                    messages.error(request, 'The overdue task is not allowed to modify')
                    return redirect('fcmsapp:task-details', task_no=task_no)
           
          editMode = request.POST['editMode']
          if editMode == 'False':
               messages.error(request, 'Please click on the edit button to edit the task details')
               return redirect('fcmsapp:task-details', task_no=task_no)
          
          title = request.POST['title']
          description = request.POST['description']      
          priority = request.POST['priority']
         
          task.title = title
          task.description = description
          task.priority = priority
          task.status = status
          task.updated_datetime = datetime.now()
          task.save()
          messages.success(request, 'Task updated successfully')
          return redirect('fcmsapp:task-details', task_no=task_no)
     
     serializers = json.loads(serialize('json', [task]))
     serializers[0]['fields'].update({
          'id': task.id,
          'case_no': task.case_team_mapping.case.case_no,
          'staff_no': task.case_team_mapping.staff.staff_no,
          'last_updated': datetime.strftime(task.updated_datetime.date(), '%d-%b-%Y')
     })
     context={
          'task': serializers[0]['fields'],
          'case': case,
          'task': task,
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None,
          'last_updated': datetime.strftime(task.updated_datetime.date(), '%d-%b-%Y')
     }

     return render(request,"Task/TaskDetails.html",context)


# Staff Features
@login_required(login_url='fcmsapp:login')
def RegisterStaff(request):
     # Get the current staff username and role
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     # Autogenerate the staff email according the sequence
     # Use get_last_value instead of get_next_value to check so that 
     # the sequence number wouldn't be used if the registration is cancelled
     last_staff_sequence = get_last_value('staff')
     if last_staff_sequence is None: # First staff
          next_staff_id = "STF00001"
     else:
          next_staff_id = "STF" + str(last_staff_sequence + 1).zfill(5)
     next_staff_email = next_staff_id + '@proofinder.com'

     
     if request.method == "POST":
          name             = request.POST['name']
          gender           = request.POST['gender']
          dob              = request.POST['dob']
          phone_number     = request.POST['phonenumber']
          role             = request.POST['role']
          created_datetime = datetime.now()
          updated_datetime = datetime.now()
          email            = request.POST['email']
          password         = request.POST['password']
          staff_no         = 'STF' + str(get_next_value('staff')).zfill(5)

          image = request.POST.get('filename', None)

          if image:
               path = os.path.join(settings.MEDIA_ROOT, 'ProfilePic', image)
               profile_pic_path = os.path.join(settings.MEDIA_ROOT, 'ProfilePic', staff_no)
               os.makedirs(profile_pic_path, exist_ok=True)

               if not os.path.exists(os.path.join(profile_pic_path, image)):
                    os.rename(path, os.path.join(profile_pic_path, image))
               else:
                    messages.error(request, 'A file with the same name already exists')
                    return redirect('fcmsapp:register-staff')

          try: 
               new_user = CustomUser.objects.create_user(
                    email=email,
                    password=password
               )
          except IntegrityError:
               messages.error(request, 'Email already exists!')

          try:
               new_staff = Staff.objects.create(
                    user=new_user,
                    staff_no=staff_no,
                    name=name,
                    gender=gender,
                    dob=dob,
                    phone_number=phone_number,
                    role=role,
                    created_datetime=created_datetime,
                    updated_datetime=updated_datetime
               )
               new_staff.save()
               

               new_profile_pic = ProfilePic(
                    staff=new_staff,
                    image=os.path.join('ProfilePic', staff_no, image)
               )
               new_profile_pic.save()
               messages.success(request, 'Staff registered successfully')
          except IntegrityError:
               messages.error(request, 'Phone number already exists!')
               return redirect('fcmsapp:register-staff')

          return redirect('fcmsapp:staff-management')
     
     context = {
          'created_datetime': datetime.strftime(datetime.now().date(), '%d-%b-%Y'),
          'next_staff_email': next_staff_email,
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None,  
          'image': ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     }
     return render(request,"Staff/RegisterStaff.html", context)

def UploadProfilePic(request):
     if request.method == 'POST':
          image = request.FILES.get('profilePic') # Get the image from the form
          filename = image.name

          os.makedirs(os.path.join(settings.MEDIA_ROOT, 'ProfilePic'), exist_ok=True) # Create the ProfilePic folder if it doesn't exist

          with open(os.path.join(settings.MEDIA_ROOT, 'ProfilePic', filename), 'wb+') as destination: # Save the image to the ProfilePic folder
               for chunk in image.chunks(): # Split the image into chunks
                    destination.write(chunk)
          
          return JsonResponse({'filename': filename})

def RemoveProfilePic(request):
     if request.method == 'POST':
          filename = request.POST['filename']
          if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'ProfilePic', filename)):
               os.remove(os.path.join(settings.MEDIA_ROOT, 'ProfilePic', filename))
               return JsonResponse({'filename': filename})
          else:
               return JsonResponse({'filename': None})

def DeleteProfilePic(request, staff_no):
     if request.method == 'POST':
          profile_pic = ProfilePic.objects.get(staff__staff_no=staff_no)
          filename = os.path.basename(profile_pic.image.name)
          if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'ProfilePic', staff_no, filename)):
               os.remove(os.path.join(settings.MEDIA_ROOT, 'ProfilePic', staff_no, filename))
               profile_pic.delete()
               
               messages.success(request, 'Profile picture sucessfully removed!')
               return redirect('fcmsapp:staff-details', staff_no=staff_no)
          else:
               messages.error(request, 'Profile picture does not exist!')
               return redirect('fcmsapp:staff-details', staff_no=staff_no)

@login_required(login_url='fcmsapp:login')
def StaffManagement(request):
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     getStaff = Staff.objects.all()
     
     # Group staff by role
     staff = {
          'Investigator': [],
          'Chemist': [],
          'Pathologist': []
     }
     if getStaff:
          for s in getStaff:
               s_user = CustomUser.objects.get(id=s.user.id)
               email = s_user.email
               last_login = s_user.last_login
               serializer = json.loads(serialize('json', [s])) # Convert queryset to json
               serializer[0]['fields'].update({
                    'id': s.id,
                    'email': email,
                    'last_login': last_login
               }) # Add email and last_login to the json
               if s.role == 'Forensic Investigator':
                    staff['Investigator'].append(serializer[0]['fields'])
               elif s.role == 'Chemist':
                    staff['Chemist'].append(serializer[0]['fields'])
               elif s.role == 'Pathologist':
                    staff['Pathologist'].append(serializer[0]['fields'])
     
     for key, value in staff.items():
          staff[key] = Paginator(value, 6) # Paginate the staff list

     context = {
          'page': 'Forensic Investigator',
          'data': staff,
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None
     }

     return render(request,"Staff/StaffManagement.html", context)

@login_required(login_url='fcmsapp:login')
def StaffDetails(request, staff_no):
     # Get the current staff username and role
     user = request.user
     currentStaff = Staff.objects.get(user=user)
     profilePic = ProfilePic.objects.get(staff=currentStaff).image.url if ProfilePic.objects.filter(staff=currentStaff) else None
     staff = Staff.objects.get(staff_no=staff_no)
     staff_user = CustomUser.objects.get(id=staff.user.id)

     if request.method == 'POST':
          editMode = request.POST['editMode']
          if editMode == 'False':
               messages.error(request, 'Please click on the edit toggle button to edit the staff details')
               return redirect('fcmsapp:staff-details', staff_no=staff_no)
          if staff.is_active is not True:
               messages.error(request, 'Staff has already been terminated')
               return redirect('fcmsapp:case-details', staff_no=staff_no)
          name = request.POST['name']
          gender = request.POST['gender']
          dob = request.POST['dob']
          phone_number = request.POST['phonenumber']
          role = request.POST['role']
          updated_datetime = datetime.now()

          try:
               staff.name = name
               staff.gender = gender
               staff.dob = dob
               staff.phone_number = phone_number
               staff.role = role
               staff.updated_datetime = updated_datetime

               staff.save()

               image = request.POST.get('filename', None)

               if image:
                    path = os.path.join(settings.MEDIA_ROOT, 'ProfilePic', image)
                    profile_pic_path = os.path.join(settings.MEDIA_ROOT, 'ProfilePic', staff_no)
                    os.makedirs(profile_pic_path, exist_ok=True)

                    if not os.path.exists(os.path.join(profile_pic_path, image)):
                         os.rename(path, os.path.join(profile_pic_path, image))
                    else:
                         messages.error(request, 'A file with the same name already exists')
                         return redirect('fcmsapp:register-staff')

                    new_profile_pic = ProfilePic(
                         staff=staff,
                         image=os.path.join('ProfilePic', staff_no, image)
                    )
                    new_profile_pic.save()

               messages.success(request, 'Staff details updated successfully')
          except IntegrityError:
               messages.error(request, 'Phone number already exists!')
          return redirect('fcmsapp:staff-management')
     
     serializer = json.loads(serialize('json', [staff]))
     serializer[0]['fields'].update({
          'id': staff.id,
          'email': staff_user.email,
          'is_active': staff.is_active,
          'last_updated': datetime.strftime(staff.updated_datetime.date(), '%d-%b-%Y'),
     })

     context = {
          'staff': serializer[0]['fields'],
          'currentStaff': currentStaff,
          'currentProfilePic': profilePic if profilePic else None,
          'image': ProfilePic.objects.get(staff=staff).image.url if ProfilePic.objects.filter(staff=staff) else None,
     }
     
     return render(request,"Staff/StaffDetails.html", context)

def TerminateStaff(request, staff_no):
     staff = Staff.objects.get(staff_no=staff_no)
     staff.is_active = False
     staff.save()
     messages.success(request, 'Staff terminated successfully')
     return redirect('fcmsapp:staff-management')


def Report(request,evidence_no):
     evidence = Evidence.objects.get(evidence_no=evidence_no)
     analysis_result = AnalysisResult.objects.get(evidence=evidence)
     case_title = evidence.case.title
     case_no = evidence.case.case_no
     show_date = datetime.now()

     serializers = json.loads(serialize('json', [evidence]))
     serializers[0]['fields'].update({
          'id': evidence.id,
          'case_no': case_no,
          'case_title': case_title,
          'created_datetime': datetime.strftime(evidence.created_datetime.date(), '%d-%b-%Y'),
          'collection_datetime': datetime.strptime(evidence.collection_datetime, '%Y-%m-%dT%H:%M').strftime('%d-%b-%Y %H:%M'),
          'analysis_techniques': analysis_result.analysis_techniques,
          'analysis_status': analysis_result.analysis_status,
          'result': analysis_result.result,
          'show_date': datetime.strftime(show_date, '%d-%b-%Y %H:%M'),
     })

     context = {
          'evidence': serializers[0]['fields'],
          'show_date': show_date,
     }


     return render(request,'Report.html', context)