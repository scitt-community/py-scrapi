# -*- coding: utf-8 -*-
"""DataTrails SCRAPI Engine implementation
"""
# Note direct support for SCRAPI endpoints in a work in progress
# for the DataTrails Python SDK. In time the direct requests calls
# and format fixups will be replaced by clean routing straight
# into the DataTrails Python SDK

import base64
import cbor2
from datetime import datetime
import logging

from rfc9290 import encode_problem_details

from archivist.archivist import Archivist
from archivist.logger import set_logger
from archivist.errors import ArchivistBadRequestError

from pycose.messages import Sign1Message
from pycose.headers import CoseHeaderAttribute

from .scrapi_engine import ScrapiEngine
from .scrapi_exception import ScrapiException

LOGGER = logging.getLogger(__name__)

# @CoseHeaderAttribute.register_attribute()
# class MetaMapHeader(CoseHeaderAttribute):
#     identifier = -6804
#     fullname = "META_MAP"

@CoseHeaderAttribute.register_attribute()
class CwtClaimsHeader(CoseHeaderAttribute):
    identifier = 13
    fullname = "CWT_CLAIMS"

class DatatrailsDroidScrapiEngine(ScrapiEngine):
    """DataTrails Native Engine implementation"""

    def __init__(self, ts_args):
        self._url = ts_args["url"]
        self._client_id = ts_args["client_id"]
        self._client_secret = ts_args["client_secret"]

        self._archivist = Archivist(
            self._url, (self._client_id, self._client_secret)
        )
        set_logger(ts_args["log_level"] or "INFO")

        # Make sure we have today's droid
        iso_date = datetime.today().strftime("%Y%m%d")
        asset_name = f"droid_{iso_date}"
        droid, _ = self._archivist.assets.create_if_not_exists(
            {
                "selector": [
                    {
                        "attributes": [
                            "arc_display_name",
                            "arc_display_type",
                            "target_artifact",
                        ],
                    },
                ],
                "behaviours": ["RecordEvidence"],
                "attributes": {
                    "arc_display_name": asset_name,
                    "arc_display_type": "scitt_droid",
                    "target_artifact": "vCon",
                    "arc_description": "Daily Event Accumulator For vCon SCITT Events",
                },
            },
        )
        self._asset_id = droid['identity']

        self._initialized = True

    def __str__(self) -> str:
        return f"DataTrails SCRAPI Droid Engine ({self._url})"

    def initialized(self):
        return self._initialized

    def get_configuration(self):
        raise NotImplementedError("get_configuration")

    def register_signed_statement(self, statement):
        logging.debug("registering signed statement")

        # Extract the meta-map and lift them as attributes
        # TODO: get_attr doesn't work because of duplicate values in
        # phdr and uhdr :-/
        # attrs = statement.get_attr(MetaMapHeader, {})
        attrs = statement.phdr["meta_map"] or {}
        logging.debug(attrs)

        # Base64 encode the original for safe transit
        bin_statement = statement.encode(sign=False)
        b64_statement = base64.b64encode(bin_statement).decode("utf-8")
        attrs["signed_statement"] = b64_statement

        # Lift the subject to make it findable
        # claims = statement.get_attr(CwtClaimsHeader, {})
        claims = statement.phdr[CwtClaimsHeader]
        attrs["subject"] = claims[2]
        attrs["issuer"] = claims[1]

        try:
            props = {
                "operation": "Record",
                "behaviour": "RecordEvidence",
            }
            event = self._archivist.events.create(
                self._asset_id,
                props=props,
                attrs=attrs,
            )
        except ArchivistBadRequestError as e:
            logging.debug(e)
            return None, encode_problem_details(
                {
                    "type": "https://example.com/error/validation-error",
                    "title": "Registration Error",
                    "detail": "Payload was not accepted by DataTrails",
                    "response-code": 400,
                }
            )

        # Form the response using Event ID as the operation id
        scrapi_response = {
            "operationID": event["identity"],
            "status": "running",
        }
        return None, cbor2.dumps(scrapi_response)

    def check_registration(self, registration_id):
        logging.debug("checking on operation %s", registration_id)

        try:
            event = self._archivist.events.read(registration_id)
        except ArchivistBadRequestError as e:
            logging.debug(e)
            return None, encode_problem_details(
                {
                    "type": "https://example.com/error/not-found-error",
                    "title": "Not Found",
                    "detail": "The specified operation id was not found as an Event in DatatTrails",
                    "response-code": 404,
                }
            )

        assert (
            event["identity"] == registration_id
        ), "Assertion failed: identities don't match."

        # Make sure it's settled on the log
        if event["confirmation_status"] in ["CONFIRMED", "COMMITTED"]:
            scrapi_response = {
                "operationID": registration_id,
                "entryID": registration_id,
                "status": "succeeded",
            }
        else:
            scrapi_response = {
                "operationID": registration_id,
                "status": "running",
            }

        return None, cbor2.dumps(scrapi_response)

    def resolve_receipt(self, entry_id):
        logging.debug("resolving receipt %s", entry_id)

        # TODO: Need to generate receipt for DataTrails native Event
        # TODO: Geting a real receipt for this is a few hours work.
        # for now just make an empty (but valid) object
        receipt = b"00"  # TODO this is not a valid object!

        return None, receipt

    def resolve_signed_statement(self, entry_id):
        logging.debug("resolving entry %s", entry_id)

        try:
            event = self._archivist.events.read(entry_id)
        except ArchivistBadRequestError as e:
            logging.debug(e)
            return None, encode_problem_details(
                {
                    "type": "https://example.com/error/not-found-error",
                    "title": "Not Found",
                    "detail": "The specified operation id was not found as an Event in DatatTrails",
                    "response-code": 404,
                }
            )

        assert (
            event["identity"] == entry_id
        ), "Assertion failed: identities don't match."

        if not event["event_attributes"]["signed_statement"]:
            return None, encode_problem_details(
                {
                    "type": "https://example.com/error/not-found-error",
                    "title": "Invalid Request",
                    "detail": "The specified event does not have a SCITT statement",
                    "response-code": 400,
                }
            )

        # Extract signed statement from within
        b64_statement = event["event_attributes"]["signed_statement"]
        cose_statement = base64.b64decode(b64_statement)
        signed_statement = Sign1Message.decode(cose_statement)

        return None, signed_statement

    def issue_signed_statement(self, statement):
        raise NotImplementedError(
            "DataTrails TS does not offer on-behalf signing"
        )
