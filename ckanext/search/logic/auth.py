from ckan.types import Context, DataDict, AuthResult


def search(context: Context, data_dict: DataDict) -> AuthResult:
    """
    All users can search by default.
    """
    return {"success": True}
