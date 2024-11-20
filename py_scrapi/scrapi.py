# -*- coding: utf-8 -*-
"""Portable SCRAPI connection interface

This module contains the core SCRAPI calls which should be
portable for any client integration.
"""

# Standard imports
import logging
from time import time

# SCRAPI and SCITT imports
import cbor2
from rfc9290 import decode_problem_details

from .scrapi_exception import ScrapiException
from .null_engine import NullScrapiEngine
from .datatrails_engine import DatatrailsScrapiEngine

LOGGER = logging.getLogger(__name__)


class Scrapi:  # pylint: disable=too-many-instance-attributes
    """Portable class for all Scrapi implementations.

    args:
        ts_type (str): Type of transparency service
        ts_args (dict): TS-specific initialization params

    """

    def __init__(self, ts_type: str, ts_args: dict):
        match ts_type:
            case "dummy":
                self.engine = NullScrapiEngine(ts_args)

            case "DataTrails":
                self.engine = DatatrailsScrapiEngine(ts_args)

            case _:
                raise ScrapiException(f"Unknown engine type: {ts_type}'")

    def __str__(self) -> str:
        if self.engine:
            return self.engine.__str__()

        return "Scrapi (uninitialized)"

    # The following methods require a Transparency Service and so require the
    # engine to be initialized

    def check_engine(self):
        """Helper to protect all calls that need a valid TS connection"""

        logging.debug("Scrapi checking engine liveness...")

        if not self.engine:
            raise ScrapiException("No Transparency Service engine specified")

        if not self.engine.initialized():
            raise ScrapiException("Transparency Service engine malfunction")

        logging.debug("Scrapi engine check SUCCESS")

    def get_configuration(self):
        """Wrapper for SCRAPI Transparency Configuration call

        args:
            none

        returns:
            application/json
        """

        self.check_engine()

        return self.engine.get_configuration()

    def register_signed_statement(self, statement):
        """Wrapper for SCRAPI Register Signed Statement call

        args:
            Content-Type: application/cose

            18([                            / COSE Sign1         /
            h'a1013822',                  / Protected Header   /
            {},                           / Unprotected Header /
            null,                         / Detached Payload   /
            h'269cd68f4211dffc...0dcb29c' / Signature          /
            ])

        returns:
            application/json
        """

        self.check_engine()

        err, result = self.engine.register_signed_statement(statement)
        if err:
            # Decode and log the RFC9290 Problem Details.
            problem_details = decode_problem_details(result)
            print(problem_details)
            return None

        # Pull the registration ID out
        operation = cbor2.loads(result)

        # Check for common errors
        if not "status" in operation or operation["status"] == "failed":
            raise ScrapiException("Statement Registration Failed")

        if not "operationID" in operation:
            raise ScrapiException("No Operation ID for Statement")

        # Seems legit, send it back
        return operation["operationID"]

    def check_registration(self, registration_id):
        """Wrapper for SCRAPI Check Registration call

        args:
            registration_id (str):

        returns:
            application/json
        """

        self.check_engine()

        err, result = self.engine.check_registration(registration_id)
        if err:
            # Decode and log the RFC9290 Problem Details.
            problem_details = decode_problem_details(result)
            print(problem_details)
            return None

        # Pull the registration ID out
        operation = cbor2.loads(result)

        # Check for common errors
        if not "operationID" in operation:
            raise ScrapiException("Operation ID link lost")

        if not "status" in operation:
            raise ScrapiException("No LRO status for Operation ID")

        # Seems legit, send it back
        return cbor2.loads(result)

    def resolve_receipt(self, entry_id):
        """Wrapper for SCRAPI Resolve Receipt call

        args:
            entry_id (str):

        returns:
            application/cose
        """
        self.check_engine()

        err, result = self.engine.resolve_receipt(entry_id)

        if err:
            # Decode and log the RFC9290 Problem Details.
            problem_details = decode_problem_details(result)
            print(problem_details)
            return None

        return result

    def resolve_signed_statement(self, entry_id):
        """Wrapper for SCRAPI Resolve Signed Statement call

        args:
            entry_id (str):

        returns:
            application/cose
        """
        self.check_engine()

        err, result = self.engine.resolve_signed_statement(entry_id)

        if err:
            # Decode and log the RFC9290 Problem Details.
            problem_details = decode_problem_details(result)
            print(problem_details)
            return None

        return result

    def issue_signed_statement(self, statement):
        """Sign a statement using a key held on the remote server

        args:
            statement (bstr): the to-be-signed bytes of a COSE Sign1 input

        returns:
            application/cose
        """

        self.check_engine()

        err, result = self.engine.issue_signed_statement(statement)

        if err:
            # Decode and log the RFC9290 Problem Details.
            problem_details = decode_problem_details(result)
            print(problem_details)
            return None

        return result

    def register_signed_statement_sync(self, statement):
        """Utility function for synchronous receipt generation.

        CAUTION! On some Transparency Service implementations this call may block
        for a *very* long time!

        args:
            Content-Type: application/cose

            18([                            / COSE Sign1         /
            h'a1013822',                  / Protected Header   /
            {},                           / Unprotected Header /
            null,                         / Detached Payload   /
            h'269cd68f4211dffc...0dcb29c' / Signature          /
            ])

        returns:
            application/cose
        """

        res = self.register_signed_statement(statement)
        rid = res["registration_id"]
        while True:
            res = self.check_registration(rid)
            if res["status"] == "running":
                # Wait a moment then go back around
                logging.info(
                    "Registration operation %s still running. Waiting...", rid
                )
                time.sleep(2)
            elif res["status"] == "failed":
                # Fatal. Return
                logging.info("Registration operation %s FAILED.", rid)
                return None
            elif res["status"] == "success":
                # All done. Extract COSE and return the receipt
                logging.info("Registration operation %s SUCCESS.", rid)
                return "COSE goes here!"
            else:
                logging.error(
                    "Malformed response from check_registration: %s", str(res)
                )
                return None
