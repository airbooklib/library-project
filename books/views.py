import datetime
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q, Count, F, ExpressionWrapper, DurationField
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, viewsets, filters as drf_filters, status
from django_filters.rest_framework import (
    FilterSet, 
    BooleanFilter, 
    NumberFilter, 
    CharFilter, 
    DjangoFilterBackend
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.views import APIView
from datetime import timedelta
from .models import Book, Member, BorrowRecord, Genre
from .serializers import (
    BookSerializer, 
    MemberSerializer, 
    BorrowRecordSerializer,
    GenreSerializer,
    BookDetailSerializer,
    MemberBorrowHistorySerializer
)


class StandardPagination(PageNumberPagination):
    """
    صفحه‌بندی سفارشی با قابلیت تنظیم اندازه صفحه
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    last_page_strings = ('last',)

    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'page_size': self.get_page_size(self.request),
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'results': data
        })


class IsLibrarian(BasePermission):
    """
    دسترسی فقط برای کتابداران
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Librarians').exists()


class BookFilter(FilterSet):
    """
    فیلترهای پیشرفته برای کتاب‌ها
    """
    min_year = NumberFilter(field_name='publish_year', lookup_expr='gte')
    max_year = NumberFilter(field_name='publish_year', lookup_expr='lte')
    genre = CharFilter(field_name='genre__name', lookup_expr='icontains')
    author = CharFilter(field_name='author', lookup_expr='icontains')
    in_stock = BooleanFilter(method='filter_in_stock')

    class Meta:
        model = Book
        fields = ['genre', 'author', 'min_year', 'max_year', 'in_stock']

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(available__gt=0)
        return queryset

class BookViewSet(viewsets.ModelViewSet):
    """
    مدیریت کامل کتاب‌ها با امکانات پیشرفته
    """
    queryset = Book.objects.annotate(
        borrow_count=Count('borrow_records')
    ).order_by('-borrow_count', 'title')
    serializer_class = BookSerializer
    pagination_class = StandardPagination
    filter_backends = [
        DjangoFilterBackend, 
        drf_filters.SearchFilter,  # استفاده از نام مستعار
        drf_filters.OrderingFilter  # استفاده از نام مستعار
    ]
    filterset_class = BookFilter
    search_fields = ['title', 'author', 'publisher', 'description', 'genre__name']
    ordering_fields = ['title', 'author', 'publish_year', 'created_at', 'borrow_count']
    ordering = ['-created_at']


    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BookDetailSerializer
        return BookSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser() | IsLibrarian()]
        return [AllowAny()]

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """کتاب‌های منتشر شده در 6 ماه اخیر"""
        six_months_ago = timezone.now().date() - timedelta(days=180)
        recent_books = self.get_queryset().filter(
            publish_year__gte=six_months_ago.year
        )[:10]
        serializer = self.get_serializer(recent_books, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """10 کتاب پرطرفدار"""
        popular_books = self.get_queryset()[:10]
        serializer = self.get_serializer(popular_books, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsLibrarian])
    def borrow(self, request, pk=None):
        """امانت گرفتن کتاب"""
        book = self.get_object()
        member_id = request.data.get('member_id')
        
        if not member_id:
            return Response({'error': 'Member ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # بررسی موجودیت کتاب
        if book.available <= 0:
            return Response({'error': 'Book not available'}, status=status.HTTP_400_BAD_REQUEST)
        
        # بررسی سقف امانت عضو
        active_borrows = BorrowRecord.objects.filter(
            member=member, 
            returned=False
        ).count()
        
        max_borrow = 5  # سقف امانت
        if active_borrows >= max_borrow:
            return Response({'error': 'Member has reached borrow limit'}, status=status.HTTP_400_BAD_REQUEST)
        
        # ثبت امانت
        with transaction.atomic():
            borrow_record = BorrowRecord.objects.create(
                book=book,
                member=member,
                borrow_date=timezone.now().date(),
                due_date=timezone.now().date() + timedelta(days=14)
            )
            
            # کاهش موجودی کتاب
            book.available = F('available') - 1
            book.save()
        
        return Response({
            'success': True,
            'borrow_id': borrow_record.id,
            'due_date': borrow_record.due_date
        }, status=status.HTTP_201_CREATED)


class MemberViewSet(viewsets.ModelViewSet):
    """
    مدیریت اعضا با امکانات پیشرفته
    """
    queryset = Member.objects.annotate(
        active_borrows=Count('borrow_records', filter=Q(borrow_records__returned=False)),
        total_borrows=Count('borrow_records')
    ).order_by('-active', 'last_name')

    serializer_class = MemberSerializer
    pagination_class = StandardPagination
    filter_backends = [drf_filters.SearchFilter, drf_filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['first_name', 'last_name', 'email', 'member_id', 'student_id']
    ordering_fields = ['membership_start', 'membership_end', 'last_name', 'total_borrows', 'active']
    ordering = ['-active', 'last_name']
    filterset_fields = ['member_type', 'active']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MemberBorrowHistorySerializer
        return MemberSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy', 'borrow_history']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def perform_destroy(self, instance):
        """غیرفعال کردن عضو به جای حذف فیزیکی"""
        instance.is_active = False
        instance.save()

    @action(detail=True, methods=['get'])
    def borrow_history(self, request, pk=None):
        """تاریخچه امانت‌های عضو"""
        member = self.get_object()
        borrows = BorrowRecord.objects.filter(member=member).order_by('-borrow_date')
        
        page = self.paginate_queryset(borrows)
        if page is not None:
            serializer = BorrowRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = BorrowRecordSerializer(borrows, many=True)
        return Response(serializer.data)


class BorrowRecordViewSet(viewsets.ModelViewSet):
    """
    مدیریت سوابق امانت کتاب
    """
    queryset = BorrowRecord.objects.annotate(
        days_overdue=ExpressionWrapper(
            F('return_date') - F('due_date'),
            output_field=DurationField()
        )
    ).order_by('-borrow_date')
    serializer_class = BorrowRecordSerializer
    pagination_class = StandardPagination
    permission_classes = [IsLibrarian | IsAdminUser]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['book__title', 'member__first_name', 'member__last_name']
    filterset_fields = ['returned', 'book', 'member']

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        """ثبت بازگشت کتاب"""
        record = self.get_object()
        
        if record.returned:
            return Response({'error': 'Book already returned'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # ثبت تاریخ بازگشت
            record.returned = True
            record.return_date = timezone.now().date()
            
            # محاسبه جریمه
            if record.return_date > record.due_date:
                days_late = (record.return_date - record.due_date).days
                record.fine = days_late * 5000  # 5000 تومان برای هر روز تاخیر
            
            record.save()
            
            # افزایش موجودی کتاب
            record.book.available = F('available') + 1
            record.book.save()
        
        return Response({
            'success': True,
            'fine': record.fine
        })


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    نمایش ژانرهای کتاب
    """
    queryset = Genre.objects.annotate(
        book_count=Count('book')
    ).order_by('-book_count', 'name')
    serializer_class = GenreSerializer
    pagination_class = StandardPagination
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


@api_view(['GET'])
@permission_classes([AllowAny])
def book_list_api(request):
    """
    لیست کتاب‌ها برای API ساده
    """
    books = Book.objects.all()
    serializer = BookSerializer(books, many=True)
    return Response(serializer.data)


def book_list(request):
    """نمایش لیست کتاب‌ها در قالب HTML"""
    books = Book.objects.all()
    return render(request, 'books/book_list.html', {'books': books})


def book_detail(request, pk):
    """نمایش جزئیات کتاب در قالب HTML"""
    book = get_object_or_404(Book, pk=pk)
    return render(request, 'books/book_detail.html', {'book': book})


def book_search(request):
    """
    جستجوی پیشرفته کتاب‌ها در قالب HTML
    """
    query = request.GET.get('q', '')
    genre = request.GET.get('genre', '')
    author = request.GET.get('author', '')
    min_year = request.GET.get('min_year', '')
    max_year = request.GET.get('max_year', '')
    in_stock = request.GET.get('in_stock', 'false') == 'true'
    
    books = Book.objects.all()
    
    # فیلترهای جستجو
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(publisher__icontains=query) |
            Q(description__icontains=query)
        ).distinct()
    
    if genre:
        books = books.filter(genre__name__icontains=genre)
    if author:
        books = books.filter(author__icontains=author)
    if min_year:
        books = books.filter(publish_year__gte=min_year)
    if max_year:
        books = books.filter(publish_year__lte=max_year)
    if in_stock:
        books = books.filter(available__gt=0)
    
    # صفحه‌بندی
    paginator = Paginator(books, 10) 
    page = request.GET.get('page', 1)
    
    try:
        books_page = paginator.page(page)
    except PageNotAnInteger:
        books_page = paginator.page(1)
    except EmptyPage:
        books_page = paginator.page(paginator.num_pages)
    
    # آمار جستجو
    stats = {
        'total_books': books.count(),
        'available_books': books.filter(available__gt=0).count(),
        'popular_genres': Genre.objects.annotate(
            book_count=Count('book')
        ).order_by('-book_count')[:5]
    }
    
    return render(request, 'books/search.html', {
        'books': books_page,
        'query': query,
        'filters': {
            'genre': genre,
            'author': author,
            'min_year': min_year,
            'max_year': max_year,
            'in_stock': in_stock
        },
        'pagination': {
            'current_page': books_page.number,
            'total_pages': paginator.num_pages,
            'has_previous': books_page.has_previous(),
            'has_next': books_page.has_next()
        },
        'stats': stats
    })