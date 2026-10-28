# Stack adapters

Load only the section for the detected stack. Each adapter reads `architecture.yaml` itself where
the tool can, so the model stays the one place to change. Sketches show the shape — adapt names,
paths and packages to the project, and keep the check one file.

## The empty-selection trap

`verify` and every AC command must fail when the filter matches nothing. Check before trusting:

| Runner | Filter that matches nothing |
|---|---|
| Gradle `--tests` | fails ("No tests found for given includes") ✓ |
| pytest `-k` | exit 5 ✓ |
| Go `go test -run` | **exit 0** — wrap |
| Cargo `cargo test <name>` | **exit 0** — wrap |
| Vitest / Jest `-t` | may exit 0 with all tests skipped — check, wrap if so |

Wrap = a small script (`scripts/ac <pattern>`) that runs the filter with a machine-readable
reporter (`go test -json`, `vitest --reporter=json`, `cargo test -- -Z unstable-options --format json`
or by counting "test result: ok. N passed"), shows the normal output, and exits 1 when zero tests ran.
The AC command in specs then uses the wrapper.

## JVM — Kotlin / Java, Gradle: ArchUnit

`verify` = a Gradle task depending on `check` (tests, lint such as detekt/ktlint/spotless).
Add `archunit-junit5` and `snakeyaml` as test dependencies. Package of a component = its `path`
below the source root (`src/main/kotlin/com/shop/orders` → `com.shop.orders`).

```kotlin
class ArchitectureTest {
    private val model: Map<String, Any> = Yaml().load(File("architecture.yaml").readText())
    private val classes = ClassFileImporter().withImportOption(DoNotIncludeTests()).importPackages(ROOT)

    @Suppress("UNCHECKED_CAST")
    private val components = model["components"] as Map<String, Map<String, Any>>
    private fun pkg(c: Map<String, Any>) = (c["path"] as String).substringAfter("kotlin/").replace('/', '.') + ".."

    @Test fun dependencies() = components.forEach { (name, c) ->
        val allowed = setOf(name) + (c["depends_on"] as? List<String>).orEmpty()
        val others = components.filterKeys { it !in allowed }.values.map(::pkg)
        if (others.isEmpty()) return@forEach
        freeze(noClasses().that().resideInAPackage(pkg(c))
            .should().dependOnClassesThat().resideInAnyPackage(*others.toTypedArray())
            .because("$name: not in depends_on")).check(classes)
    }
}
```

- **I/O placement:** the same loop with `resideInAnyPackage(PERSISTENCE)` for components owning no
  entity — `jakarta.persistence..`, `javax.persistence..`, `org.springframework.data..`, `java.sql..`,
  `org.jetbrains.exposed..`, `org.jooq..`. HTTP clients — `java.net.http..`, `okhttp3..`,
  `io.ktor.client..`, `org.springframework.web.client..`, `retrofit2..`. Server —
  `org.springframework.web.bind.annotation..`, `io.ktor.server..`, `jakarta.ws.rs..`.
- **Rules:** one `@Test fun R1_...()` per rule; `checked_by: ArchitectureTest.R1_...`.
- **Baseline:** `FreezingArchRule.freeze(...)`; `src/test/resources/archunit.properties` sets
  `freeze.store.default.path=archunit_store`. Allow store creation only for the first run, then set
  `freeze.store.default.allowStoreCreation=false` and commit `archunit_store/`.
- **Gradle:** declare `architecture.yaml` and `src/main` as inputs of the test task, or a model-only
  change leaves the check up to date and skipped. Set `testLogging { exceptionFormat = FULL }` so a
  failure prints the model-named message; `-q` hides it, so don't prove checks with `-q`.
- **Kotlin-only alternative:** Konsist, which works on source files, so components map by path, not package.

## TypeScript / JavaScript: dependency-cruiser

