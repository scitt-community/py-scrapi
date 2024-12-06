"""Simple test for end-to-end happy day case"""

from pprint import pprint
import os
import sys
import time

from pycose.messages import Sign1Message
from py_scrapi.py_scrapi import PyScrapi

args = {
    "url": "https://app.datatrails.ai",
    "client_secret": os.environ.get("DATATRAILS_CLIENT_SECRET"),
    "client_id": os.environ.get("DATATRAILS_CLIENT_ID"),
    "log_level": "INFO",
}

print("Initializing TS connection")
#myScrapi = PyScrapi("DataTrails", args)
myScrapi = PyScrapi("DataTrailsDroid", args)

print("Registering Signed Statement")
# Read the binary data from the file and make into Sign1Message
with open("signed-statement.cbor", "rb") as data_file:
    original_cose = data_file.read()

original_signed_statement = Sign1Message.decode(original_cose)

# Hack in a meta-map
original_signed_statement.phdr["meta_map"] = {
  "conserver_link": "scitt",
  "conserver_link_name":  "scitt_created",
  "conserver_link_version": "0.2.0",
  "timestamp_declared": "2024-05-07T16:33:29.004994",
  "vcon_operation": "vcon_create",
  "vcon_draft_version": "01"
}

# DEBUG: Re-serialise for check at the end
submitted_cose = original_signed_statement.encode(tag=True, sign=False)

# Send to SCITT Transparency Service
lro = myScrapi.register_signed_statement(original_signed_statement)
if not lro:
    print("FATAL: failed to get registration ID for Signed Statement")
    sys.exit()

print("Polling operation status")
# Check on the status of the operation
# Poll until success or failure
while True:
    reg_result = myScrapi.check_registration(lro)

    if not "status" in reg_result:
        print("This shouldn't happen!")
        # May be transient. Go round again
    elif reg_result["status"] == "failed":
        print("Registration FAILED :-(")
        sys.exit(1)
    elif reg_result["status"] == "running":
        print("STILL RUNNING :-|")
    elif reg_result["status"] == "succeeded":
        print("SUCCESS :-)")
        break
    else:
        print(
            f"This shouldn't happen! What is status '{reg_result['status']}'"
        )
        # May be transient. Go round again

    time.sleep(2)

print("Next we fetch the receipt!")
receipt = myScrapi.resolve_receipt(reg_result["entryID"])

# Write out the updated Transparent Statement
with open("final_receipt", "wb") as file:
    file.write(receipt)
    print("File saved successfully")

print("Now see if we can get the original Signed Statement back")
retrieved_signed_statement = myScrapi.resolve_signed_statement(
    reg_result["entryID"]
)

retrieved_cose = retrieved_signed_statement.encode(tag=True, sign=False)
if submitted_cose != retrieved_cose:
    print("FATAL: STATEMENTS DO NOT MATCH!")
    sys.exit(1)

print("ALL TESTS PASSED")
