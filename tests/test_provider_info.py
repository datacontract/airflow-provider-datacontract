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


def test_react_app_bundle_shipped():
    from pathlib import Path

    import datacontract_provider
    from datacontract_provider.plugin import DataContractPlugin

    bundle = Path(datacontract_provider.__file__).parent / "static" / "main.umd.cjs"
    assert bundle.is_file()
    assert "AirflowPlugin" in bundle.read_text()
    if DataContractPlugin.react_apps:  # present when FastAPI is available (Airflow 3)
        assert DataContractPlugin.react_apps[0]["bundle_url"] == "/datacontract/static/main.umd.cjs"
        assert DataContractPlugin.react_apps[0]["url_route"] == "datacontract-results"
