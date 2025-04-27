import os
from django.db.models import Avg
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from .forms import StyledRegisterForm
from django.contrib.auth import login
from .models import Profile, ControllerProfile, Feedback, Material
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Event, ScheduleItem, Registration
from .forms import EventForm, ScheduleItemForm, MaterialForm, FeedbackForm, PublicRegistrationForm
import openpyxl
from django.http import HttpResponse, JsonResponse, Http404
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib.auth.views import LoginView
from babel.dates import format_datetime
from .pdf_fonts import register_dejavu


def index(request):
    return render(request, 'index.html')

def register(request):
    if request.method == 'POST':
        form = StyledRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # создать профиль (если ещё не)
            if not hasattr(user, 'profile'):
                Profile.objects.create(user=user)

            login(request, user)

            # 🎯 Редирект по роли
            if hasattr(user, 'controllerprofile'):
                return redirect('controller_panel')
            elif hasattr(user, 'profile') and user.profile.role == 'organizer':
                return redirect('my_events')
            else:
                return redirect('index')
    else:
        form = StyledRegisterForm()

    return render(request, 'register.html', {'form': form})


@login_required
def event_list(request):
    """
    Организатор -> только свои события.
    Контролёр -> события, к которым привязан.
    Любой другой -> всё (или ничего, если так нужно).
    """
    role = getattr(request.user.profile, 'role', '')

    if role == 'organizer':
        events = Event.objects.filter(created_by=request.user).order_by('-date')
    elif role == 'controller':
        events = Event.objects.filter(controllerprofile__user=request.user).distinct()
    else:
        events = Event.objects.all().order_by('-date')

    return render(request, 'event_list.html', {'events': events})


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if (request.user.profile.role == 'organizer'
            and request.user != event.created_by):
        raise Http404("Мероприятие не найдено")

    is_registered = False
    if request.user.is_authenticated:
        is_registered = Registration.objects.filter(email=request.user.email, event=event).exists()

    feedback_event = event.feedback_set.all()
    avg_event_rating = feedback_event.aggregate(Avg('rating'))['rating__avg']

    activities = event.schedule_items.all()
    feedback_by_activity = {
        activity.id: {
            'activity': activity,
            'feedbacks': activity.feedback_set.all(),
            'avg_rating': activity.feedback_set.aggregate(Avg('rating'))['rating__avg'],
        }
        for activity in activities
    }

    public_link = request.build_absolute_uri(
        reverse('public_register', args=[event.id])
    )

    return render(request, 'event_detail.html', {
        'event': event,
        'is_registered': is_registered,
        'feedback_event': feedback_event,
        'avg_event_rating': avg_event_rating,
        'feedback_by_activity': feedback_by_activity,
        'public_link': public_link,
    })


@login_required
def create_event(request):
    if not request.user.profile.role == 'organizer':
        return redirect('event_list')

    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            return redirect('event_list')
    else:
        form = EventForm()
    return render(request, 'create_event.html', {'form': form})


@login_required
def add_schedule_item(request, event_id):
    event = Event.objects.get(id=event_id)

    if (request.user.profile.role == 'organizer'
            and request.user != event.created_by):
        raise Http404("Мероприятие не найдено")

    if not request.user.profile.role == 'organizer' or event.created_by != request.user:
        return redirect('event_detail', event_id=event_id)

    if request.method == 'POST':
        form = ScheduleItemForm(request.POST)
        if form.is_valid():
            schedule_item = form.save(commit=False)
            schedule_item.event = event
            schedule_item.save()
            return redirect('event_detail', event_id=event_id)
    else:
        form = ScheduleItemForm()

    return render(request, 'add_schedule_item.html', {'form': form, 'event': event})


