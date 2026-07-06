"""Unit tests for browsix init module."""

from __future__ import annotations

import pytest
import yaml

from browsix.init import (
    TEMPLATE_NAMES,
    TEMPLATES,
    generate_config,
    interactive_init,
    list_templates,
)


@pytest.mark.unit
class TestListTemplates:
    """Tests for list_templates."""

    def test_returns_all_templates(self) -> None:
        """Test that all templates are listed."""
        templates = list_templates()
        assert len(templates) == len(TEMPLATE_NAMES)
        for name, desc in templates:
            assert name in TEMPLATE_NAMES
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_template_names_match_keys(self) -> None:
        """Test that TEMPLATE_NAMES matches TEMPLATES keys."""
        assert set(TEMPLATE_NAMES) == set(TEMPLATES.keys())


@pytest.mark.unit
class TestGenerateConfig:
    """Tests for generate_config."""

    def test_screenshot_template(self) -> None:
        """Test screenshot template generates valid YAML."""
        result = generate_config("screenshot")
        config = yaml.safe_load(result)
        assert "actions" in config
        assert len(config["actions"]) == 1
        assert "screenshot" in config["actions"][0]
        assert config["actions"][0]["screenshot"]["url"] == "https://example.com"

    def test_pdf_template(self) -> None:
        """Test pdf template generates valid YAML."""
        result = generate_config("pdf")
        config = yaml.safe_load(result)
        assert "pdf" in config["actions"][0]
        assert config["actions"][0]["pdf"]["paper"] == "a4"

    def test_scrape_template(self) -> None:
        """Test scrape template generates valid YAML."""
        result = generate_config("scrape")
        config = yaml.safe_load(result)
        assert "scrape" in config["actions"][0]
        assert "urls" in config["actions"][0]["scrape"]

    def test_eval_template(self) -> None:
        """Test eval template generates valid YAML."""
        result = generate_config("eval")
        config = yaml.safe_load(result)
        assert "eval" in config["actions"][0]
        assert config["actions"][0]["eval"]["expression"] == "document.title"

    def test_multi_step_template(self) -> None:
        """Test multi-step template has multiple actions."""
        result = generate_config("multi-step")
        config = yaml.safe_load(result)
        actions = config["actions"]
        assert len(actions) == 4
        assert "navigate" in actions[0]
        assert "click" in actions[1]
        assert "type" in actions[2]
        assert "screenshot" in actions[3]

    def test_cookies_template(self) -> None:
        """Test cookies template generates valid YAML."""
        result = generate_config("cookies")
        config = yaml.safe_load(result)
        actions = config["actions"]
        assert len(actions) == 2
        assert "navigate" in actions[0]
        assert "eval" in actions[1]

    def test_url_override(self) -> None:
        """Test URL override replaces default URL."""
        result = generate_config("screenshot", url="https://custom.com")
        config = yaml.safe_load(result)
        assert config["actions"][0]["screenshot"]["url"] == "https://custom.com"

    def test_url_override_scrape(self) -> None:
        """Test URL override replaces urls list in scrape."""
        result = generate_config("scrape", url="https://custom.com")
        config = yaml.safe_load(result)
        assert config["actions"][0]["scrape"]["urls"] == ["https://custom.com"]

    def test_expression_override(self) -> None:
        """Test expression override for scrape/eval."""
        result = generate_config("eval", expression="document.body.innerHTML")
        config = yaml.safe_load(result)
        assert config["actions"][0]["eval"]["expression"] == "document.body.innerHTML"

    def test_expression_override_scrape(self) -> None:
        """Test expression override for scrape."""
        result = generate_config("scrape", expression="document.querySelector('h1').textContent")
        config = yaml.safe_load(result)
        assert "h1" in config["actions"][0]["scrape"]["expression"]

    def test_selector_override(self) -> None:
        """Test selector override for multi-step click."""
        result = generate_config("multi-step", selector="#my-button")
        config = yaml.safe_load(result)
        assert config["actions"][1]["click"]["selector"] == "#my-button"

    def test_text_override(self) -> None:
        """Test text override for multi-step type."""
        result = generate_config("multi-step", text="custom text")
        config = yaml.safe_load(result)
        assert config["actions"][2]["type"]["text"] == "custom text"

    def test_all_overrides_multi_step(self) -> None:
        """Test all overrides applied to multi-step template."""
        result = generate_config(
            "multi-step",
            url="https://test.com",
            selector="#submit",
            text="hello world",
        )
        config = yaml.safe_load(result)
        assert config["actions"][0]["navigate"]["url"] == "https://test.com"
        assert config["actions"][1]["click"]["selector"] == "#submit"
        assert config["actions"][2]["type"]["text"] == "hello world"

    def test_unknown_template_raises(self) -> None:
        """Test unknown template raises ValueError."""
        with pytest.raises(ValueError, match="Unknown template"):
            generate_config("nonexistent")

    def test_generated_yaml_is_parseable(self) -> None:
        """Test that generated YAML is always parseable."""
        for name in TEMPLATE_NAMES:
            result = generate_config(name)
            config = yaml.safe_load(result)
            assert isinstance(config, dict)
            assert "actions" in config
            assert isinstance(config["actions"], list)
            assert len(config["actions"]) > 0


