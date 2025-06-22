from django.db.models import Count
from .models import Book

def get_popular_books(limit=10):
    return Book.objects.annotate(
        borrow_count=Count('borrowrecord')
    ).order_by('-borrow_count')[:limit]