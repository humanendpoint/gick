import hmac
import hashlib
from difflib import SequenceMatcher
import time
import re
import github_tools, utilities
import json

class SignatureVerificationError(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail

# function to calculate similarity score between two strings
def similarity_score(a, b):
    return SequenceMatcher(None, a, b).ratio()


def extract_chars(payload):
    title_matches = r"#\d+ (.+?)>"
    pr_title_match = re.search(title_matches, payload["message"]["attachments"][1]["blocks"][0]["text"]["text"])
    if pr_title_match:
        pr_title = pr_title_match.group(1)
    else:
        pr_title = ""  # Handle the case where no match is found
    pr_number = payload["actions"][0]["action_id"].split("-")[0]
    user_that_clicked = payload["user"]["id"]

    return pr_title, pr_number, user_that_clicked


# wait until the github checks are complete
def wait_for_checks(org, repo, github_token, commit_sha, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(2)
        print("testing checks...")
        all_checks = github_tools.get_pr_checks(org, repo, github_token, commit_sha)
        if all_checks:
            if are_checks_completed(all_checks["check_runs"]):
                if are_checks_successful(all_checks["check_runs"]):
                    status = "Passing"
                    return status
                else:
                    status = ":red-cross-mark:"
                    return status
    # If the timeout is reached
    print("Timeout reached while waiting for checks to complete.")
    status = "Timeout"
    return status


def are_checks_completed(check_runs):
    return all(check["status"] not in ["in_progress", "queued"] for check in check_runs)


def are_checks_successful(check_runs):
    return all(
        check["conclusion"]
        not in ["action_required", "cancelled", "failure", "neutral"]
        for check in check_runs
    )


# function to extract values
def extract_value(data, keys, default=""):
    """
    Helper function to extract nested values from a dictionary.
    :param data: The dictionary to extract values from.
    :param keys: A list of keys specifying the path to the desired value.
    :param default: The default value to return if the path is not found.
    :return: The extracted value or the default value.
    """
    try:
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, {})
            elif isinstance(data, list):
                data = data[int(key)]
            else:
                return default
        return data
    except (KeyError, IndexError, TypeError):
        return default


def verify_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.
    Raise and return 403 if not authorized.
    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    print("Verifying signature.")
    if not signature_header:
        raise SignatureVerificationError(403, detail="x-hub-signature-256 header is missing!")
    _, github_signature = signature_header.split('=', 1)
    encoded_key = bytes(secret_token, 'utf-8')
    encoded_payload = payload_body.encode('utf-8')
    mac = hmac.new(encoded_key, msg=encoded_payload, digestmod=hashlib.sha256)
    calculated_signature = mac.hexdigest()
    return hmac.compare_digest(calculated_signature, github_signature)



def get_bot_id(client):
    try:
        response = client.auth_test()
        if response["ok"]:
            print("Got bot ID...")
            return response["bot_id"]
        else:
            print("Failed to get bot ID:", response["error"])
            return None
    except Exception as e:
        print("Error occurred:", e)
        return None
