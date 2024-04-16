INVALID_ACTIONS = [
    "assigned",
    "auto_merge_disabled",
    "auto_merge_enabled",
    "unassigned", 
    "converted_to_draft", 
    "milestoned",
    "demilestoned", 
    "dequeued", 
    "edited", 
    "enqueued", 
    "labeled", 
    "locked", 
    "ready_for_review", 
    "review_request_removed", 
    "review_requested",
    "synchronized", 
    "unlabeled", 
    "unlocked"
]

def skipped_action(action):
    return action in INVALID_ACTIONS