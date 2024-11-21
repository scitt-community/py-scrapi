# -*- coding: utf-8 -*-
"""DataTrails SCRAPI Engine implementation
"""
# Note direct support for SCRAPI endpoints in a work in progress
# for the DataTrails Python SDK. In time the direct requests calls
# and format fixups will be replaced by clean routing straight
# into the DataTrails Python SDK

import logging

from archivist.archivist import Archivist
from archivist.logger import set_logger

import cbor2
from pycose.messages import Sign1Message
import requests

from .scrapi_engine import ScrapiEngine
from .scrapi_exception import ScrapiException

LOGGER = logging.getLogger(__name__)


class DatatrailsScrapiEngine(ScrapiEngine):
    """DataTrails SCRAPI Engine implementation"""

    def __init__(self, ts_args):
        self._url = ts_args["url"]
        self._client_id = ts_args["client_id"]
        self._client_secret = ts_args["client_secret"]

        self._archivist = Archivist(
            self._url, (self._client_id, self._client_secret)
        )
        set_logger(ts_args["log_level"] or "INFO")

        self._initialized = True

    def __str__(self) -> str:
        return f"DataTrails SCRAPI Engine ({self._url})"

    def initialized(self):
        # TODO: need to check more status for emergent errors. Maybe send a NoOp?
        return self._initialized

    def get_configuration(self):
        raise NotImplementedError("get_configuration")

    def register_signed_statement(self, statement):
        logging.debug("registering signed statement")

        marshalled = statement.encode(sign=False)

        headers = self._archivist._add_headers({})
        response = requests.post(
            f"{self._url}/archivist/v1/publicscitt/entries",
            data=marshalled,
            headers=headers,
            timeout=20000,
        )

        # Should be 201 CREATED but be flexible here
        if response.status_code not in [200, 201, 202]:
            logging.debug("%s", str(response))
            raise ScrapiException(f"Failed to register statement: {response}")

        # Early DataTrails implementations return JSON. In such cases fake
        # up CBOR response here so that common code doesn't need to change
        jr = response.json()
        if jr:
            return None, cbor2.dumps(response.json())

        return None, response.content

    def check_registration(self, registration_id):
        logging.debug("checking on operation %s", registration_id)

        headers = headers = self._archivist._add_headers({})
        response = requests.get(
            f"{self._url}/archivist/v1/publicscitt/operations/{registration_id}",
            headers=headers,
            timeout=20000,
        )
        if response.status_code == 400:
            # Note: The Public SCITT endpoint returns 400 for Events that have not
            # made it across the sharing boundary yet.
            # Temporarily patch this, it will be removed soon.
            logging.debug("Suspected temporary propagation 400 error")
            return None, cbor2.dumps(
                {"operationID": registration_id, "status": "running"}
            )

        if response.status_code not in [200, 201, 202]:
            logging.debug(
                "FAILED to get operation status: %s", response.status_code
            )
            return response.content, None

        # Early DataTrails implementations return JSON. In such cases fake
        # up CBOR response here so that common code doesn't need to change
        jr = response.json()
        if jr:
            return None, cbor2.dumps(response.json())

        return None, response.content

    def resolve_receipt(self, entry_id):
        logging.debug("resolving receipt %s", entry_id)

        headers = headers = self._archivist._add_headers({})
        response = requests.get(
            f"{self._url}/archivist/v1/publicscitt/entries/{entry_id}/receipt",
            headers=headers,
            timeout=20000,
        )
        if response.status_code != 200:
            logging.debug("FAILED to get receipt: %s", response.status_code)
            return response.content, None

        return None, response.content

    def resolve_signed_statement(self, entry_id):
        logging.debug("resolving entry %s", entry_id)

        headers = headers = self._archivist._add_headers({})
        response = requests.get(
            f"{self._url}/archivist/v1/publicscitt/entries/{entry_id}",
            headers=headers,
            timeout=20000,
        )
        if response.status_code != 200:
            logging.debug("FAILED to get entry: %s", response.status_code)
            return response.content, None

        # Note: DataTrails currently returns the _counter_SignedStatement
        # but SCRAPI wants the original SignedStatement exactly as submitted
        # by the Issuer, so strip off the outer envelope
        decoded_statement = Sign1Message.decode(response.content)
        inner_statement = Sign1Message.decode(decoded_statement.payload)

        return None, inner_statement

    def issue_signed_statement(self, statement):
        raise NotImplementedError(
            "DataTrails TS does not offer on-behalf signing"
        )
