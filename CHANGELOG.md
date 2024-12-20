# CHANGELOG


## v1.4.1 (2024-12-20)

### Bug Fixes

- Fix and rename util function to get product id from filename
  ([`0c91d4b`](https://github.com/nasaharvest/glam-api/commit/0c91d4bfa8579217c3c0fba21149fef8686977c1))


## v1.4.0 (2024-12-20)

### Features

- Add function to add ProductRaster records from existing raster storage
  ([`a388e03`](https://github.com/nasaharvest/glam-api/commit/a388e030f49d7a81e82a4c86da8f915adcd58df0))


## v1.3.1 (2024-12-20)

### Bug Fixes

- Modify save method for ProductRaster
  ([`19a034e`](https://github.com/nasaharvest/glam-api/commit/19a034e722152940477e61dc6cad6f071a3e0c68))


## v1.3.0 (2024-12-19)

### Features

- Add utility functions to extract the date and product_id from a filename
  ([`6895687`](https://github.com/nasaharvest/glam-api/commit/68956870ab69abe10a7d683a6bc927bae6d222b9))


## v1.2.0 (2024-12-19)

### Build System

- Add glam-processing as dependency
  ([`7a0c92e`](https://github.com/nasaharvest/glam-api/commit/7a0c92e0edc9eac386cc8c6a4b8cc5f78d3f6804))

- Bump minimum python version to 3.11 and bump django from 4.2.14 to 4.2.17
  ([`38f4a1c`](https://github.com/nasaharvest/glam-api/commit/38f4a1cae28e2efd85921fd11097d651fba6f93a))

- Update glam-processing dependency
  ([`33038d6`](https://github.com/nasaharvest/glam-api/commit/33038d650d4bd34302488419c8404d92e35f68f8))

### Features

- Add utility function for creating aws session environment variables with MFA
  ([`b0d6726`](https://github.com/nasaharvest/glam-api/commit/b0d67264fbda51bbdad2d5a66f925c26442ea1a6))

### Refactoring

- Add example gdal/goes configuration settings for geodjango
  ([`63ee312`](https://github.com/nasaharvest/glam-api/commit/63ee31275872eef72834b454cc1c17cc916193c0))

- Rename ProductRaster file_object directory
  ([`29cc3ff`](https://github.com/nasaharvest/glam-api/commit/29cc3ffa8e68b51c92b0b4b45e87a3952366cdad))


## v1.1.4 (2024-12-11)

### Bug Fixes

- Update s3 private media storage class
  ([`fa7e7b3`](https://github.com/nasaharvest/glam-api/commit/fa7e7b3dc12f4acb63a17e24b3304c3520eb3ce6))

### Refactoring

- Move django-storages configuration to local_settings
  ([`8251873`](https://github.com/nasaharvest/glam-api/commit/8251873603163eaf2ca02b97c594108ae1febb92))


## v1.1.3 (2024-12-11)

### Bug Fixes

- Remove django-storages s3 session profile option
  ([`d804eb0`](https://github.com/nasaharvest/glam-api/commit/d804eb080561163ed6562409ffb038b02801fa89))


## v1.1.2 (2024-12-10)

### Bug Fixes

- Adjust django storages s3 session profile configuration
  ([`3b67fe1`](https://github.com/nasaharvest/glam-api/commit/3b67fe125dbcd74bba6fd3498b713fffc5071e10))


## v1.1.1 (2024-12-10)

### Bug Fixes

- Add django-storages session profile configuration option
  ([`bdd9343`](https://github.com/nasaharvest/glam-api/commit/bdd9343175d3ff6d1628bdfe50aa3bd163dbfde2))


## v1.1.0 (2024-12-10)

### Features

- Add new default S3 media storage
  ([`5ed3710`](https://github.com/nasaharvest/glam-api/commit/5ed37107aa6fd17257c75a77caa4cc9880eff580))


## v1.0.3 (2024-11-25)

### Bug Fixes

- Rename apprunner yaml file with correct extension
  ([`49335ed`](https://github.com/nasaharvest/glam-api/commit/49335ed223cf8f067ac8896be5704801d72b378c))


## v1.0.2 (2024-11-25)

### Bug Fixes

- Change apprunner config location
  ([`d6a015a`](https://github.com/nasaharvest/glam-api/commit/d6a015a1929f18e642c5c608849de14da53e3197))


## v1.0.1 (2024-11-25)

### Bug Fixes

- Change apprunner config location
  ([`2cb2e02`](https://github.com/nasaharvest/glam-api/commit/2cb2e02fd9484ca9679a089641d54a38f58aef32))

### Build System

- Add apprunner configuration file
  ([`abc5646`](https://github.com/nasaharvest/glam-api/commit/abc564698bb0daccae38b60c13b4741dbb611f84))

- Update .dockerignore
  ([`2491270`](https://github.com/nasaharvest/glam-api/commit/2491270b984982983179f534189baae53e24afb8))


## v1.0.0 (2024-11-19)

### Build System

- Merge pull request #18 from nasaharvest/upgrade
  ([`a2e92e6`](https://github.com/nasaharvest/glam-api/commit/a2e92e62c1792ddb2889fa910a2ee5fa21b7b15d))

Major upgrade and reconfiguration of glam-api code base.

BREAKING CHANGE: Upgrade Django version: 3.2.15 -> ^4.2. BREAKING CHANGE: Replace requirements files
  with poetry for dependency management.

### BREAKING CHANGES

- Upgrade Django version: 3.2.15 -> ^4.2. BREAKING CHANGE: Replace requirements files with poetry
  for dependency management.


## v0.2.0 (2022-10-20)


## v0.1.0 (2022-10-13)