@login_required
def add_material(request, event_id):
    event = Event.objects.get(id=event_id)

    if (request.user.profile.role == 'organizer'
            and request.user != event.created_by):
        raise Http404("Мероприятие не найдено")

    if not request.user.profile.role == 'organizer' or event.created_by != request.user:
        return redirect('event_detail', event_id=event_id)

    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.event = event
            material.save()
            return redirect('event_detail', event_id=event_id)
    else:
        form = MaterialForm()

    return render(request, 'add_material.html', {'form': form, 'event': event})


@login_required
def register_for_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.user == event.created_by:
        return redirect('event_detail', event_id=event_id)

    Registration.objects.get_or_create(user=request.user, event=event)
    return redirect('event_detail', event_id=event_id)


@login_required
def leave_feedback(request, event_id):
    event = Event.objects.get(id=event_id)

    if event.end_date and timezone.localtime() < event.end_date:
        return render(request, 'feedback_too_early.html', {'event': event})

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.user = request.user
            feedback.event = event
            feedback.save()
            return redirect('event_detail', event_id=event_id)
    else:
        form = FeedbackForm()

    return render(request, 'leave_feedback.html', {'form': form, 'event': event})

@login_required
def view_participants(request, event_id):
    event = Event.objects.get(id=event_id)

    if (request.user.profile.role == 'organizer'
            and request.user != event.created_by):
        raise Http404("Мероприятие не найдено")

    if not request.user.profile.role == 'organizer' or event.created_by != request.user:
        return redirect('event_detail', event_id=event_id)

    registrations = event.registrations.all()

    # Поиск по имени
    search = request.GET.get('search', '')
    if search:
        registrations = registrations.filter(full_name__icontains=search)

    # Фильтр по статусу
    checkin_filter = request.GET.get('checked_in')
    if checkin_filter == 'yes':
        registrations = registrations.filter(checked_in=True)
    elif checkin_filter == 'no':
        registrations = registrations.filter(checked_in=False)

    # Поиск по примечанию
    note_query = request.GET.get('note_contains', '')
    if note_query:
        registrations = registrations.filter(note__icontains=note_query)

    return render(request, 'view_participants.html', {
        'event': event,
        'registrations': registrations,
        'search': search,
        'checkin_filter': checkin_filter,
        'note_query': note_query,
    })


# @require_POST
# @login_required
# def toggle_checkin(request, event_id, registration_id):
#     event = Event.objects.get(id=event_id)
#     if not request.user.profile.role == 'organizer' or event.created_by != request.user:
#         return redirect('event_detail', event_id=event_id)
#
#     registration = Registration.objects.get(event=event, id=registration_id)
#     registration.checked_in = not registration.checked_in
#     registration.save()
#     return redirect('view_participants', event_id=event_id)


@require_POST
@login_required
def toggle_checkin(request, event_id, registration_id):
    event = get_object_or_404(Event, id=event_id)

    # --- доступ разрешён, если ---
    is_organizer = request.user == event.created_by
    is_controller = ControllerProfile.objects.filter(
        user=request.user,
        event=event,
        is_active=True     # не деактивирован
    ).exists()

    if not (is_organizer or is_controller):
        return JsonResponse({'error': 'forbidden'}, status=403)

    # --- меняем отметку ---
    reg = get_object_or_404(Registration, id=registration_id, event=event)
    reg.checked_in = not reg.checked_in
    reg.save(update_fields=['checked_in'])

    return JsonResponse({'checked': reg.checked_in})


@require_POST
@login_required
def update_note(request, event_id, registration_id):
    event = get_object_or_404(Event, id=event_id)

    # доступить может только организатор-создатель
    if request.user != event.created_by or request.user.profile.role != 'organizer':
        return redirect('event_detail', event_id=event_id)

    registration = get_object_or_404(
        Registration,
        id=registration_id,
        event=event
    )

    registration.note = request.POST.get('note', '').strip()
    registration.save(update_fields=['note'])

    return redirect('view_participants', event_id=event_id)


