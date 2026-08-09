from bolt_on.cli.main import main
from bolt_on.configuration import ProductConfiguration
from bolt_on.core import ContainerIdentity, ContractError
from bolt_on.docker_adapter import DockerEnvironment, FakeDockerObservationAdapter
from bolt_on.modules import ModuleDeclaration, ModuleRegistry
from bolt_on.receipts import CanonicalReceipt, canonical_json_bytes


def test_configuration_defaults_fail_closed():
    config = ProductConfiguration()
    config.validate()
    assert config.observation_only is True
    assert config.telemetry_enabled is False
    assert config.enabled_modules == ()


def test_exact_container_identity():
    identity = ContainerIdentity("a" * 64)
    assert identity.full_id == "a" * 64
    try:
        ContainerIdentity("a" * 12)
    except ContractError:
        pass
    else:
        raise AssertionError("short identity accepted")


def test_canonical_receipt_vector():
    receipt = CanonicalReceipt("stage0.example", 1, {"b": 2, "a": 1})
    assert canonical_json_bytes(receipt.body()) == b'{"payload":{"a":1,"b":2},"receipt_type":"stage0.example","schema_version":1}'
    assert receipt.digest() == "27512887656836eb9acf44756e12c23ffdf9369d0d8cda5490f7ea16b41b60cf"


def test_fake_adapter_is_deterministic():
    adapter = FakeDockerObservationAdapter(DockerEnvironment(False, None, "not connected"))
    assert adapter.check_environment() == DockerEnvironment(False, None, "not connected")
    assert adapter.list_containers() == ()


def test_module_registry_is_disabled_by_default():
    registry = ModuleRegistry()
    registry.register(ModuleDeclaration("incidents", "0.1", 1))
    assert registry.declarations()[0].default_enabled is False


def test_version_command(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out == "bolt 0.3.0.dev0\n"
