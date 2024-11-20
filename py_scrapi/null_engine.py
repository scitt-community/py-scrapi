# -*- coding: utf-8 -*-
"""Dummy SCRAPI Engine implementation
"""

from .scrapi_engine import ScrapiEngine


class NullScrapiEngine(ScrapiEngine):
    """Dummy SCRAPI Engine implementation"""

    def __init__(self, ts_args):
        self._initialized = True

    def __str__(self) -> str:
        return "Dummy SCRAPI Engine (does not implement endpoints!)"

    def initialized(self):
        """Returns True if this instance is initialized"""
        return self._initialized

    def get_configuration(self):
        """Get TS configuration (not implemented)"""
        raise NotImplementedError("get_configuration")

    def register_signed_statement(self, statement):
        """Register a signed statement (not implemented)"""
        raise NotImplementedError("register_signed_statement")

    def check_registration(self, registration_id):
        """Check progress of signed statement registration (not implemented)"""
        raise NotImplementedError("check_registration")

    def resolve_receipt(self, entry_id):
        """Get a receipt (not implemented)"""
        raise NotImplementedError("resolve_receipt")

    def resolve_signed_statement(self, entry_id):
        """Get a previously registered signed statement (not implemented)"""
        raise NotImplementedError("resolve_signed_statement")

    def issue_signed_statement(self, statement):
        """On-behalf signing of statements (not implemented)"""
        raise NotImplementedError("issue_signed_statement")
