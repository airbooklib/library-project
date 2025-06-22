from django.db import migrations

def convert_old_genres(apps, schema_editor):
    # مدل‌های تاریخی را بگیرید
    Book = apps.get_model('books', 'Book')
    Genre = apps.get_model('books', 'Genre')
    
    # ایجاد ژانرهای جدید بر اساس مقادیر قدیمی
    genre_mapping = {
        'رمان': Genre.objects.get_or_create(name='رمان')[0],
        'علمی': Genre.objects.get_or_create(name='علمی')[0],
        'تاریخی': Genre.objects.get_or_create(name='تاریخی')[0],
        'پزشکی': Genre.objects.get_or_create(name='پزشکی')[0],
    }
    
    # به‌روزرسانی همه کتاب‌ها
    for book in Book.objects.all():
        if book.genre in genre_mapping:
            book.genre_new = genre_mapping[book.genre]
            book.save()

class Migration(migrations.Migration):

    dependencies = [
        ('books', '0006_alter_borrowrecord_options_book_created_at_and_more'),
    ]

    operations = [
        migrations.RunPython(convert_old_genres),
    ]