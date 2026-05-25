"""Tests for the frontend config model and loader."""

from kadathic_cryptogram.config import FrontendConfig, load_frontend_config


class TestFrontendConfigDefaults:
    def test_default_title(self) -> None:
        cfg = FrontendConfig()
        assert cfg.ui.title == "Kadathic Cryptogram"

    def test_default_cipher(self) -> None:
        cfg = FrontendConfig()
        assert cfg.ui.default_cipher == "substitution"

    def test_default_solve_config(self) -> None:
        cfg = FrontendConfig()
        assert cfg.solve.agent_id == "cryptogram_solver"
        assert cfg.solve.max_retries == 3
        assert cfg.solve.max_ciphertext_length == 2000
        assert cfg.solve.min_ciphertext_length == 50

    def test_default_backend(self) -> None:
        cfg = FrontendConfig()
        assert cfg.backend.project_config_path == "./agentfoundry.yaml"
        assert cfg.backend.project_id == "cryptogram_project"

    def test_load_without_file_returns_defaults(self) -> None:
        cfg = load_frontend_config(path="/nonexistent/path/config.yaml")
        assert cfg.ui.title == "Kadathic Cryptogram"


class TestFrontendConfigCustom:
    def test_custom_title(self) -> None:
        cfg = FrontendConfig.model_validate({
            "ui": {"title": "My Custom Cryptogram"}
        })
        assert cfg.ui.title == "My Custom Cryptogram"

    def test_custom_solve_retries(self) -> None:
        cfg = FrontendConfig.model_validate({
            "solve": {"max_retries": 5}
        })
        assert cfg.solve.max_retries == 5

    def test_non_defaults_are_not_none(self) -> None:
        cfg = FrontendConfig()
        assert cfg.ui.title is not None
        assert cfg.solve.max_retries > 0
