# -*- coding: utf-8 -*-
"""Pure virtual class to define legal shape of TS Engines for SCRAPI

This module contains the base class which defines the standard
interactions that any implementation should support. These are then
overridden in specific engine files for each Transparency Service
implementation.
"""

# pylint: disable=W0107

from abc import ABC
from abc import abstractmethod


class ScrapiEngine(ABC):
    """Virtual base class for all SCRAPI providers"""

    @abstractmethod
    def initialized(self):
        """Pure virtual. Use a derived class"""
        pass

    @abstractmethod
    def get_configuration(self):
        """Pure virtual. Use a derived class"""
        pass

    @abstractmethod
    def register_signed_statement(self, statement):
        """Pure virtual. Use a derived class"""
        pass

    @abstractmethod
    def check_registration(self, registration_id):
        """Pure virtual. Use a derived class"""
        pass

    @abstractmethod
    def resolve_receipt(self, entry_id):
        """Pure virtual. Use a derived class"""
        pass

    @abstractmethod
    def resolve_signed_statement(self, entry_id):
        """Pure virtual. Use a derived class"""
        pass

    @abstractmethod
    def issue_signed_statement(self, statement):
        """Pure virtual. Use a derived class"""
        pass
