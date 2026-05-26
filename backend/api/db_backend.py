"""
Custom MySQL backend for Django 6.0 that disables RETURNING support.
This is needed for MariaDB 10.4 compatibility.
"""

from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from django.db.backends.mysql.features import DatabaseFeatures as MySQLDatabaseFeatures
from django.db.backends.mysql.operations import DatabaseOperations as MySQLDatabaseOperations


class CustomDatabaseFeatures(MySQLDatabaseFeatures):
    """Custom features that disable RETURNING for MariaDB 10.4."""
    supports_returning = False
    can_return_columns_from_insert = False


class CustomDatabaseOperations(MySQLDatabaseOperations):
    """Custom operations that disable RETURNING for MariaDB 10.4."""
    def can_return_columns_from_insert(self, cursor, returning_cols=None):
        return False


class CustomDatabaseWrapper(MySQLDatabaseWrapper):
    """Custom wrapper that uses custom features and operations."""
    features_class = CustomDatabaseFeatures
    ops_class = CustomDatabaseOperations
    
    def check_database_version_supported(self):
        # Skip version check for MariaDB 10.4
        pass
