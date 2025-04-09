class DynamicAppDatabaseRouter:
    """
    A database router to route queries for dynamically created app models to specific databases.
    """
    def db_for_read(self, model, **hints):
        db_name = getattr(model._meta, 'db_name', None)
        if db_name:
            return db_name
        return 'default'  # Default database

    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'default'
