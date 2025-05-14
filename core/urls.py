from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import RoleBasedLoginView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', RoleBasedLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('events/', views.event_list, name='event_list'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:event_id>/schedule/add/', views.add_schedule_item, name='add_schedule_item'),
    path('events/<int:event_id>/materials/add/', views.add_material, name='add_material'),
    path('events/<int:event_id>/register/', views.register_for_event, name='register_for_event'),
    path('events/<int:event_id>/feedback/', views.leave_feedback, name='leave_feedback'),
    path('events/<int:event_id>/participants/', views.view_participants, name='view_participants'),
    path('events/<int:event_id>/participants/<int:registration_id>/checkin/', views.toggle_checkin,
         name='toggle_checkin'),
    path('events/<int:event_id>/participants/<int:registration_id>/note/', views.update_note, name='update_note'),
    path('events/<int:event_id>/participants/export/', views.export_participants_xlsx, name='export_participants_xlsx'),
    path('register/<int:event_id>/', views.public_register, name='public_register'),
    path('access/<uuid:access_token>/', views.access_via_token, name='access_event'),
    path('events/<int:event_id>/activity/<int:activity_id>/material/add/', views.add_material_to_activity,
         name='add_material_to_activity'),
    path('feedback/<uuid:access_token>/', views.leave_feedback_token, name='leave_feedback_token'),
    path('feedback/<uuid:access_token>/activity/<int:activity_id>/', views.leave_feedback_token,
         name='leave_activity_feedback'),
    path('controller/', views.controller_panel, name='controller_panel'),
    path('my-events/', views.my_events, name='my_events'),
    path('events/<int:event_id>/stats/', views.event_stats, name='event_stats'),
    path('events/<int:event_id>/stats/pdf/', views.event_stats_pdf, name='event_stats_pdf'),
    path('events/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('events/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('schedule/<int:item_id>/edit/', views.edit_schedule_item, name='edit_schedule_item'),
    path('schedule/<int:item_id>/delete/', views.delete_schedule_item, name='delete_schedule_item'),
    path('materials/<int:material_id>/delete/', views.delete_material, name='delete_material'),
    path(
        'feedback/<uuid:access_token>/activity/<int:activity_id>/api/',
        views.leave_activity_feedback_api,
        name='leave_activity_feedback_api'
    ),
    path('register-controller/<uuid:token>/', views.register_controller_by_token, name='register_controller_by_token'),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
