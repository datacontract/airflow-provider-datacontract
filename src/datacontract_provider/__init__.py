__version__ = "0.1.0"


def get_provider_info():
    return {
        "package-name": "airflow-provider-datacontract",
        "name": "Data Contract",
        "description": "Test data contracts with the Data Contract CLI from Airflow DAGs.",
        "versions": [__version__],
        "integrations": [
            {
                "integration-name": "Data Contract CLI",
                "external-doc-url": "https://cli.datacontract.com",
                "tags": ["software"],
            }
        ],
        "operators": [
            {
                "integration-name": "Data Contract CLI",
                "python-modules": ["datacontract_provider.operators.datacontract"],
            }
        ],
        "extra-links": ["datacontract_provider.links.TestResultsLink"],
    }
