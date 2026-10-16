from django.urls import admin
from django.urls import path, include
from app import views

urlpatterns = [
	path(’admin/’, admin.site.urls),
	path(’app/’, include(’app.urls’)),
	path(’time’, views.time_view, name=’time’),
	path(’sum’, views.sum_view, name=’sum’),
]
