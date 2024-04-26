## Bot!

Screenshots soon!

### Background

Created to see how much more useful info and usability you can get out of a GitHub integration with Slack, specifically for PRs, and interacting with those. This uses GitHub webhooks for PRs, which is very chatty, so bear that in mind before setting this up under an org on a private repo.  

Still in progress, but the features below are what's working right now.

### Features

When a GitHub PR is created:  
  
In DM:
  - we send a DM with `Approve` and `Request Changes` buttons to the assignee(s)
    - if multiple assignees we send a DM to all
  - includes the file changes in the message if less than 4k characters
  - also includes assignees, the PR number and title

In the channel:
  - kinda sorta imitates the official integration output design
  - assigned users tagged by Slack ID (approx match GH user vs Okta email unless a `ASSIGNEE_EMAILS` secret exists in GCP)
  - includes links to the file diffs in the PR
  - includes a comment button (like the official integration)
  - tests for PR check results
    - colorbar changes depending on status (for checks and buttons)

In DM:
  - when `Approve` or `Request Changes` is clicked, the buttons change to `Merge`/`Squash`.
    - upon approval, the message gets removed from the other assignees that didn't click approve.
    - Once either button is clicked at that stage, we replace the buttons with a message that the PR has been merged/squashed, in both DM and channel.

### Setup

#### You'll need:
- A GitHub App with token to access your team and repo (needs to be able to read teams)
- GitHub webhooks to trigger on Pull Requests
- An Okta token to access your team members
- A Slack app
  - permissions: send msg, edit and retrieve history from a supposed private Slack channel

#### Steps
1. Complete the `config.yaml` keys and edit `deployment.yml` if you are using GCF
      - or use the same keys in the `.yaml` file as env vars wherever you host this
      - Run the workflow!

2. Setup a gcloud function and edit your Slack app for interaction and events  
3. Wait for any output!
