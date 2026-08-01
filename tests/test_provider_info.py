from datacontract_provider import get_provider_info


def test_provider_info_shape():
    info = get_provider_info()
    assert info["package-name"] == "airflow-provider-datacontract"
    assert info["versions"]
    assert "datacontract_provider.links.TestResultsLink" in info["extra-links"]


def test_plugin_importable():
    from datacontract_provider.plugin import DataContractPlugin

    assert DataContractPlugin.name == "datacontract"
    assert DataContractPlugin.operator_extra_links
