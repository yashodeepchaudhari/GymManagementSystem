from django.shortcuts import redirect, render
from .models import TeamMember,add_Enquiry,add_Plan,add_Equipment,add_Member,Image  # Make sure to import the TeamMember model
from .forms import ContactFormModelForm,EnquiryForm,PlanForm,EquipmentForm,MemberForm,ImageForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# The home view (already defined)
def home(request):
    # Data for services
    services =  [
    {'count': 1, 'title': 'Personal Training', 'icon': 'bi-activity', 'description': 'Work one-on-one with our expert trainers...'},
    {'count': 2, 'title': 'Group Classes', 'icon': 'bi-person-lines-fill', 'description': 'Join our group fitness classes...'},
    {'count': 3, 'title': 'Yoga', 'icon': 'bi-yoga', 'description': 'Enhance your flexibility and mental well-being with yoga classes...'},
    {'count': 4, 'title': 'Cardio Training', 'icon': 'bi-heart', 'description': 'Boost your stamina with cardio-based exercises...'},
    {'count': 5, 'title': 'Nutrition Counseling', 'icon': 'bi-apple', 'description': 'Get personalized nutrition plans from our expert dieticians...'},
    {'count': 6, 'title': 'Massage Therapy', 'icon': 'bi-hand-thumbs-up', 'description': 'Relax and recover with professional massage therapy...'}
]
    
    # Fetch team members from the database
    team_members = TeamMember.objects.all()

    # Handle form submission (if any)
    if request.method == 'POST':
        form = ContactFormModelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/') # Redirect to success after form submission
    else:
        form = ContactFormModelForm()

    # Return the rendered home page with services, team members, and the form
    return render(request, 'index.html', {
        'services': services,
        'team_members': team_members,
        'form': form
    })

def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")  # Make sure "pass" matches your input name in HTML

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_staff:  # Allow only admin users to log in
                login(request, user)
                return redirect('admin_dashboard')  # Change this to your admin dashboard page
            else:
                messages.error(request, "You are not authorized to access this page.")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "admin_login.html")

def admin_logout(request):
    logout(request)
    return redirect("admin_login")


@login_required(login_url="admin_login")  # Redirect if not logged in
def admin_dashboard(request):
    return render(request, "admin_panel/admin_dashboard.html")  # Show the admin dashboard


@login_required(login_url="admin_login")  # Redirect if not logged in
def admin_about(request):
    return render(request, "admin_panel/admin_about.html") 


@login_required(login_url="admin_login")  # Redirect if not logged in
def admin_contact(request):
    return render(request, "admin_panel/admin_contact.html") 



@login_required(login_url="admin_login")  # Redirect if not logged in
def add_enquiry(request):
    if request.method == 'POST':
        form = EnquiryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('view_enquiry')  # Redirect to a success page
    else:
        form = EnquiryForm()
    
    return render(request, 'admin_panel/add_enquiry.html', {'form': form})


@login_required(login_url="admin_login")  # Redirect if not logged in
def view_enquiry(request):
    enquiries = add_Enquiry.objects.all()  # Fetch all enquiry records
    return render(request, 'admin_panel/view_enquiry.html', {'enquiries': enquiries})


@login_required(login_url="admin_login")  # Redirect if not logged in
def delete_enquiry(request, enquiry_id):
    enquiry = add_Enquiry.objects.get(id=enquiry_id)
    enquiry.delete()
    return redirect('view_enquiry')  # Redirect back to the list


@login_required(login_url="admin_login")  # Redirect if not logged in
def add_plan(request):
    if request.method == "POST":
        form = PlanForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('view_plan')  # Redirect to view plans page
    else:
        form = PlanForm()
    return render(request, 'admin_panel/add_plan.html', {'form': form})


@login_required(login_url="admin_login")  # Redirect if not logged in
def view_plan(request):
    plans = add_Plan.objects.all()
    return render(request, 'admin_panel/view_plan.html', {'plans': plans})


@login_required(login_url="admin_login")  # Redirect if not logged in
def delete_plan(request, plan_id):
    plan = add_Plan.objects.get(id=plan_id)
    plan.delete()
    return redirect('view_plan')


@login_required(login_url="admin_login")  # Redirect if not logged in
def add_equipment(request):
    if request.method == "POST":
        form = EquipmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('view_equipment')
    else:
        form = EquipmentForm()
    return render(request, 'admin_panel/add_equipment.html', {'form': form})


@login_required(login_url="admin_login")  # Redirect if not logged in
def view_equipment(request):
    equipment_list = add_Equipment.objects.all()
    return render(request, 'admin_panel/view_equipment.html', {'equipment_list': equipment_list})


@login_required(login_url="admin_login")  # Redirect if not logged in
def delete_equipment(request, equipment_id):
    equipment = add_Equipment.objects.get(id=equipment_id)
    equipment.delete()
    return redirect('view_equipment')


@login_required(login_url="admin_login")  # Redirect if not logged in
def add_member(request):
    if request.method == "POST":
        form = MemberForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('view_member')
    else:
        form = MemberForm()
    return render(request, 'admin_panel/add_member.html', {'form': form})


@login_required(login_url="admin_login")  # Redirect if not logged in
def view_member(request):
    members = add_Member.objects.all()
    return render(request, 'admin_panel/view_member.html', {'members': members})


@login_required(login_url="admin_login")  # Redirect if not logged in
def delete_member(request, member_id):
    member = add_Member.objects.get(id=member_id)
    member.delete()
       
    return redirect('view_member')


def test(request):
    return render(request,"test.html")


@login_required(login_url="admin_login")  # Redirect if not logged in
def gallery(request):
    if request.method == "POST":
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("gallery")  # Redirect to clear form resubmission

    images = Image.objects.all()
    form = ImageForm()
    return render(request, "admin_panel/gallery.html", {"form": form, "img": images})

def home_gallery(request):
    images = Image.objects.all()
    form = ImageForm()
    return render(request, "home_gallery.html", {"form": form, "img": images})
    



