from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import os
from django.utils import timezone
from django.urls import reverse

def book_cover_path(instance, filename):
    """تعیین مسیر ذخیره تصویر جلد کتاب"""
    return f'book_covers/{instance.title.replace(" ", "_")}{os.path.splitext(filename)[1]}'

class Genre(models.Model):
    """مدل برای دسته‌بندی سلسله‌مراتبی کتاب‌ها"""
    name = models.CharField(max_length=100, verbose_name='نام ژانر')
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name='ژانر والد'
    )
    
    class Meta:
        verbose_name = 'ژانر'
        verbose_name_plural = 'ژانرها'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Book(models.Model):
    """مدل جامع کتاب با تمام ویژگی‌های ضروری"""
    STATUS_CHOICES = [
        ('available', 'موجود'),
        ('borrowed', 'امانت داده شده'),
        ('reserved', 'رزرو شده'),
        ('maintenance', 'در حال تعمیر'),
        ('damaged', 'آسیب دیده'),
    ]
    
    PHYSICAL_CONDITION_CHOICES = [
        ('excellent', 'عالی'),
        ('good', 'خوب'),
        ('fair', 'متوسط'),
        ('poor', 'ضعیف'),
        ('damaged', 'آسیب دیده'),
    ]
    
    # اطلاعات اصلی
    title = models.CharField(max_length=200, verbose_name='عنوان کتاب')
    authors = models.CharField(max_length=200, verbose_name='نویسنده/نویسندگان')
    isbn = models.CharField(max_length=20, unique=True, verbose_name='شابک/کد کتاب')
    publisher = models.CharField(max_length=100, verbose_name='ناشر')
    publication_year = models.PositiveIntegerField(
        verbose_name='سال انتشار',
        validators=[
            MinValueValidator(1000), 
            MaxValueValidator(timezone.now().year)
        ]
    )
    genre = models.ForeignKey(
        Genre, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='ژانر'
    )
    
    # وضعیت فیزیکی
    pages = models.PositiveIntegerField(verbose_name='تعداد صفحات')
    physical_condition = models.CharField(
        max_length=15,
        choices=PHYSICAL_CONDITION_CHOICES,
        default='good',
        verbose_name='وضعیت فیزیکی'
    )
    cover = models.ImageField(
        upload_to=book_cover_path,
        verbose_name='تصویر جلد',
        blank=True,
        null=True
    )
    
    # مدیریت موجودیت
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='تعداد کل'
    )
    available = models.PositiveIntegerField(
        verbose_name='موجودی', 
        default=1,
        editable=False
    )
    status = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='available',
        verbose_name='وضعیت'
    )
    
    # اطلاعات اضافی
    description = models.TextField(blank=True, verbose_name='توضیحات')
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ اضافه شدن'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاریخ به‌روزرسانی'
    )

    class Meta:
        verbose_name = 'کتاب'
        verbose_name_plural = 'کتاب‌ها'
        ordering = ['title']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['isbn']),
            models.Index(fields=['publication_year']),
        ]

    def __str__(self):
        return f"{self.title} - {self.authors}"

    def save(self, *args, **kwargs):
        """محاسبه خودکار موجودی و وضعیت"""
        # محاسبه موجودی
        if not self.available:
            self.available = self.quantity
        
        # به‌روزرسانی خودکار وضعیت
        if self.available == 0:
            self.status = 'borrowed'
        elif self.physical_condition == 'damaged':
            self.status = 'damaged'
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('book_detail', args=[str(self.id)])


class Member(models.Model):
    """مدل جامع اعضا با قابلیت اتصال به سیستم احراز هویت"""
    MEMBER_TYPE_CHOICES = [
        ('student', 'دانشجو'),
        ('professor', 'استاد'),
        ('staff', 'کارمند'),
        ('guest', 'میهمان'),
    ]
    
    # اتصال به سیستم کاربری
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='حساب کاربری'
    )
    
    # اطلاعات هویتی
    first_name = models.CharField(max_length=100, verbose_name='نام')
    last_name = models.CharField(max_length=100, verbose_name='نام خانوادگی')
    member_id = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name='شماره عضویت'
    )
    student_id = models.CharField(
        max_length=20, 
        unique=True,
        null=True,
        blank=True,
        verbose_name='شماره دانشجویی/پرسنلی'
    )
    
    # اطلاعات تماس
    phone = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        verbose_name='تلفن'
    )
    email = models.EmailField(
        verbose_name='ایمیل'
    )
    address = models.TextField(
        blank=True,
        verbose_name='آدرس'
    )
    
    # وضعیت عضویت
    member_type = models.CharField(
        max_length=10,
        choices=MEMBER_TYPE_CHOICES,
        default='student',
        verbose_name='نوع عضو'
    )
    membership_start = models.DateField(
        auto_now_add=True,
        verbose_name='تاریخ شروع عضویت'
    )
    membership_end = models.DateField(
        verbose_name='تاریخ پایان عضویت'
    )
    active = models.BooleanField(
        default=True, 
        verbose_name='فعال'
    )
    max_borrow_limit = models.PositiveIntegerField(
        default=3,
        verbose_name='حداکثر تعداد امانت'
    )
    
    # اطلاعات اضافی
    notes = models.TextField(
        blank=True,
        verbose_name='یادداشت‌ها'
    )

    class Meta:
        verbose_name = 'عضو'
        verbose_name_plural = 'اعضا'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['member_id']),
            models.Index(fields=['last_name', 'first_name']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.member_id})"

    def get_full_name(self):
        """نام کامل عضو"""
        if self.user:
            return self.user.get_full_name()
        return f"{self.first_name} {self.last_name}"
    
    def is_membership_valid(self):
        """بررسی اعتبار عضویت"""
        return self.active and self.membership_end >= timezone.now().date()
    
    @property
    def name(self):
        """برای سازگاری با کدهای قدیمی"""
        return self.get_full_name()