`verify` = `"verify": "tsc --noEmit && eslint . && vitest run && depcruise src --ignore-known"`
(use the project's runner and package manager). Keep component paths plain directories.

```js
// .dependency-cruiser.cjs — reads the model on every run
const { parse } = require("yaml");
const model = parse(require("fs").readFileSync("architecture.yaml", "utf8"));
const comps = Object.entries(model.components);
const paths = (c) => [].concat(c.path);
const re = (ps) => `^(${ps.map((p) => p.replace(/[.]/g, "\\.")).join("|")})/`;

const forbidden = comps.flatMap(([name, c]) => {
  const allowed = new Set([name, ...(c.depends_on || [])]);
  const others = comps.filter(([n]) => !allowed.has(n)).flatMap(([, o]) => paths(o));
  return others.length ? [{ name: `${name}: not in depends_on`, severity: "error",
    from: { path: re(paths(c)) }, to: { path: re(others) } }] : [];
});
module.exports = { forbidden, options: { tsConfig: { fileName: "tsconfig.json" } } };
```

- **I/O placement:** rules with `to: { path: "^node_modules/(pg|@prisma|prisma|typeorm|drizzle-orm|mongoose|knex)/" }`
  from components owning no entity; clients `(axios|got|ky|undici|node-fetch|@aws-sdk)`; servers
  `(express|fastify|@nestjs|hono|koa)`. Global `fetch` isn't an import — it can't be caught here;
  list it as a manual rule if it matters.
- **Unowned code:** `{ name: "unowned", from: { path: "^src/", pathNot: re(allPaths) }, to: {} }`.
- **Rules:** a vitest file `architecture.test.ts` with `it("R2_...")` for what depcruise can't say.
- **Baseline:** `depcruise src --output-type baseline > .dependency-cruiser-known-violations.json`.

## Python: grimp in a pytest

`verify` = `uv run ruff check && uv run pyright && uv run pytest` (whatever the project uses).
Add `grimp` and `pyyaml` as dev dependencies. Module of a component = its `path` without the
source root, slashes → dots.

```python
# tests/test_architecture.py
import grimp, pathlib, yaml

MODEL = yaml.safe_load(pathlib.Path("architecture.yaml").read_text())
COMPS = {n: c["path"].removeprefix("src/").replace("/", ".") for n, c in MODEL["components"].items()}
GRAPH = grimp.build_graph(next(iter(COMPS.values())).split(".")[0])
BASE_FILE = pathlib.Path("tests/architecture-baseline.txt")   # known violations, one per line
BASELINE = set(BASE_FILE.read_text().splitlines()) if BASE_FILE.exists() else set()

def owner(module):
    return next((n for n, p in COMPS.items() if module == p or module.startswith(p + ".")), None)

def test_dependencies():
    bad = set()
    for name, c in MODEL["components"].items():
        allowed = {name, *c.get("depends_on", [])}
        for m in GRAPH.find_descendants(COMPS[name]) | {COMPS[name]}:
            for imp in GRAPH.find_modules_directly_imported_by(m):
                if (o := owner(imp)) and o not in allowed:
                    bad.add(f"{m} -> {imp}: {name} -> {o} not in depends_on")
    assert not bad - BASELINE, "\n".join(sorted(bad - BASELINE))
```

- **I/O placement:** the same walk over imports of `sqlalchemy`, `psycopg`, `django.db`, `peewee`
  (persistence); `httpx`, `requests`, `aiohttp`, `boto3` (clients); `fastapi`, `flask`, `django.urls` (server).
  `build_graph(..., include_external_packages=True)` makes them visible.
- **Rules:** `def test_R2_...()` in the same file.

## Go: a test over `go/packages`

`verify` = `make verify`: `go vet ./... && golangci-lint run && go test ./...`, plus the AC wrapper
(Go passes on an empty `-run`). Import path of a component = module path + `/` + its `path`.
`arch_test.go` loads `./...` with `golang.org/x/tools/go/packages` (mode `NeedName|NeedImports`),
reads the model with `gopkg.in/yaml.v3`, and fails on imports outside `depends_on` and on
`database/sql`, `gorm.io`, `net/http` (client vs server by `http.Client` / `http.Handle` use — or
treat `net/http` as server-only and allow clients via a wrapper package).

## Rust, Swift: the manifest is the boundary

Make each component a crate (Cargo workspace) or a target (SwiftPM). The compiler then enforces
declared dependencies, and the check is a test that compares the manifest with the model:
`cargo metadata --format-version 1` or `swift package dump-package` → each component's dependencies
must be a subset of `depends_on`. Drift in either file fails.

## Dart / Flutter

A `test/architecture_test.dart` reading the model with the `yaml` package and scanning
`import 'package:<app>/<component>/…'` lines under each component's path. Dart imports are
regular enough for that to be exact.

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
      #   Go:  actions/setup-go (cache is on by default)
      - run: <the verify command>
```

Pin each action to its current major from the action's README. Public repos run free; private
repos use the account's included minutes.
