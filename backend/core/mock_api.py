import pytest
import pytest_mock
from backend.core.external_api import Client
from backend.core.config import config
from backend.core.logging_config import setup_logging
import logging

logger = logging.getLogger(__name__)
setup_logging()

@pytest.fixture
def mock_external_api_client(mocker: pytest_mock.MockerFixture):
    """Fixture to mock the external API client."""
    mock_client = mocker.Mock()
    mocker.patch.object(Client, 'fetch_data', return_value={"data": "mocked data"})
    logger.info("Mock external API client created.")
    return mock_client