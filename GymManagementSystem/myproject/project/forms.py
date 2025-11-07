# forms.py
from django import forms
from .models import Contact,add_Enquiry,add_Plan,add_Equipment,add_Member,Image # Import the model where you want to store the contact form data

class ContactFormModelForm(forms.ModelForm):
    class Meta:
        model = Contact  # Replace this with your model if you have a custom one
        fields = ['name', 'email', 'subject', 'message']  # Include the fields that the form will take input for



class EnquiryForm(forms.ModelForm):
    class Meta:
        model = add_Enquiry
        fields = ['name', 'contact', 'email', 'age', 'gender']

class PlanForm(forms.ModelForm):
    class Meta:
        model = add_Plan
        fields = ['name', 'amount', 'duration']


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = add_Equipment
        fields = ['name', 'price', 'unit', 'date', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class MemberForm(forms.ModelForm):
    class Meta:
        model = add_Member
        fields = ['name', 'contact', 'email', 'age', 'gender', 'plan', 'join_date', 'expiry_date', 'amount']
        widgets = {
            'join_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

class ImageForm(forms.ModelForm):
 class Meta:
  model = Image
  fields = '__all__'
  labels = {'photo':''}
    
       