class BorrowRecord(models.Model):
    """مدل پیشرفته سوابق امانت کتاب"""
    book = models.ForeignKey(
        Book, 
        on_delete=models.CASCADE, 
        verbose_name='کتاب',
        related_name='borrow_records'
    )
    member = models.ForeignKey(
        Member, 
        on_delete=models.CASCADE, 
        verbose_name='عضو',
        related_name='borrow_records'
    )
    
    # اطلاعات امانت
    borrow_date = models.DateField(
        auto_now_add=True,
        verbose_name='تاریخ امانت'
    )
    due_date = models.DateField(
        verbose_name='موعد بازگشت'
    )
    return_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name='تاریخ بازگشت'
    )
    returned = models.BooleanField(
        default=False, 
        verbose_name='برگشت داده شده؟'
    )
    
    # اطلاعات تمدید و جریمه
    renewal_count = models.PositiveIntegerField(
        default=0,
        verbose_name='تعداد تمدید'
    )
    fine_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0, 
        verbose_name='مبلغ جریمه'
    )
    
    # اطلاعات اضافی
    notes = models.TextField(
        blank=True,
        verbose_name='یادداشت‌ها'
    )

    class Meta:
        verbose_name = 'سابقه امانت'
        verbose_name_plural = 'سوابق امانت'
        ordering = ['-borrow_date']
        permissions = [
            ('can_renew_borrowing', 'می‌تواند امانت را تمدید کند'),
        ]
        indexes = [
            models.Index(fields=['borrow_date']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        status = "برگشت داده شده" if self.returned else "در دست امانت"
        return f"{self.book.title} - {self.member.name} ({status})"

    def save(self, *args, **kwargs):
        """محاسبات خودکار هنگام ذخیره"""
        # محاسبه تاریخ برگشت
        if self.returned and not self.return_date:
            self.return_date = timezone.now().date()
        
        # محاسبه موعد برگشت برای امانت جدید
        if not self.pk:
            self.set_due_date()
        
        # محاسبه جریمه
        self.calculate_fine()
        
        super().save(*args, **kwargs)
    
    def set_due_date(self):
        """تعیین تاریخ برگشت بر اساس نوع عضو"""
        base_days = 14  # پیش‌فرض برای دانشجویان و مهمانان
        
        if self.member.member_type == 'professor':
            base_days = 30
        elif self.member.member_type == 'staff':
            base_days = 21
            
        self.due_date = self.borrow_date + timezone.timedelta(days=base_days)
    
    def calculate_fine(self):
        """محاسبه جریمه تأخیر"""
        if not self.returned or not self.return_date:
            self.fine_amount = 0
            return
        
        if self.return_date > self.due_date:
            days_late = (self.return_date - self.due_date).days
            self.fine_amount = days_late * 5000  # 5000 تومان برای هر روز تأخیر


class Reservation(models.Model):
    """مدل مدیریت رزرو کتاب"""
    RESERVATION_STATUS = [
        ('pending', 'در انتظار تایید'),
        ('approved', 'تایید شده'),
        ('canceled', 'لغو شده'),
        ('expired', 'منقضی شده'),
    ]
    
    book = models.ForeignKey(
        Book, 
        on_delete=models.CASCADE, 
        verbose_name='کتاب',
        related_name='reservations'
    )
    member = models.ForeignKey(
        Member, 
        on_delete=models.CASCADE, 
        verbose_name='عضو',
        related_name='reservations'
    )
    
    # اطلاعات رزرو
    reservation_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ رزرو'
    )
    expiration_date = models.DateTimeField(
        verbose_name='تاریخ انقضا'
    )
    status = models.CharField(
        max_length=10, 
        choices=RESERVATION_STATUS, 
        default='pending',
        verbose_name='وضعیت'
    )
    
    # اطلاعات اضافی
    notes = models.TextField(
        blank=True,
        verbose_name='یادداشت‌ها'
    )

    class Meta:
        verbose_name = 'رزرو'
        verbose_name_plural = 'رزروها'
        ordering = ['-reservation_date']
        unique_together = ['book', 'member', 'status']

    def __str__(self):
        return f"رزرو {self.book.title} توسط {self.member.name}"

    def save(self, *args, **kwargs):
        """تعیین خودکار تاریخ انقضا"""
        if not self.expiration_date:
            self.expiration_date = timezone.now() + timezone.timedelta(days=3)
        super().save(*args, **kwargs)
    
    def is_active(self):
        """بررسی فعال بودن رزرو"""
        return self.status == 'approved' and timezone.now() < self.expiration_date