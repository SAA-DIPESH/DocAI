from typing import Any


# def extract_token_usage(response: Any) -> dict[str, int | None]:
#     usage = getattr(response, "usage_metadata", None)

#     if usage is None:
#         response_metadata = getattr(response, "response_metadata", {}) or {}
#         usage = response_metadata.get("token_usage") or response_metadata.get("usage")

#     if usage is None:
#         return {
#             "input_tokens": None,
#             "output_tokens": None,
#             "total_tokens": None,
#         }

#     if not isinstance(usage, dict):
#         usage = dict(usage)

#     return {
#         "input_tokens": usage.get("input_tokens")
#         or usage.get("prompt_tokens"),
#         "output_tokens": usage.get("output_tokens")
#         or usage.get("completion_tokens"),
#         "total_tokens": usage.get("total_tokens"),
#     }
