"""
EpitopX — logging filter that injects request_id into log records.
"""
import logging
import threading

_local = threading.local()


def set_request_id(rid: str):
    _local.request_id = rid


def get_request_id() -> str:
    return getattr(_local, 'request_id', '-')


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id()
        return True
