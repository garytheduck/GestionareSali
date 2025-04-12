from app import create_app
from app.utils.schedule_importer import import_schedule_from_usv_api

app = create_app('development')
with app.app_context():
    result = import_schedule_from_usv_api('2023-2024-2')
    print(result)
