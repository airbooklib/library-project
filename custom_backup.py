import json
from django.core import serializers
from books.models import *

def export_data():
    data = serializers.serialize('json', Book.objects.all(), ensure_ascii=False)
    with open('backup_fa.json', 'w', encoding='utf-8') as f:
        f.write(data)

export_data()