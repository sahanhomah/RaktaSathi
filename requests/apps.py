from django.apps import AppConfig


class RequestsConfig(AppConfig):
    name = 'requests'

    def ready(self):
        from . import signals  # noqa: F401
