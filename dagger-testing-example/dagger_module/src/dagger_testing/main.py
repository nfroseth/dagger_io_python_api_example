"""Dagger testing module for Python applications with FastAPI.

This module provides containerized testing capabilities using Dagger,
focusing on simplicity and reliability as guiding principles.
"""

import asyncio

import dagger as dg
from dagger import dag, function, object_type


@object_type
class DaggerTestingExample:
    """A testing module for Python applications with FastAPI using uv.

    This module demonstrates:
    - Running unit tests in isolated containers
    - Testing across multiple Python versions
    - Creating and testing API services
    - Service binding patterns for integration testing
    """

    # Base container creation
    @function
    def test_container(
        self, source: dg.Directory, python_version: str = "3.12"
    ) -> dg.Container:
        """Create a base container with uv and source code.

        Args:
            source: Directory containing the source code
            python_version: Python version to use (default: 3.12)

        Returns:
            Container configured with uv and source code
        """
        uv_cache = dag.cache_volume("uv")

        return (
            dag.container()
            .from_(f"ghcr.io/astral-sh/uv:python{python_version}-bookworm-slim")
            .with_mounted_cache("/root/.cache/uv", uv_cache)
            .with_directory("/app", source)
            .with_workdir("/app")
            .with_env_variable("UV_SYSTEM_PYTHON", "1")
        )

    # Unit testing functions
    @function
    async def unit_test(
        self, source: dg.Directory, python_version: str = "3.12"
    ) -> str:
        """Run unit tests with pytest.

        Args:
            source: Directory containing the source code
            python_version: Python version to use

        Returns:
            Test output from pytest
        """
        return await (
            self.test_container(source, python_version)
            .with_exec(["uv", "pip", "install", "-e", ".[test]"])
            .with_exec(["pytest", "tests/unit", "-v", "--tb=short"])
            .stdout()
        )

    @function
    async def unit_test_matrix(
        self, source: dg.Directory, versions: str = "3.10,3.11,3.12"
    ) -> str:
        """Run unit tests concurrently on multiple Python versions.

        Args:
            source: Directory containing the source code
            versions: Comma-separated list of Python versions

        Returns:
            Formatted test results for all versions
        """
        version_list = [v.strip() for v in versions.split(",")]

        async def test_version(version: str) -> tuple[str, str]:
            """Test a specific Python version."""
            try:
                result = await self.unit_tests(source, version)
                return version, f"Python {version}: PASSED\n{result}"
            except Exception as e:
                return version, f"Python {version}: FAILED\n{str(e)}"

        # Run all versions concurrently
        results = await asyncio.gather(*[test_version(v) for v in version_list])

        # Format results
        output_lines = ["=== MULTI-VERSION TEST RESULTS ===", ""]
        for _, result in results:
            output_lines.extend([result, "=" * 50, ""])

        return "\n".join(output_lines)

    @function
    async def run_test(
        self, source: dg.Directory, path: str, python_version: str = "3.12"
    ) -> str:
        """Run tests at a specific path.

        Args:
            source: Directory containing the source code
            path: Path to test files or directory
            python_version: Python version to use

        Returns:
            Test output from pytest
        """
        return await (
            self.test_container(source, python_version)
            .with_exec(["uv", "pip", "install", "-e", ".[test]"])
            .with_exec(["pytest", path, "-v", "--tb=short"])
            .stdout()
        )

    # Service-related functions
    @function
    def api_service(
        self, source: dg.Directory, python_version: str = "3.12"
    ) -> dg.Service:
        """Create a FastAPI service for testing.

        This function demonstrates how to:
        1. Build a container with the FastAPI application
        2. Install dependencies using uv
        3. Expose the service on port 8000
        4. Return it as a Dagger service for binding

        The service can be used in other functions via service binding,
        allowing integration tests to run against a live API instance.

        Args:
            source: Directory containing the FastAPI application code
            python_version: Python version to use (default: 3.12)

        Returns:
            A Dagger service running the FastAPI application
        """
        return (
            self.test_container(source, python_version)
            .with_exec(["uv", "pip", "install", "-e", "."])
            .with_exposed_port(8000)
            .as_service(args=["python", "-m", "hello_world"])
        )

    @function
    async def test_api_service(
        self, source: dg.Directory, python_version: str = "3.12"
    ) -> str:
        """Test the API service by sending HTTP requests.

        This function demonstrates a complete service testing pattern:
        1. Start the FastAPI service using api_service()
        2. Bind it to a test container with alias 'api'
        3. Send HTTP requests to verify functionality
        4. Return formatted test results

        The test container uses curl to make requests, demonstrating
        how services communicate via hostnames in Dagger.

        Args:
            source: Directory containing the source code
            python_version: Python version to use

        Returns:
            Test results showing API responses
        """
        # Create the API service
        api_svc = self.api_service(source, python_version)

        # Create a test client container
        test_client = (
            dag.container()
            .from_("alpine:latest")
            .with_exec(["apk", "add", "--no-cache", "curl", "jq"])
            .with_service_binding("api", api_svc)
        )

        # Test the root endpoint
        root_response = await test_client.with_exec(
            ["curl", "-s", "http://api:8000/"]
        ).stdout()

        # Test the health endpoint
        health_response = await test_client.with_exec(
            ["curl", "-s", "http://api:8000/health"]
        ).stdout()

        # Format pretty JSON output
        root_pretty = await test_client.with_exec(
            ["sh", "-c", f"echo '{root_response}' | jq ."]
        ).stdout()

        health_pretty = await test_client.with_exec(
            ["sh", "-c", f"echo '{health_response}' | jq ."]
        ).stdout()

        # Build result string
        result_lines = [
            "=== API SERVICE TEST RESULTS ===",
            "",
            "Root Endpoint (GET /):",
            root_pretty,
            "",
            "Health Endpoint (GET /health):",
            health_pretty,
            "",
            "All endpoints responded successfully!",
        ]

        return "\n".join(result_lines)

    @function
    async def integration_test(
        self, source: dg.Directory, python_version: str = "3.12"
    ) -> str:
        """Run integration tests against a live API service.

        This advanced example shows how to:
        1. Start the API service in the background
        2. Run pytest integration tests that connect to the service
        3. Use service bindings for test isolation

        Perfect for testing real HTTP interactions, database connections,
        or other service dependencies in a controlled environment.

        Args:
            source: Directory containing the source code
            python_version: Python version to use

        Returns:
            Integration test results from pytest
        """
        # Start the API service
        api_svc = self.api_service(source, python_version)

        # Run integration tests with the API service bound
        return await (
            self.test_container(source, python_version)
            .with_service_binding("api", api_svc)
            .with_env_variable("API_BASE_URL", "http://api:8000")
            .with_exec(["uv", "pip", "install", "-e", ".[test]"])
            .with_exec(["pytest", "tests/e2e", "-v", "--tb=short"])
            .stdout()
        )
