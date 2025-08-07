# Dagger Services Guide

This guide demonstrates how to work with services in Dagger Functions, including binding services, exposing them to hosts, and managing their lifecycle.

## Table of Contents
1. [Bind and Use Services in Dagger Functions](#bind-and-use-services-in-dagger-functions)
2. [Expose Services to the Host](#expose-services-to-the-host)
3. [Expose Host Services to Dagger Functions](#expose-host-services-to-dagger-functions)
4. [Use Service Endpoints](#use-service-endpoints)
5. [Create Transient Services for Unit Tests](#create-transient-services-for-unit-tests)
6. [Start and Stop Services](#start-and-stop-services)
7. [Create Interdependent Services](#create-interdependent-services)

## Bind and Use Services in Dagger Functions

Create an HTTP service in one function and consume it from another using service bindings.

```python
import dagger
from dagger import dag, function, object_type


@object_type
class MyModule:
    @function
    def http_service(self) -> dagger.Service:
        """Start and return an HTTP service."""
        return (
            dag.container()
            .from_("python")
            .with_workdir("/srv")
            .with_new_file("index.html", "Hello, world!")
            .with_exposed_port(8080)
            .as_service(args=["python", "-m", "http.server", "8080"])
        )

    @function
    async def get(self) -> str:
        """Send a request to an HTTP service and return the response."""
        return await (
            dag.container()
            .from_("alpine")
            .with_service_binding("www", self.http_service())
            .with_exec(["wget", "-O-", "http://www:8080"])
            .stdout()
        )
```

**Usage:**
```bash
dagger -c get
```

## Expose Services to the Host

Create a service that can be accessed from the host machine.

```python
import dagger
from dagger import dag, function, object_type


@object_type
class MyModule:
    @function
    def http_service(self) -> dagger.Service:
        """Start and return an HTTP service."""
        return (
            dag.container()
            .from_("python")
            .with_workdir("/srv")
            .with_new_file("index.html", "Hello, world!")
            .with_exposed_port(8080)
            .as_service(args=["python", "-m", "http.server", "8080"])
        )
```

**Usage:**

Expose on default port:
```bash
dagger -c 'http-service | up'
curl localhost:8080
```

Expose on custom port:
```bash
dagger -c 'http-service | up --ports 9000:8080'
curl localhost:9000
```

## Expose Host Services to Dagger Functions

Access services running on the host from within Dagger Functions.

```python
from typing import Annotated

import dagger
from dagger import Doc, dag, function, object_type


@object_type
class MyModule:
    @function
    async def user_list(
        self, svc: Annotated[dagger.Service, Doc("Host service")]
    ) -> str:
        """Send a query to a MariaDB service and return the response."""
        return await (
            dag.container()
            .from_("mariadb:10.11.2")
            .with_service_binding("db", svc)
            .with_exec(
                [
                    "/usr/bin/mysql",
                    "--user=root",
                    "--password=secret",
                    "--host=db",
                    "-e",
                    "SELECT Host, User FROM mysql.user",
                ]
            )
            .stdout()
        )
```

**Usage:**
```bash
dagger -c 'user-list tcp://localhost:3306'
```

## Use Service Endpoints

Manually start a service and retrieve its endpoint for direct access.

```python
from dagger import dag, function, object_type


@object_type
class MyModule:
    @function
    async def get(self) -> str:
        # start NGINX service
        service = dag.container().from_("nginx").with_exposed_port(80).as_service()
        await service.start()

        # wait for service endpoint
        endpoint = await service.endpoint(port=80, scheme="http")

        # send HTTP request to service endpoint
        return await dag.http(endpoint).contents()
```

**Usage:**
```bash
dagger -c get
```

## Create Transient Services for Unit Tests

Set up temporary services for testing purposes, such as a database for Drupal unit tests.

```python
from dagger import dag, function, object_type


@object_type
class MyModule:
    @function
    async def test(self) -> str:
        """Run unit tests against a database service."""
        # get MariaDB base image
        mariadb = (
            dag.container()
            .from_("mariadb:10.11.2")
            .with_env_variable("MARIADB_USER", "user")
            .with_env_variable("MARIADB_PASSWORD", "password")
            .with_env_variable("MARIADB_DATABASE", "drupal")
            .with_env_variable("MARIADB_ROOT_PASSWORD", "root")
            .with_exposed_port(3306)
            .as_service(use_entrypoint=True)
        )

        # get Drupal base image
        # install additional dependencies
        drupal = (
            dag.container()
            .from_("drupal:10.0.7-php8.2-fpm")
            .with_exec(
                [
                    "composer",
                    "require",
                    "drupal/core-dev",
                    "--dev",
                    "--update-with-all-dependencies",
                ]
            )
        )

        # add service binding for MariaDB
        # run kernel tests using PHPUnit
        return await (
            drupal.with_service_binding("db", mariadb)
            .with_env_variable("SIMPLETEST_DB", "mysql://user:password@db/drupal")
            .with_env_variable("SYMFONY_DEPRECATIONS_HELPER", "disabled")
            .with_workdir("/opt/drupal/web/core")
            .with_exec(["../../vendor/bin/phpunit", "-v", "--group", "KernelTests"])
            .stdout()
        )
```

**Usage:**
```bash
dagger -c test
```

## Start and Stop Services

Explicitly manage service lifecycle with start and stop operations.

```python
import contextlib

import dagger
from dagger import dag, function, object_type


@contextlib.asynccontextmanager
async def managed_service(svc: dagger.Service):
    """Start and stop a service."""
    yield await svc.start()
    await svc.stop()


@object_type
class MyModule:
    @function
    async def redis_service(self) -> str:
        """Explicitly start and stop a Redis service."""
        redis_srv = dag.container().from_("redis").with_exposed_port(6379).as_service()

        # start Redis ahead of time so it stays up for the duration of the test
        # and stop when done
        async with managed_service(redis_srv) as redis_srv:
            # create Redis client container
            redis_cli = (
                dag.container()
                .from_("redis")
                .with_service_binding("redis-srv", redis_srv)
            )

            args = ["redis-cli", "-h", "redis-srv"]

            # set value
            setter = await redis_cli.with_exec([*args, "set", "foo", "abc"]).stdout()

            # get value
            getter = await redis_cli.with_exec([*args, "get", "foo"]).stdout()

            return setter + getter
```

**Usage:**
```bash
dagger -c redis-service
```

## Create Interdependent Services

Run multiple services that depend on each other with custom hostnames for inter-service communication.

```python
import dagger
from dagger import dag, function, object_type


@object_type
class MyModule:
    @function
    async def services(self) -> dagger.Service:
        """Run two services which are dependent on each other"""
        svc_a = (
            dag.container()
            .from_("nginx")
            .with_exposed_port(80)
            .as_service(
                args=[
                    "sh",
                    "-c",
                    "nginx & while true; do curl svcb:80 && sleep 1; done",
                ]
            )
            .with_hostname("svca")
        )

        await svc_a.start()

        svc_b = (
            dag.container()
            .from_("nginx")
            .with_exposed_port(80)
            .as_service(
                args=[
                    "sh",
                    "-c",
                    "nginx & while true; do curl svca:80 && sleep 1; done",
                ]
            )
            .with_hostname("svcb")
        )

        await svc_b.start()

        return svc_b
```

**Usage:**
```bash
dagger -c 'services | up --ports 8080:80'
```

## Tutorial: Testing FastAPI Services with Dagger

This tutorial demonstrates how to create and test a FastAPI service using the patterns above. We'll build a complete testing solution that follows Python best practices.

### Step 1: Create the API Service

First, we create a function that builds and returns our FastAPI application as a service:

```python
@function
def api_service(self, source: dg.Directory, python_version: str = "3.12") -> dg.Service:
    """Create a FastAPI service for testing."""
    return (
        self.test_container(source, python_version)
        .with_exec(["uv", "pip", "install", "-e", "."])
        .with_exposed_port(8000)
        .as_service(args=["python", "-m", "hello_world"])
    )
```

This function:
- Uses our base test container with uv pre-installed
- Installs the application and its dependencies
- Exposes port 8000 where FastAPI runs
- Returns a Dagger service that can be bound by other containers

### Step 2: Test the API Service

Next, we create a function to test our API endpoints:

```python
@function
async def test_api_service(
    self, source: dg.Directory, python_version: str = "3.12"
) -> str:
    """Test the API service by sending HTTP requests."""
    # Create the API service
    api_svc = self.api_service(source, python_version)
    
    # Create a test client container
    test_client = (
        dag.container()
        .from_("alpine:latest")
        .with_exec(["apk", "add", "--no-cache", "curl", "jq"])
        .with_service_binding("api", api_svc)
    )
    
    # Test endpoints
    root_response = await (
        test_client
        .with_exec(["curl", "-s", "http://api:8000/"])
        .stdout()
    )
    
    return f"API Response: {root_response}"
```

Key points:
- The API service is bound with alias "api"
- Test client accesses the service via `http://api:8000`
- Service starts automatically when first accessed
- Cleanup happens automatically after the function completes

### Step 3: Run Integration Tests

For more complex testing, run pytest against the live service:

```python
@function
async def integration_tests(
    self, source: dg.Directory, python_version: str = "3.12"
) -> str:
    """Run integration tests against a live API service."""
    api_svc = self.api_service(source, python_version)
    
    return await (
        self.test_container(source, python_version)
        .with_service_binding("api", api_svc)
        .with_env_variable("API_BASE_URL", "http://api:8000")
        .with_exec(["uv", "pip", "install", "-e", ".[test]"])
        .with_exec(["pytest", "tests/e2e", "-v"])
        .stdout()
    )
```

This approach:
- Provides the API URL via environment variable
- Runs actual pytest integration tests
- Tests interact with the real API service
- Ensures complete isolation between test runs

### Usage Examples

Test the API service:
```bash
dagger -c test-api-service --source .
```

Run integration tests:
```bash
dagger -c integration-tests --source .
```

Expose the API to the host for debugging:
```bash
dagger -c 'api-service --source . | up --ports 8080:8000'
```

### Best Practices

1. **Reliability First**: Keep services simple and focused
2. **Type Hints**: Use proper type annotations for all parameters
3. **Documentation**: Include comprehensive docstrings
4. **Error Handling**: Services should fail fast with clear errors
5. **Isolation**: Each test run gets fresh service instances
6. **Performance**: Use caching (uv cache) to speed up builds

## Key Concepts

### Service Bindings
- Services can be bound to containers using aliases (e.g., `with_service_binding("www", service)`)
- Bound services are accessible within the container using the alias as hostname

### Service Lifecycle
- Services can be started implicitly when used or explicitly with `start()`
- Use context managers for proper cleanup with `stop()`
- Services persist for the duration they're needed

### Host Integration
- Services can be exposed to the host using the `up` command
- Host services can be accessed from Dagger using TCP URLs
- Custom port mappings allow flexible host-container communication

### Testing Patterns
- Create transient services for isolated testing environments
- Services are automatically cleaned up after test completion
- Multiple services can be composed for complex testing scenarios