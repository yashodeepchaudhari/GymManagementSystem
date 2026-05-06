from django import forms
from .models import Contact, Enquiry, Plan, Equipment, Member, Image


def _add_class(widget, klass):
    """Append a CSS class to a widget without nuking existing attrs."""
    existing = widget.attrs.get('class', '')
    widget.attrs['class'] = (existing + ' ' + klass).strip()


class _BootstrapMixin:
    """Auto-apply form-control / form-select to all rendered widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.Select, forms.SelectMultiple, forms.NullBooleanSelect)):
                _add_class(widget, 'form-select')
            elif isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                _add_class(widget, 'form-check-input')
            elif isinstance(widget, (forms.RadioSelect,)):
                pass
            elif isinstance(widget, forms.FileInput):
                _add_class(widget, 'form-control')
            else:
                _add_class(widget, 'form-control')


class ContactFormModelForm(_BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'subject', 'message']


class EnquiryForm(_BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ['name', 'contact', 'email', 'age', 'gender']


class PlanForm(_BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Plan
        fields = ['name', 'amount', 'duration', 'duration_days']


class EquipmentForm(_BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['name', 'price', 'unit', 'date', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }


class MemberForm(_BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'name', 'contact', 'email', 'age', 'gender',
            'plan', 'join_date', 'amount',
            'height_cm', 'weight_kg', 'goal', 'experience', 'diet',
        ]
        widgets = {
            'join_date': forms.DateInput(attrs={'type': 'date'}),
        }


class ImageForm(_BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Image
        fields = '__all__'
        labels = {'photo': ''}
