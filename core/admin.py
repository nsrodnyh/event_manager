from django.contrib import admin
from .models import Event, ScheduleItem, Material, Feedback, Profile, ControllerProfile, Registration
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User



@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location', 'created_by')
    search_fields = ('title', 'description', 'location')
    list_filter = ('date',)


@admin.register(ScheduleItem)
class ScheduleItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'start_time', 'end_time')
    list_filter = ('event',)
    search_fields = ('title',)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('event', 'file')
    search_fields = ('event__title',)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    # list_display = ('id', 'registration_full_name', 'rating')

    def registration_full_name(self, obj):
        return obj.registration.full_name
    registration_full_name.short_description = 'Участник'

    list_display = ('id', 'registration_full_name', 'event_or_activity', 'rating')

    def event_or_activity(self, obj):
        return obj.activity.title if obj.activity else f"Мероприятие: {obj.event.title}"

    event_or_activity.short_description = 'Объект отзыва'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user_id','user', 'role')
    list_filter = ('role',)


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'event', 'email', 'phone', 'checked_in', 'created_at')
    list_filter = ('event', 'checked_in', 'created_at')
    search_fields = ('full_name', 'email', 'phone', 'note')
    readonly_fields = ('access_token', 'created_at')


class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff')


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class ControllerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'is_active')
    list_filter = ('is_active',)

admin.site.register(ControllerProfile, ControllerProfileAdmin)