@pytest.mark.unit
class TestInteractiveInit:
    """Tests for interactive_init."""

    def test_screenshot_template_interactive(self) -> None:
        """Test interactive wizard with screenshot template."""
        inputs = iter(["1", "https://custom.com"])
        outputs: list[str] = []

        result = interactive_init(
            input_fn=lambda _prompt: next(inputs),
            output_fn=lambda msg: outputs.append(msg),
        )
        config = yaml.safe_load(result)
        assert config["actions"][0]["screenshot"]["url"] == "https://custom.com"

    def test_scrape_template_interactive(self) -> None:
        """Test interactive wizard with scrape template."""
        inputs = iter(["3", "https://data.com", "document.querySelector('h1').textContent"])
        outputs: list[str] = []

        result = interactive_init(
            input_fn=lambda _prompt: next(inputs),
            output_fn=lambda msg: outputs.append(msg),
        )
        config = yaml.safe_load(result)
        assert config["actions"][0]["scrape"]["urls"] == ["https://data.com"]
        assert "h1" in config["actions"][0]["scrape"]["expression"]

    def test_template_by_name(self) -> None:
        """Test selecting template by name instead of number."""
        inputs = iter(["pdf", "https://docs.com"])
        outputs: list[str] = []

        result = interactive_init(
            input_fn=lambda _prompt: next(inputs),
            output_fn=lambda msg: outputs.append(msg),
        )
        config = yaml.safe_load(result)
        assert config["actions"][0]["pdf"]["url"] == "https://docs.com"

    def test_default_url(self) -> None:
        """Test that empty input uses default URL."""
        inputs = iter(["1", ""])
        outputs: list[str] = []

        result = interactive_init(
            input_fn=lambda _prompt: next(inputs),
            output_fn=lambda msg: outputs.append(msg),
        )
        config = yaml.safe_load(result)
        assert config["actions"][0]["screenshot"]["url"] == "https://example.com"

    def test_invalid_selection_raises(self) -> None:
        """Test invalid numeric selection raises ValueError."""
        inputs = iter(["99", ""])
        outputs: list[str] = []

        with pytest.raises(ValueError, match="Invalid selection"):
            interactive_init(
                input_fn=lambda _prompt: next(inputs),
                output_fn=lambda msg: outputs.append(msg),
            )

    def test_invalid_template_name_raises(self) -> None:
        """Test invalid template name raises ValueError."""
        inputs = iter(["nonexistent"])
        outputs: list[str] = []

        with pytest.raises(ValueError, match="Unknown template"):
            interactive_init(
                input_fn=lambda _prompt: next(inputs),
                output_fn=lambda msg: outputs.append(msg),
            )
