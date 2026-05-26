"""
Django app configuration for bioinformatics module.
"""

from django.apps import AppConfig


class BioinformaticsConfig(AppConfig):
    """Configuration for the bioinformatics Django app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bioinformatics'
    verbose_name = 'Bioinformatics Tools'
    
    def ready(self):
        """Called when Django app is ready."""
        pass
