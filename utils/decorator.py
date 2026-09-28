from functools import wraps

from rest_framework import status
from rest_framework.response import Response

from utils.helpers import get_error_from_serializer_errors_obj, get_error_response
from utils.messages import FailureMessage


def validate_input_data(serializer, many=False):
    def function_decorator(fn):
        @wraps(fn)
        def validate(*args, **kwargs):
            serialized_obj = serializer(data=args[1].data, many=many)
            if not serialized_obj.is_valid():
                error_message = get_error_from_serializer_errors_obj(serialized_obj.errors) or \
                    FailureMessage.INVALID_INPUT_DATA
                return Response(get_error_response(error_message, errors=serialized_obj.errors),
                                status=status.HTTP_400_BAD_REQUEST)
            kwargs["validated_data"] = serialized_obj.data
            return fn(*args, **kwargs)
        return validate
    return function_decorator
