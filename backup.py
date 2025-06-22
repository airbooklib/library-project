import json
from django.core import serializers
from books.models import *
from django.contrib.auth.models import *
import os
from datetime import datetime

def get_all_models():
    """لیست تمام مدل‌های موجود در پروژه"""
    return [
        (Genre, 'genres'),
        (Book, 'books'),
        (Member, 'members'),
        (BorrowRecord, 'borrow_records'),
        (User, 'auth_users'),
        (Group, 'auth_groups'),
        (Permission, 'auth_permissions'),
    ]

def create_backup_dir():
    """ایجاد پوشه بک‌آپ"""
    backup_dir = f"backups/{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def backup_model(model, filename, backup_dir):
    """ذخیره یک مدل در فایل JSON"""
    try:
        data = serializers.serialize("python", model.objects.all())
        backup_path = f"{backup_dir}/{filename}.json"
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True, backup_path
    except Exception as e:
        return False, str(e)

def backup_all_data():
    """تابع اصلی برای بک‌آپ گرفتن"""
    print("📂 شروع فرآیند بک‌آپ...\n")
    
    backup_dir = create_backup_dir()
    results = []
    
    for model, filename in get_all_models():
        success, message = backup_model(model, filename, backup_dir)
        results.append({
            'model': model.__name__,
            'success': success,
            'message': message
        })
    
    # نمایش نتایج
    print("\n📊 نتایج بک‌آپ:")
    for result in results:
        status = "✅ موفق" if result['success'] else "❌ خطا"
        print(f"{status} - {result['model']}: {result['message']}")
    
    print(f"\n🎉 تمام داده‌ها در مسیر {backup_dir} ذخیره شدند")

if __name__ == '__main__':
    backup_all_data()