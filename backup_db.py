import shutil
import os
from datetime import datetime

def backup_database():
    """Создает резервную копию текущей БД"""
    current_db = 'tutors.db'
    
    if not os.path.exists(current_db):
        print(f"❌ Файл БД не найден: {current_db}")
        return False
    
    # Создаем имя бэкапа с временной меткой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"tutors_backup_{timestamp}.db"
    old_db_name = "tutors_old.db"
    
    try:
        # Создаем бэкап с временной меткой
        shutil.copy2(current_db, backup_name)
        print(f"✅ Создан бэкап: {backup_name}")
        
        # Также создаем копию для миграции
        shutil.copy2(current_db, old_db_name)
        print(f"✅ Создана копия для миграции: {old_db_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания бэкапа: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Создание резервной копии базы данных...")
    success = backup_database()
    
    if success:
        print("\n✅ Резервная копия создана успешно!")
        print("Теперь можно запускать миграцию: python migrate_database.py")
    else:
        print("\n❌ Не удалось создать резервную копию!")