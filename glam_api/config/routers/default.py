"""
DEFAULT ROUTERS
"""


class CacheRouter:
    """A router to control all database cache operations"""

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "django_cache":
            return "task_db"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "django_cache":
            return "task_db"
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "django_cache":
            return db == "task_db"
        return None


class TaskRouter:
    """Router to control django_q operations"""

    def db_for_read(self, model, **hints):
        if model._meta.app_label == "django_q":
            return "task_db"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "django_q":
            return "task_db"
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "django_q":
            return db == "task_db"
        return None
