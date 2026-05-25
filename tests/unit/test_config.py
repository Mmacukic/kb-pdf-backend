from app.core.config import Settings


def build_settings(**overrides) -> Settings:
    defaults = {
        "app_name": "test",
        "environment": "test",
        "mongo_uri": "mongodb://localhost:27017",
        "mongo_db": "test",
        "jwt_secret_key": "secret",
        "jwt_algorithm": "HS256",
        "jwt_access_token_expire_minutes": 60,
        "admin_username": "admin",
        "admin_password": "admin123",
        "user_username": "user",
        "user_password": "user123",
        "minio_endpoint": "localhost:9000",
        "minio_access_key": "minioadmin",
        "minio_secret_key": "minioadmin",
        "minio_bucket_name": "pdf-documents",
        "openai_api_key": "test",
        "qdrant_url": "http://localhost:6333",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_cors_origins_parse_comma_separated_values():
    settings = build_settings(
        cors_origins=(
            "http://localhost:5173, "
            "http://127.0.0.1:5173,"
            "http://0.0.0.0:5173,"
            "http://[::1]:5173"
        )
    )

    assert settings.allowed_cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173",
        "http://[::1]:5173",
    ]


def test_cors_origin_regex_covers_local_development_hosts():
    settings = build_settings()

    assert settings.cors_origin_regex is not None
    assert "localhost" in settings.cors_origin_regex
    assert "127" in settings.cors_origin_regex
    assert "0\\.0\\.0\\.0" in settings.cors_origin_regex
    assert "\\[::1\\]" in settings.cors_origin_regex
