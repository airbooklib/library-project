from django.core.management.base import BaseCommand
import json
from django.core import serializers
from books.models import *
from django.contrib.auth.models import User, Group, Permission
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'Backup all database data to JSON files'

    def handle(self, *args, **options):
        backup_dir = f"backups/{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        models = [
            (Genre, 'genres'),
            (Book, 'books'),
            (Member, 'members'),
            (BorrowRecord, 'borrow_records'),
            (User, 'users'),
            (Group, 'groups'),
            (Permission, 'permissions'),
        ]

        for model, name in models:
            try:
                data = serializers.serialize("json", model.objects.all())
                file_path = f"{backup_dir}/{name}.json"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(data)
                
                self.stdout.write(self.style.SUCCESS(f'Successfully backed up {model.__name__} to {file_path}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error backing up {model.__name__}: {str(e)}'))