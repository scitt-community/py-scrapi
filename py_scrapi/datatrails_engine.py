# -*- coding: utf-8 -*-
"""DataTrails SCRAPI Engine implementation
"""
# Note direct support for SCRAPI endpoints in a work in progress
# for the DataTrails Python SDK. In time the direct requests calls
# and format fixups will be replaced by clean routing straight
# into the DataTrails Python SDK

import cbor2
import json
import logging

from rfc9290 import encode_problem_details

from archivist.archivist import Archivist
from archivist.logger import set_logger
from archivist.errors import ArchivistBadRequestError

from pycose.messages import Sign1Message

from .scrapi_engine import ScrapiEngine
from .scrapi_exception import ScrapiException

LOGGER = logging.getLogger(__name__)

dummy_problem = {
    "type": "https://example.com/error/validation-error",
    "title": "Validation Error",
    "detail": "Missing required field 'username'.",
    "instance": "/requests/12345",
    "response-code": 400,
}


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

        response = self._archivist.post_binary(
            f"{self._url}/archivist/v1/publicscitt/entries",
            statement,
        )

        # DataTrails API currently returns JSON...
        # Temporarily hack around this
        # Early DataTrails implementations return JSON. In such cases fake
        # up CBOR response here so that common code doesn't need to change
        jr = json.loads(response.decode("utf-8"))
        if jr:
            return None, cbor2.dumps(jr)

        return encode_problem_details(dummy_problem), None

    def check_registration(self, registration_id):
        logging.debug("checking on operation %s", registration_id)

        try:
            response = self._archivist.get_binary(
                f"{self._url}/archivist/v1/publicscitt/operations/{registration_id}",
            )
        except ArchivistBadRequestError as e:
            # Note: The Public SCITT endpoint returns 400 for Events that have not
            # made it across the sharing boundary yet.
            # Temporarily patch this, it will be removed soon.
            logging.debug(e)
            logging.debug("Suspected temporary propagation 400 error")
            return None, cbor2.dumps(
                {"operationID": registration_id, "status": "running"}
            )

        # DataTrails API currently returns JSON...
        # Temporarily hack around this
        # Early DataTrails implementations return JSON. In such cases fake
        # up CBOR response here so that common code doesn't need to change
        jr = json.loads(response.decode("utf-8"))
        if jr:
            return None, cbor2.dumps(jr)

        return encode_problem_details(dummy_problem), None

    def resolve_receipt(self, entry_id):
        logging.debug("resolving receipt %s", entry_id)

        response = self._archivist.get_binary(
            f"{self._url}/archivist/v1/publicscitt/entries/{entry_id}/receipt",
        )

        return None, response

    def resolve_signed_statement(self, entry_id):
        logging.debug("resolving entry %s", entry_id)

        response = self._archivist.get_binary(
            f"{self._url}/archivist/v1/publicscitt/entries/{entry_id}",
        )

        # Note: DataTrails currently returns the _counter_SignedStatement
        # but SCRAPI wants the original SignedStatement exactly as submitted
        # by the Issuer, so strip off the outer envelope
        decoded_statement = Sign1Message.decode(response)
        inner_statement = Sign1Message.decode(decoded_statement.payload)

        return None, inner_statement

    def issue_signed_statement(self, statement):
        raise NotImplementedError(
            "DataTrails TS does not offer on-behalf signing"
        )
