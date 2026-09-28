import re


def safe_get(obj, path, default_value=None):
    result = default_value
    for key in path.split("."):
        try:
            result = getattr(obj, key)
            obj = result
        except AttributeError:
            return default_value
    return result


def get_error_response(message, errors=None):
    data = {"status": False, "message": message}
    if errors is not None:
        data["errors"] = errors
    return data


def get_success_response(message=None, data=None):
    response_data = {"status": True}
    if message:
        response_data["message"] = message
    if data is not None:
        response_data["data"] = data
    return response_data


def get_error_from_serializer_errors_obj(errors):
    for field, field_errors in errors.items():
        if isinstance(field_errors, list) and field_errors:
            return f"{field}: {field_errors[0]}"
    return None


def normalize_place_name(name):
    # CSV has "Saint Johns" / "Mc Donald", census has "St. Johns" / "McDonald"
    name = name.lower().replace(".", "").replace("'", "").replace("-", " ")
    name = re.sub(r"\bsainte?\b", "st", name)
    name = re.sub(r"\bmc\s+", "mc", name)
    return re.sub(r"\s+", " ", name).strip()
