from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'books', views.BookViewSet)
router.register(r'members', views.MemberViewSet)

urlpatterns = [
    path('search/', views.book_search, name='book-search'),
] + router.urls