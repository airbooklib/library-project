from rest_framework import serializers
from .models import Book, Member, BorrowRecord, Genre
from django.utils import timezone

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name', 'parent', 'book_count']
        read_only_fields = ['book_count']

class BookSerializer(serializers.ModelSerializer):
    genre = GenreSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'isbn', 'genre', 'quantity', 'available',
            'status', 'status_display', 'description', 'publisher', 'publish_year',
            'cover', 'pages', 'created_at', 'updated_at'
        ]
        read_only_fields = ['available', 'created_at', 'updated_at']

class BookDetailSerializer(BookSerializer):
    borrow_history = serializers.SerializerMethodField()
    
    class Meta(BookSerializer.Meta):
        fields = BookSerializer.Meta.fields + ['borrow_history']
    
    def get_borrow_history(self, obj):
        # نمایش 5 امانت آخر
        borrows = obj.borrow_records.order_by('-borrow_date')[:5]
        return BorrowRecordSerializer(borrows, many=True).data

class MemberSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Member
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'member_id', 'student_id',
            'member_type', 'phone', 'email', 'membership_start', 'membership_end',
            'active', 'max_borrow_limit', 'notes'
        ]
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

class MemberBorrowHistorySerializer(MemberSerializer):
    borrow_records = serializers.SerializerMethodField()
    
    class Meta(MemberSerializer.Meta):
        fields = MemberSerializer.Meta.fields + ['borrow_records']
    
    def get_borrow_records(self, obj):
        borrows = obj.borrow_records.order_by('-borrow_date')
        return BorrowRecordSerializer(borrows, many=True).data

class BorrowRecordSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)
    member_name = serializers.SerializerMethodField()
    days_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = BorrowRecord
        fields = [
            'id', 'book', 'book_title', 'member', 'member_name',
            'borrow_date', 'due_date', 'returned', 'return_date',
            'fine', 'renewal_count', 'notes', 'days_overdue'
        ]
        read_only_fields = ['fine', 'days_overdue']
    
    def get_member_name(self, obj):
        return f"{obj.member.first_name} {obj.member.last_name}"
    
    def get_days_overdue(self, obj):
        if obj.returned and obj.return_date > obj.due_date:
            return (obj.return_date - obj.due_date).days
        elif not obj.returned and timezone.now().date() > obj.due_date:
            return (timezone.now().date() - obj.due_date).days
        return 0