@login_required
def export_participants_xlsx(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.user != event.created_by or request.user.profile.role != 'organizer':
        return redirect('event_detail', event_id=event_id)

    # ❶ без select_related
    registrations = event.registrations.all()

    # --- применяем фильтры, как раньше ---
    search = request.GET.get('search', '')
    if search:
        registrations = registrations.filter(full_name__icontains=search)

    checkin_filter = request.GET.get('checked_in')
    if checkin_filter == 'yes':
        registrations = registrations.filter(checked_in=True)
    elif checkin_filter == 'no':
        registrations = registrations.filter(checked_in=False)

    note_query = request.GET.get('note_contains', '')
    if note_query:
        registrations = registrations.filter(note__icontains=note_query)

    # --- создаём xlsx ---
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Участники"

    ws.append(['ФИО', 'Email', 'Телефон', 'Посетил', 'Примечание'])

    for reg in registrations:
        ws.append([
            reg.full_name,
            reg.email,
            reg.phone,
            'Да' if reg.checked_in else 'Нет',
            reg.note
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"{event.title}_участники.xlsx".replace(" ", "_")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


def public_register(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    submitted = False

    # ⏳ Проверка срока регистрации ДО формы
    if event.registration_deadline and timezone.now() > event.registration_deadline:
        return render(request, 'registration_closed.html', {'event': event})

    local_dt = timezone.localtime(event.date)
    formatted_date = format_datetime(local_dt, "d MMMM y 'в' HH:mm", locale='ru')
    formatted_date = format_datetime(event.date, "d MMMM y 'в' HH:mm", locale='ru')

    if request.method == 'POST':
        form = PublicRegistrationForm(request.POST)
        if form.is_valid():
            registration = form.save(commit=False)
            registration.event = event
            registration.save()

            # 🎟️ Ссылка с токеном
            access_link = request.build_absolute_uri(
                reverse('access_event', kwargs={'access_token': registration.access_token})
            )

            # ✉️ Письмо
            subject = f"Регистрация на мероприятие: {event.title}"
            message = (
                f"Здравствуйте, {registration.full_name}!\n\n"
                f"Вы успешно зарегистрированы на мероприятие «{event.title}».\n"
                f"Дата: {formatted_date}\n\n"
                f"Ссылка для доступа к материалам и расписанию:\n{access_link}\n\n"
                f"Пожалуйста, сохраните эту ссылку — она понадобится вам в день мероприятия.\n\n"
                f"С уважением,\nОрганизаторы мероприятия"
            )

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [registration.email],
                fail_silently=False,
            )

            return redirect(f"{request.path}?submitted=1")
    else:
        form = PublicRegistrationForm()
        submitted = request.GET.get('submitted')

    return render(request, 'public_register.html', {
        'form': form,
        'event': event,
        'submitted': submitted
    })



def access_via_token(request, access_token):
    registration = get_object_or_404(Registration, access_token=access_token)
    event = registration.event
    schedule = event.schedule_items.all()
    materials = event.materials.all()
    now = timezone.localtime()

    # Можем вычислить завершено ли мероприятие
    event_over = event.end_date < timezone.localtime(now)
    can_leave_feedback = (
        event.end_date and timezone.localtime() >= event.end_date
    )

    # ➊ Есть ли уже отзыв от этого участника
    feedback = (
        Feedback.objects.filter(registration=registration,
                                event=event,
                                activity__isnull=True)  # только по мероприятию
        .first()
    )

    activity_feedbacks = []
    for act in schedule:
        fb = Feedback.objects.filter(
            registration=registration,
            activity=act
        ).first()
        activity_feedbacks.append({
            'activity': act,
            'feedback': fb  # None, если ещё не оставляли
        })

        for activity in schedule:
            activity.feedback = (
                Feedback.objects.filter(
                    registration=registration,
                    activity=act
                ).first()
            )

    return render(request, 'access_event.html', {
        'registration': registration,
        'event': event,
        'schedule': schedule,
        'materials': materials,
        'event_over': event_over,
        'now': now,
        'can_leave_feedback': can_leave_feedback,
        'feedback': feedback,
        'activity_feedbacks': activity_feedbacks,
    })


@login_required
def add_material_to_activity(request, event_id, activity_id):
    event = get_object_or_404(Event, id=event_id)
    activity = get_object_or_404(ScheduleItem, id=activity_id, event=event)

    if request.user.profile.role != 'organizer' or event.created_by != request.user:
        return redirect('event_detail', event_id=event.id)

    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.event = event
            material.schedule_item = activity
            material.save()
            return redirect('event_detail', event_id=event.id)
    else:
        form = MaterialForm()

    return render(request, 'add_material_to_activity.html', {
        'form': form,
        'event': event,
        'activity': activity,
    })


def leave_feedback_token(request, access_token, activity_id=None):
    registration = get_object_or_404(Registration, access_token=access_token)
    event = registration.event

    if activity_id:
        activity = get_object_or_404(ScheduleItem, id=activity_id, event=event)
        if activity.end_time >= timezone.localtime():
            return HttpResponse("Оставить отзыв можно только после окончания активности.")
    else:
        if event.date >= timezone.localtime():
            return HttpResponse("Оставить отзыв можно только после окончания мероприятия.")
        activity = None

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.registration = registration
            feedback.event = event if activity is None else None
            feedback.activity = activity
            feedback.save()
            return HttpResponse("Спасибо за ваш отзыв!")
    else:
        form = FeedbackForm()

    return render(request, 'leave_feedback_token.html', {
        'form': form,
        'event': event,
        'activity': activity,
    })


@login_required
def controller_panel(request):
    try:
        profile = request.user.controllerprofile
    except ControllerProfile.DoesNotExist:
        return redirect('index')

    # Автодеактивация если мероприятие прошло
    if profile.event.end_date < timezone.now():
        profile.is_active = False
        profile.save()
        return render(request, 'controller_expired.html')

    if not hasattr(request.user, 'controllerprofile'):
        return HttpResponse("У вас нет доступа к панели контролёра.")

    event = request.user.controllerprofile.event
    registrations = event.registrations.all()

    if request.method == 'POST':
        for reg in registrations:
            checked_in = str(reg.id) in request.POST
            if reg.checked_in != checked_in:
                reg.checked_in = checked_in
                reg.save()
        return redirect('controller_panel')

    return render(request, 'controller_panel.html', {
        'event': event,
        'registrations': registrations,
    })


@login_required
def my_events(request):
    if request.user.profile.role != 'organizer':
        return redirect('event_list')

    events = Event.objects.filter(created_by=request.user)
    return render(request, 'my_events.html', {'events': events})


@login_required
def event_stats(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.user.profile.role != 'organizer' or event.created_by != request.user:
        return redirect('event_detail', event_id=event_id)

    registrations = event.registrations.all()
    total = registrations.count()
    attended = registrations.filter(checked_in=True).count()
    missed = total - attended

    avg_rating = event.feedback_set.aggregate(Avg('rating'))['rating__avg']

    activity_data = []
    for activity in event.schedule_items.all():
        total_feedback = activity.feedback_set.count()
        avg_activity_rating = activity.feedback_set.aggregate(Avg('rating'))['rating__avg']
        activity_data.append({
            'title': activity.title,
            'avg_rating': avg_activity_rating or 0,
            'feedback_count': total_feedback
        })

    return render(request, 'event_stats.html', {
        'event': event,
        'total': total,
        'attended': attended,
        'missed': missed,
        'avg_rating': avg_rating,
        'activity_data': activity_data,
    })


# ---------- PDF рендер ----------
def render_to_pdf(template_src, context):
    register_dejavu()                       # <── регистрируем перед рендером
    html = get_template(template_src).render(context)

    response = HttpResponse(content_type='application/pdf')
    pisa.CreatePDF(html, dest=response, encoding='UTF-8')
    return response


@login_required
def event_stats_pdf(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.user.profile.role != 'organizer' or event.created_by != request.user:
        return redirect('event_detail', event_id=event_id)

    registrations = event.registrations.all()
    total = registrations.count()
    attended = registrations.filter(checked_in=True).count()
    missed = total - attended
    avg_rating = event.feedback_set.aggregate(Avg('rating'))['rating__avg']

    activity_data = []
    for activity in event.schedule_items.all():
        total_feedback = activity.feedback_set.count()
        avg_activity_rating = activity.feedback_set.aggregate(Avg('rating'))['rating__avg']
        activity_data.append({
            'title': activity.title,
            'avg_rating': avg_activity_rating or 0,
            'feedback_count': total_feedback
        })

    context = {
        'event': event,
        'total': total,
        'attended': attended,
        'missed': missed,
        'avg_rating': avg_rating,
        'activity_data': activity_data,
    }

    return render_to_pdf('event_stats_pdf.html', context)


@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if (request.user.profile.role == 'organizer'
            and request.user != event.created_by):
        raise Http404("Мероприятие не найдено")

    if request.user != event.created_by or request.user.profile.role != 'organizer':
        return redirect('event_detail', event_id=event_id)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm(instance=event)

    return render(request, 'edit_event.html', {'form': form, 'event': event})


@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if (request.user.profile.role == 'organizer'
            and request.user != event.created_by):
        raise Http404("Мероприятие не найдено")

    if request.user != event.created_by or request.user.profile.role != 'organizer':
        return redirect('event_detail', event_id=event_id)

    if request.method == 'POST':
        event.delete()
        return redirect('my_events')

    return render(request, 'confirm_delete_event.html', {'event': event})


@login_required
def edit_schedule_item(request, item_id):
    item = get_object_or_404(ScheduleItem, id=item_id)
    event = item.event

    if (request.user.profile.role == 'organizer'
            and request.user != event.created_by):
        raise Http404("Мероприятие не найдено")

    if request.user != event.created_by or request.user.profile.role != 'organizer':
        return redirect('event_detail', event_id=event.id)

    if request.method == 'POST':
        form = ScheduleItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect('event_detail', event_id=event.id)
    else:
        form = ScheduleItemForm(instance=item)

    return render(request, 'edit_schedule_item.html', {
        'form': form,
        'event': event,
        'item': item
    })


@login_required
def delete_schedule_item(request, item_id):
    item = get_object_or_404(ScheduleItem, id=item_id)
    event = item.event

    if (request.user.profile.role == 'organizer'
            and request.user != event.created_by):
        raise Http404("Мероприятие не найдено")

    if request.user != event.created_by or request.user.profile.role != 'organizer':
        return redirect('event_detail', event_id=event.id)

    if request.method == 'POST':
        item.delete()
        return redirect('event_detail', event_id=event.id)

    return render(request, 'confirm_delete_schedule_item.html', {
        'item': item,
        'event': event
    })


class RoleBasedLoginView(LoginView):
    def get_success_url(self):
        user = self.request.user

        # Если у пользователя есть профиль контролёра — он контролёр
        if hasattr(user, 'controllerprofile'):
            return reverse('controller_panel')

        # Если организатор
        if hasattr(user, 'profile') and user.profile.role == 'organizer':
            return reverse('my_events')

        # По умолчанию — на главную
        return reverse('index')


@login_required
def delete_material(request, material_id):
    """
    Удаляет Material (как «общий» так и «по активности»).
    Доступно только организатору-создателю мероприятия.
    """
    material = get_object_or_404(Material, id=material_id)

    # выясняем мероприятие, к которому принадлежит файл
    event = material.event or material.activity.event

    if request.user != event.created_by or request.user.profile.role != 'organizer':
        return redirect('event_detail', event_id=event.id)

    # удаляем сам файл из ФС (если нужно) и запись
    storage, path = material.file.storage, material.file.path
    material.delete()
    try:
        storage.delete(path)          # безопасно: silently ignore absent file
    except Exception:
        pass

    return redirect('event_detail', event_id=event.id)
