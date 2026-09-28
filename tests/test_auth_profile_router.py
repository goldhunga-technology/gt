import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from gt.auth.routers._auth_profile_router import create_profile_router
from gt.auth.schemas._auth_profile_schemas import AuthChangeLanguageSchema


def get_endpoint(router, method: str, path: str):
    for route in router.routes:
        if route.path == path and method in (route.methods or set()):
            return route.endpoint
    raise AssertionError(f"No route {method} {path}")


def parse(response) -> dict:
    return json.loads(response.body)


class TestAuthChangeLanguageSchema:
    def test_valid_language(self):
        schema = AuthChangeLanguageSchema(language="es")
        assert schema.language == "es"

    def test_rejects_empty_language(self):
        with pytest.raises(ValidationError):
            AuthChangeLanguageSchema(language="")

    def test_rejects_too_long_language(self):
        with pytest.raises(ValidationError):
            AuthChangeLanguageSchema(language="toolonglanguagecode")


class TestProfileRouterEndpoints:
    def make_auth(self, *, user_service):
        auth = MagicMock()
        services = MagicMock()
        services.user = user_service
        auth.get_services.return_value = services
        auth.get_db_session = MagicMock()
        return auth

    async def test_change_language_endpoint_success(self):
        user = MagicMock()
        user.language = "en"

        updated_user = MagicMock()
        updated_user.language = "ne"

        user_service = MagicMock()
        user_service.update_language = AsyncMock(return_value=updated_user)

        auth = self.make_auth(user_service=user_service)
        router = create_profile_router(auth=auth)

        endpoint = get_endpoint(router, "PATCH", "/language")

        session = AsyncMock()
        body = AuthChangeLanguageSchema(language="ne")

        response = await endpoint(
            body=body,
            session=session,
            current_user=user,
        )

        assert response.status_code == 200
        parsed = parse(response)
        assert parsed["data"]["language"] == "ne"
        assert parsed["message"] == "Language updated successfully."
        user_service.update_language.assert_awaited_once_with(user=user, language="ne")

    async def test_update_profile_endpoint_includes_language(self):
        user = MagicMock()
        updated_user = MagicMock()
        updated_user.uuid = "user-uuid"
        updated_user.full_name = "Jane Doe"
        updated_user.email = "jane@example.com"
        updated_user.avatar = None
        updated_user.avatar_bg = "#ffffff"
        updated_user.language = "fr"

        user_service = MagicMock()
        user_service.update_profile = AsyncMock(return_value=updated_user)

        auth = self.make_auth(user_service=user_service)
        router = create_profile_router(auth=auth)

        endpoint = get_endpoint(router, "PATCH", "/profile")

        session = AsyncMock()
        body = SimpleNamespace(
            model_dump=lambda **kwargs: {"language": "fr"},
        )

        response = await endpoint(
            body=body,
            session=session,
            current_user=user,
        )

        assert response.status_code == 200
        parsed = parse(response)
        assert parsed["data"]["language"] == "fr"
