# Stack adapters

Load only the section for the detected stack. Each adapter gets import edges from the tool the stack already has, and applies SKILL.md step 4 to them. Sketches show the shape: adapt names and roots, and keep the check one file. Add libraries at their current stable release, looked up in the registry.

`paths` in a unit are what the model has: directories for components, directories or packages for modules (`travelai.poi.**`, `src/orders/**`). Normalize them to the stack's module names.

## The empty-selection trap

`verify` and every AC command must fail when the filter matches nothing.

| Runner | Filter that matches nothing |
|---|---|
| Gradle `--tests` | fails ✓ |
| pytest `-k` | exit 5 ✓ |
| Go `go test -run` | **exit 0**: wrap |
| Cargo `cargo test <name>` | **exit 0**: wrap |
| Vitest / Jest `-t` | may exit 0: check, wrap if so |
| `flutter test --name` | check, wrap if needed |

Wrap = `scripts/ac <pattern>`: runs the filter with a machine-readable reporter, shows the output, exits 1 when zero tests ran. AC commands then use the wrapper.

## Python: grimp in a pytest

`verify` = `uv run ruff check && uv run pytest` (whatever the project uses). Add `grimp` as a dev dependency.

```python
# tests/test_architecture.py
import hashlib, json, pathlib, re
import grimp

GATE = json.loads(pathlib.Path("docs/architecture.gate.json").read_text())
ROOT = "shop"  # top-level package
SOURCE = pathlib.Path("src")
LIBS = {"persistence": {"sqlalchemy", "psycopg", "django"}, "client": {"httpx", "requests", "aiohttp", "boto3"},
        "messaging": {"kafka", "pika", "celery"}, "server": {"fastapi", "flask"}}

def module_of(path):
    path = re.sub(r"(/\*\*|\.\*\*|/)$", "", path)
    return path.removeprefix(f"{SOURCE}/").replace("/", ".")

PREFIXES = {module_of(p): u for u, spec in GATE["units"].items() for p in spec["paths"]}

def owner(module):
    return next((PREFIXES[p] for p in sorted(PREFIXES, key=len, reverse=True)
                 if module == p or module.startswith(p + ".")), None)

def violations():
    graph = grimp.build_graph(ROOT, include_external_packages=True)
    bad = set()
    for mod in graph.modules:
        if not (mod == ROOT or mod.startswith(ROOT + ".")):
            continue
        unit = owner(mod)
        if unit is None:  # an empty __init__ or a file without imports can't break a boundary
            if graph.find_modules_directly_imported_by(mod):
                bad.add(f"{mod}: unowned")
            continue
        allowed = {unit, *GATE["units"][unit]["imports"]}
        for imp in graph.find_modules_directly_imported_by(mod):
            if imp.split(".")[0] == ROOT:
                if (to := owner(imp)) and to not in allowed:
                    bad.add(f"{unit} -> {to}: import not allowed")
            for kind, libs in LIBS.items():
                if imp.split(".")[0] in libs and kind not in GATE["units"][unit]["io"]:
                    bad.add(f"{unit}: {kind} import")
    return bad

def test_gate_is_fresh():
    model = hashlib.sha256(pathlib.Path("docs/architecture.yaml").read_bytes()).hexdigest()
    assert model == GATE["model_sha256"], "model changed: run gate.py"

def test_architecture():
    path = pathlib.Path("docs/architecture.baseline")
    base = set(path.read_text().splitlines()) if path.exists() else set()
    found = violations()
    assert not found - base, "new:\n" + "\n".join(sorted(found - base))
    assert not base - found, "fixed, remove from the baseline:\n" + "\n".join(sorted(base - found))
```

## JVM — Kotlin / Java, Gradle: ArchUnit

`verify` = a Gradle task depending on `check`. Add `archunit` and a JSON library as test dependencies. Use ArchUnit as the class graph, and the same walk as the Python sketch:

```kotlin
val classes = ClassFileImporter().withImportOption(DoNotIncludeTests()).importPackages(ROOT)
for (c in classes) for (d in c.directDependenciesFromSelf) {
    val to = d.targetClass.name  // owner(c.name) -> owner(to), library prefixes for I/O
}
```

- **Component paths** are directories; give the test a map from each to its root package.
- **Libraries:** persistence `jakarta.persistence`, `javax.persistence`, `org.springframework.data`, `java.sql`, `org.jetbrains.exposed`, `org.jooq`; client `java.net.http`, `okhttp3`, `io.ktor.client`, `org.springframework.web.client`, `retrofit2`; messaging `org.apache.kafka`, `org.springframework.kafka`, `org.springframework.amqp`, `com.google.cloud.pubsub`; server `org.springframework.web.bind.annotation`, `io.ktor.server`, `jakarta.ws.rs`.
- **Gradle:** declare `docs/architecture.yaml`, the gate file and the baseline as inputs of the test task, or a model-only change is skipped as up to date. Set `testLogging { exceptionFormat = FULL }`, and don't prove checks with `-q`.

## TypeScript / JavaScript: dependency-cruiser

`verify` = `tsc --noEmit && eslint . && vitest run`. An `architecture.test.ts` runs `depcruise src --output-type json`, and walks `modules[].source` → `dependencies[].resolved`.

- **Libraries:** persistence `pg`, `prisma`, `@prisma`, `typeorm`, `drizzle-orm`, `mongoose`, `knex`; client `axios`, `got`, `ky`, `undici`, `node-fetch`, `@aws-sdk`; messaging `kafkajs`, `amqplib`, `bullmq`; server `express`, `fastify`, `@nestjs`, `hono`, `koa`.
- Global `fetch` isn't an import, so it can't be caught here.

## Go: a test over `go/packages`

`verify` = `go vet ./... && golangci-lint run && go test ./...`, plus the AC wrapper. `arch_test.go` loads `./...` with `golang.org/x/tools/go/packages` (`NeedName|NeedImports`) and walks each package's imports.

- **Libraries:** persistence `database/sql`, `gorm.io`; server and client both use `net/http`, so treat it as `server` and allow clients through a wrapper package.

## Rust, Swift: the manifest is the boundary

Make each unit a crate or target, so the compiler enforces dependencies. The test compares `cargo metadata --format-version 1` or `swift package dump-package` with `imports`.

## Dart / Flutter

`test/architecture_test.dart` scans `import 'package:<app>/…'` lines under each unit's paths. Dart imports are regular enough for that to be exact.

## CI — GitHub Actions

```yaml
# .github/workflows/verify.yml
name: verify
on:
  pull_request:
  push:
    branches: [main]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      # one toolchain setup step with dependency caching:
      #   JVM: actions/setup-java (temurin) + gradle/actions/setup-gradle
      #   TS:  pnpm/action-setup + actions/setup-node (cache: pnpm)
      #   Py:  astral-sh/setup-uv (enable-cache: true)
      #   Go:  actions/setup-go
      - run: <the verify command>
```

Pin each action to its current major from the action's README.
