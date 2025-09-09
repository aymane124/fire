import os
import django
import sys
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import connection

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'firewallbackend.settings')
django.setup()

def check_database_tables():
    """Check what tables exist in the database"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = cursor.fetchall()
        return [table[0] for table in tables]

def create_missing_tables():
    """Create any missing essential tables"""
    tables = check_database_tables()
    
    if 'auth_user' not in tables:
        print("Creating missing auth_user table...")
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE "auth_user" (
                    "id" varchar(36) NOT NULL PRIMARY KEY,
                    "password" varchar(128) NOT NULL,
                    "is_superuser" bool NOT NULL,
                    "username" varchar(150) NOT NULL UNIQUE,
                    "first_name" varchar(150) NOT NULL,
                    "last_name" varchar(150) NOT NULL,
                    "email" varchar(254) NOT NULL UNIQUE,
                    "phone_number" varchar(20) NOT NULL,
                    "is_active" bool NOT NULL,
                    "is_staff" bool NOT NULL,
                    "date_joined" datetime NOT NULL,
                    "last_login" datetime NULL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX "auth_user_email_ece7f7_idx" ON "auth_user" ("email")
            """)
            
            cursor.execute("""
                CREATE INDEX "auth_user_usernam_f2740e_idx" ON "auth_user" ("username")
            """)
        print("✅ auth_user table created!")

def setup_database():
    print("🚀 Starting database setup...")
    
    # Check if we should reset the database
    reset_db = input("Do you want to reset the database? (y/N): ").lower().strip()
    
    if reset_db == 'y':
        if os.path.exists('db.sqlite3'):
            print("🗑️  Removing existing database...")
            os.remove('db.sqlite3')
    
    # Check current migration status
    print("📋 Checking migration status...")
    try:
        call_command('showmigrations', verbosity=0)
    except Exception as e:
        print(f"⚠️  Migration check failed: {e}")
    
    # Create migrations for all apps
    print("📝 Creating migrations...")
    try:
        call_command('makemigrations', verbosity=0)
        print("✅ Migrations created successfully!")
    except Exception as e:
        print(f"⚠️  Migration creation failed: {e}")
    
    # Run migrations
    print("🔄 Running migrations...")
    try:
        call_command('migrate', verbosity=0)
        print("✅ Migrations applied successfully!")
    except Exception as e:
        print(f"⚠️  Migration application failed: {e}")
        print("🔧 Attempting to fix missing tables...")
        create_missing_tables()
    
    # Verify database tables
    print("🔍 Verifying database tables...")
    tables = check_database_tables()
    print(f"📊 Found {len(tables)} tables in database")
    
    if 'auth_user' not in tables:
        print("❌ auth_user table is missing!")
        create_missing_tables()
    else:
        print("✅ auth_user table exists")
    
    # Create superuser
    print("👤 Creating superuser...")
    User = get_user_model()
    
    try:
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            print("✅ Superuser created successfully!")
            print("📋 Login credentials:")
            print("   Username: admin")
            print("   Password: admin123")
        else:
            print("ℹ️  Superuser already exists!")
    except Exception as e:
        print(f"❌ Error creating superuser: {e}")
        print("🔧 This might be due to database connection issues.")
        print("💡 Try running: python manage.py createsuperuser")
        return False
    
    # Final verification
    print("\n🔍 Final verification...")
    try:
        call_command('check', verbosity=0)
        print("✅ Django system check passed!")
    except Exception as e:
        print(f"⚠️  System check failed: {e}")
    
    print("\n🎉 Database setup completed successfully!")
    print("🚀 You can now run the application with:")
    print("   python manage.py runserver")
    print("   or")
    print("   python run_app.py")
    return True

if __name__ == '__main__':
    setup_database() 