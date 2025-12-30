
import sys
import anyio
import dagger

async def main():
    async with dagger.Connection(dagger.Config(log_output=sys.stderr)) as client:
        # 1. Base Image
        src = client.host().directory(".")

        # 2. Setup Python Environment
        python = (
            client.container()
            .from_("python:3.11-slim")
            .with_exec(["apt-get", "update"])
            .with_exec(["apt-get", "install", "-y", "git", "gcc", "libpq-dev"]) # Postgres deps
            .with_workdir("/app")
            .with_file("pyproject.toml", src.file("auth_platform/pyproject.toml"))
            .with_file("poetry.lock", src.file("auth_platform/poetry.lock"))
            .with_exec(["pip", "install", "poetry", "pytest", "httpx", "psycopg2-binary"])
            .with_exec(["poetry", "config", "virtualenvs.create", "false"])
            .with_exec(["poetry", "install", "--no-root", "--no-interaction"])
        )

        # 3. Mount Code
        python = python.with_directory("/app/auth_platform", src.directory("auth_platform"))

        # 4. Run Tests
        # We start a postgres service for integration tests?
        # For simplicity in this demo, we can rely on SQLite or skip DB heavy tests
        # Or better: Spin up a sidecar postgres.

        postgres = (
            client.container()
            .from_("postgres:15-alpine")
            .with_env_variable("POSTGRES_PASSWORD", "postgres")
            .with_env_variable("POSTGRES_DB", "auth_db")
            .with_expose_port(5432)
        )


        test_runner = (
            python
            .with_service_binding("db", postgres)
            .with_env_variable("DATABASE_URL", "postgresql://postgres:postgres@db:5432/auth_db")
            .with_env_variable("ENVIRONMENT", "testing")
            .with_exec(["pytest", "auth_platform/auth_platform_tests/test_tier_gating.py", "-v"])
        )

        # 5. Build Containers (Checklist 5.1/5.3)
        print("Building Auth Service container...")
        auth_build = (
            client.container()
            .build(src.directory("auth_platform"))
        )

        print("Building Frontend container...")
        frontend_build = (
            client.container()
            .build(src.directory("dev-portal-ui"))
        )

        # Execute
        print("Running specific tier gating tests...")
        output = await test_runner.stdout()
        print(output)

        # Trigger builds (force evaluation)
        await auth_build.sync()
        await frontend_build.sync()
        print("Container builds successful.")


if __name__ == "__main__":
    anyio.run(main)
