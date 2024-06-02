from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

urlpatterns = [
    path('', views.index, name='index'),
    path('process_audio/', views.process_audio, name='process_audio'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)