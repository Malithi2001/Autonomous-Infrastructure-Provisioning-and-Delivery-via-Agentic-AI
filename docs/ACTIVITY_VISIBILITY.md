# Dashboard and audit visibility

Every signed-in role lands on the dashboard. Members see their own recent
actions and pending approval requests, with shortcuts permitted for their role.
Admins see the shared operations dashboard, including system and webhook work.

Both `/api/v1/audit` and `/api/v1/executions` enforce ownership in the backend:

| Role | Audit list and details | Dashboard | Approval requests |
| --- | --- | --- | --- |
| Viewer | Own actions | Personal | Own requests, read only |
| Developer | Own actions | Personal | Review and decide own authorized work |
| Operator | Own actions | Personal | Shared queue for authorized review |
| Admin | All actors, including system actions | Shared operations | All requests |

Members cannot broaden their audit access with the `actor` query parameter.
Requests for another member's execution ID return 404. Filters for tool, status,
date, and source operate inside the member's ownership boundary. Admins can
filter by an exact actor username on the audit page.

Ownership uses the existing `requested_by` identity: the authenticated unique
username, falling back to the JWT subject when no username is present. A member
without either identity is rejected; their query is never left unfiltered.
System and webhook records remain visible to admins rather than being assigned
to an arbitrary member.

Personal dashboards request `/approvals?scope=mine`. Viewers and developers are
restricted to their own requests even when requesting `scope=all`. Developers
have `approvals:decide:own`, which permits approving or rejecting their own work
without granting access to the shared queue. Operators and admins retain the
shared queue and existing approval gates.

Developers can generate workflow YAML, scan repositories, and request workflow
pull requests through **Repositories**. Their workflow PRs always create a
pending approval, including when the optional demo HITL setting is disabled.
No repository mutation occurs until a human approves. They may approve their
own workflow PRs, safe workflow fix PRs, and existing development/staging
container restart requests. Shell commands, elevated Docker operations,
workflow dispatch, and account administration retain their privileged review
requirements. Developers may reject their own operational requests that need
an operator/admin to approve; account administration remains admin-only.

Both approval list and detail responses include `can_approve` and `can_reject`
for the authenticated reviewer. The frontend uses these capabilities to display
the appropriate controls, while the decision endpoint independently enforces
ownership and tool authorization. Another member's approval ID returns 404.
Concurrent decisions are serialized and expired or completed requests cannot
execute again. Requester and decision-maker attribution remain in the audit.

The audit response retains `requested_by` and additionally reports
`approval_decided_by` and `approval_status` from the linked approval. The UI
shows the requester and reviewer separately, so approved work is not wrongly
attributed solely to the requester. No database migration is required.

Dashboard activity statistics describe the latest five records from the last
seven days, rather than claiming to be totals for all historical work.

Regression coverage is in `backend/tests/test_audit_filtering.py`, including
member isolation, both API aliases, actor overrides, detail access, missing
identity, admin filtering, personal approval scope, and reviewer attribution.
