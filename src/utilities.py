import hmac
import hashlib
from difflib import SequenceMatcher
import time
import re
import github_tools, utilities


# function to calculate similarity score between two strings
def similarity_score(a, b):
    return SequenceMatcher(None, a, b).ratio()


def extract_chars(payload):
    title_matches = r"#\d+ (.+?)>"
    pr_title_match = re.findall(title_matches, payload)
    pr_title = pr_title_match[0]

    user_that_clicked = utilities.extract_value(payload, ["user", "id"])

    button_id_fetch = utilities.extract_value(payload, ["actions", "action_id"])
    pr_number = button_id_fetch.split("-")[0]

    return pr_title, pr_number, user_that_clicked


# wait until the github checks are complete
def wait_for_checks(conf):
    while True:
        time.sleep(2)
        all_checks = github_tools.get_pr_checks(conf)
        if all_checks:
            if are_checks_completed(all_checks["check_runs"]):
                if are_checks_successful(all_checks["check_runs"]):
                    status = "Passing"
                    return status
                else:
                    status = ":red-cross-mark:"
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
    if not signature_header:
        raise Exception(
            status_code=403, detail="x-hub-signature-256 header is missing!"
        )
    hash_object = hmac.new(
        secret_token.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise Exception(status_code=403, detail="Request signatures didn't match!")


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
