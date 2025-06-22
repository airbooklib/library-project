from django.test import TestCase

from django.test import TestCase
from .models import Book

class BookTestCase(TestCase):
    def setUp(self):
        Book.objects.create(title="کتاب تست", author="نویسنده تست")
    
    def test_book_creation(self):
        book = Book.objects.get(title="کتاب تست")
        self.assertEqual(book.author, "نویسنده تست")
