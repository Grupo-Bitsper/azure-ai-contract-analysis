"""ACL extraction for security trimming (resolves D-7).

Takes a SharePoint item and returns the effective list of Entra group IDs
and user object IDs that can read the document. SharePoint-native groups
(Owners/Members/Visitors) are expanded recursively to their Entra members.
"""

from __future__ import annotations

from . import graph_client


def extract_principals_for_item(
    site_id: str,
    list_id: str,
    list_item_id: str,
) -> tuple[list[str], list[str]]:
    """Returns (group_ids, user_ids) for a SharePoint list item. Returns
    empty lists on error (fail-open for dev; fail-closed should be enforced
    at query time by the Foundry agent in Fase 6.1b)."""
    try:
        perms = graph_client.get_item_permissions(site_id, list_id, list_item_id)
    except Exception:
        return [], []

    group_ids: set[str] = set()
    user_ids: set[str] = set()

    for perm in perms.get("value", []):
        granted = perm.get("grantedToV2") or perm.get("grantedTo") or {}
        identities = perm.get("grantedToIdentitiesV2") or perm.get("grantedToIdentities") or []
        if granted and not identities:
            identities = [granted]

        for identity in identities:
            if not isinstance(identity, dict):
                continue

            user = identity.get("user") or {}
            if user.get("id"):
                user_ids.add(user["id"])

            group = identity.get("group") or {}
            if group.get("id"):
                group_ids.add(group["id"])

            sp_group = identity.get("siteGroup") or identity.get("sharePointGroup") or {}
            sp_group_id = sp_group.get("id")
            if sp_group_id:
                try:
                    members = graph_client.get_sharepoint_group_members(site_id, sp_group_id)
                    for m in members:
                        if m.get("@odata.type", "").endswith("user"):
                            mid = m.get("id")
                            if mid:
                                user_ids.add(mid)
                        elif m.get("@odata.type", "").endswith("group"):
                            gid = m.get("id")
                            if gid:
                                group_ids.add(gid)
                except Exception:
                    pass

    return sorted(group_ids), sorted(user_ids)
