from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from books.views import BookListAPI, BookViewSet, MemberViewSet, book_search


router = DefaultRouter()
router.register(r'books', BookViewSet, basename='book') 
router.register(r'members', MemberViewSet, basename='member') 

urlpatterns = [

    path('admin/', admin.site.urls),
    

    path('api/', include([
        path('v1/', include(router.urls)),  
        path('v1/books-list/', BookListAPI.as_view(), name='books-list'), 
    ])),
    

    path('search/', book_search, name='book-search'),
    

    path('api/auth/', include('rest_framework.urls', namespace='rest_framework')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)