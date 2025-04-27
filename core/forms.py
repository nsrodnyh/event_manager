from django import forms
from .models import Event, ScheduleItem, Material, Feedback, Registration
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone


# форматы, которые понимают <input type="datetime-local"> и <input type="time">
_DT_FMT  = '%Y-%m-%dT%H:%M'   # 2025-04-27T14:30
_TIME_FMT = '%H:%M'           # 14:30


class EventForm(forms.ModelForm):
    # переопределяем поля, чтобы задать и widget, и input_formats
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'},
            format=_DT_FMT
        ),
        input_formats=[_DT_FMT],
    )
    end_date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'},
            format=_DT_FMT
        ),
        input_formats=[_DT_FMT],
        required=False
    )
    registration_deadline = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'},
            format=_DT_FMT
        ),
        input_formats=[_DT_FMT],
        required=False
    )

    class Meta:
        model  = Event
        fields = ['title', 'description', 'date', 'end_date',
                  'location', 'cover', 'registration_deadline']
        widgets = {
            'title'      : forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'location'   : forms.TextInput(attrs={'class': 'form-control'}),
            'cover'      : forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # если редактируем существующее мероприятие — проставим initial
        if self.instance.pk:
            for fld in ('date', 'end_date', 'registration_deadline'):
                dt = getattr(self.instance, fld)
                if dt:
                    self.fields[fld].initial = timezone.localtime(dt).strftime(_DT_FMT)


class ScheduleItemForm(forms.ModelForm):
    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'},
            format=_DT_FMT
        ),
        input_formats=[_DT_FMT],
    )
    end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'},
            format=_DT_FMT
        ),
        input_formats=[_DT_FMT],
    )

    class Meta:
        model  = ScheduleItem
        fields = ['title', 'description', 'start_time', 'end_time']
        widgets = {
            'title'      : forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['start_time'].initial = (
                timezone.localtime(self.instance.start_time).strftime(_DT_FMT)
            )
            self.fields['end_time'].initial = (
                timezone.localtime(self.instance.end_time).strftime(_DT_FMT)
            )


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['file', 'description']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class PublicRegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ['full_name', 'email', 'phone']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class StyledLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class StyledRegisterForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
