# CHANGELOG


## v1.11.8 (2025-05-19)

### Bug Fixes

- Update boundary feature graphic generation
  ([`2fc88b2`](https://github.com/nasaharvest/glam-api/commit/2fc88b267e7de95615fe24b17fba5ec5e1bec8e8))

### Build System

- Bump glam-processing version to 0.4.3
  ([`08bd7fe`](https://github.com/nasaharvest/glam-api/commit/08bd7feb58d5e93a7d18410331f9ba445ab27cf9))

- Bump glam-processing version to 0.4.4
  ([`2a98b73`](https://github.com/nasaharvest/glam-api/commit/2a98b733f7353b39b3d6f2f55e83b3f33e20976d))


## v1.11.7 (2025-02-18)

### Bug Fixes

- Create output directory if not exists; add general per product error handling
  ([`b898694`](https://github.com/nasaharvest/glam-api/commit/b898694a77e286ed92f00e5a385245392b4ecbbc))


## v1.11.6 (2025-02-18)

### Bug Fixes

- Set default vi value to None; fix esi name handling
  ([`f729fc7`](https://github.com/nasaharvest/glam-api/commit/f729fc73872d1ca766a7525f361677c96ab92e91))

### Build System

- Bump glam-processing version to 0.4.2
  ([`1593f3b`](https://github.com/nasaharvest/glam-api/commit/1593f3b6ec55a04a05f512627417e6c6664f7c86))

- Update glam-processing version
  ([`9c1fb6a`](https://github.com/nasaharvest/glam-api/commit/9c1fb6ad21cde8553c41b96d998d0cad5d193049))


## v1.11.5 (2025-02-14)

### Bug Fixes

- Update glam-processing version
  ([`4a8843c`](https://github.com/nasaharvest/glam-api/commit/4a8843cea03b4ea303404a254d92d36dcc1a5d01))


## v1.11.4 (2025-02-13)

### Bug Fixes

- Update utility function imports
  ([`7a6451b`](https://github.com/nasaharvest/glam-api/commit/7a6451b629e136c71d924f430ad7399c4f7aff9b))


## v1.11.3 (2025-02-13)

### Bug Fixes

- Update utility function imports
  ([`c2f0ccd`](https://github.com/nasaharvest/glam-api/commit/c2f0ccd5f424817aba69bf41f86c30b065f3ea90))


## v1.11.2 (2025-02-13)

### Bug Fixes

- Remove circular imports
  ([`e78bf93`](https://github.com/nasaharvest/glam-api/commit/e78bf9335be9c9501ab1c72a2092087386ad1d3f))


## v1.11.1 (2025-02-13)

### Bug Fixes

- Fix management command imports
  ([`fd72232`](https://github.com/nasaharvest/glam-api/commit/fd7223293c5cd5738a0602e3d4ffdebaf28e128a))

### Refactoring

- Move glam utiliity functions to tasks.py
  ([`f1c893c`](https://github.com/nasaharvest/glam-api/commit/f1c893c6c140b36725243c92a42897956a2ba5d6))

- Rearrange utility functions
  ([`83ed576`](https://github.com/nasaharvest/glam-api/commit/83ed576138e95dd9028e907ca59b4b7fb3ad3383))


## v1.11.0 (2025-02-13)

### Features

- Add management command to automate download and ingest of new product rasters
  ([`4073fcf`](https://github.com/nasaharvest/glam-api/commit/4073fcf122f205fe9fadf0aacf21d351e8a34246))

- Add utility function to download new product rasters
  ([`b3a36c5`](https://github.com/nasaharvest/glam-api/commit/b3a36c5c26b28e5c2bdaf22d447bb5041b2d4d8b))


## v1.10.1 (2025-01-28)

### Bug Fixes

- Add baseline queries for custom geometry
  ([`29975bd`](https://github.com/nasaharvest/glam-api/commit/29975bd031a201fad6683632e26c436afa343312))


## v1.10.0 (2025-01-24)

### Features

- Add baseline queries
  ([`fec3db7`](https://github.com/nasaharvest/glam-api/commit/fec3db7d1c735232cfbf0aa0f0f5317f5da5d3ed))

- Add cache controll setting
  ([`8550102`](https://github.com/nasaharvest/glam-api/commit/85501020f02e0db42344475134e9c9ea0718638b))

### Refactoring

- Add per view caching to tile retrieval
  ([`3a4b2a5`](https://github.com/nasaharvest/glam-api/commit/3a4b2a5af9b9444fee603f3c6df3384bdc552768))

- Use django caching api instead of cache_page method
  ([`55d36fd`](https://github.com/nasaharvest/glam-api/commit/55d36fd3b026803299695904eac58e634e948c82))


## v1.9.2 (2025-01-21)

### Bug Fixes

- Fix DEBUG setting from env variable
  ([`69e382e`](https://github.com/nasaharvest/glam-api/commit/69e382e34415f598467f497c84b9d23a6ba4b34f))


## v1.9.1 (2025-01-21)

### Bug Fixes

- Fix utility function for getting product id from filename
  ([`ccbe027`](https://github.com/nasaharvest/glam-api/commit/ccbe02794bda28024c7b12d26a03e626d41d5a4a))


## v1.9.0 (2025-01-21)

### Bug Fixes

- Update AnomalyBaselineRaster save method
  ([`4afdcbc`](https://github.com/nasaharvest/glam-api/commit/4afdcbc4e0485c1e3b23d3caecf2963ffae11c5c))

### Features

- Add utility function to add anomaly baseline rasters from storage
  ([`de4fa57`](https://github.com/nasaharvest/glam-api/commit/de4fa576fb6fb9d160c5e6ac0930cd9514f70219))


## v1.8.2 (2025-01-21)

### Bug Fixes

- Update utility function for getting product id from filename
  ([`4b41a1c`](https://github.com/nasaharvest/glam-api/commit/4b41a1c8704805eff1aaecdefe6c3922ef520923))


## v1.8.1 (2025-01-17)

### Bug Fixes

- Hande TileOutsideBounds error
  ([`c733527`](https://github.com/nasaharvest/glam-api/commit/c733527d971d2ebc4c74cdeb2db457835dc562d1))

### Build System

- Add alernative django local settings file name patterns to .gitignore
  ([`02868ed`](https://github.com/nasaharvest/glam-api/commit/02868ed7cc81a9b747d7a455a9c3a9c01624a38a))

### Refactoring

- Add per view caching to boundary feature queries
  ([`aef6072`](https://github.com/nasaharvest/glam-api/commit/aef60720f591b2184dece1eb7ebbef910f088325))

- Rename sample settings files
  ([`415a18a`](https://github.com/nasaharvest/glam-api/commit/415a18a92e48472a9847e7f40a8c3856062826a9))


## v1.8.0 (2025-01-15)

### Features

- Updated utility funtion to ingest geoboundaries features from existing layers
  ([`fd9fb42`](https://github.com/nasaharvest/glam-api/commit/fd9fb42e541045b4f26f4222be6576ac6a596157))


## v1.7.0 (2025-01-13)

### Features

- Add updated utility function to bulk load geoboundaries layers
  ([`c21e52f`](https://github.com/nasaharvest/glam-api/commit/c21e52f032911877e3b66f4690f5ee848ddb11da))


## v1.6.2 (2025-01-09)

### Bug Fixes

- Add GDAL configuration options to all COGReader functions
  ([`41ae773`](https://github.com/nasaharvest/glam-api/commit/41ae773aa3c4a1b87440cab27cef8997ee13d521))


## v1.6.1 (2025-01-09)

### Bug Fixes

- Update utility function to create BoundaryFeatures from BoundaryLayer geojson file
  ([`c6263b0`](https://github.com/nasaharvest/glam-api/commit/c6263b05ee1e182980c714bfa9b51d74a0182e3d))

### Build System

- Add no-binary installation configuration for rasterio
  ([`83e1c08`](https://github.com/nasaharvest/glam-api/commit/83e1c08b0a020e27eed2a45602ce750352a04c0a))

- Change python docker image to slim-bookworm
  ([`e2b9f64`](https://github.com/nasaharvest/glam-api/commit/e2b9f64b5eea6c5c0addda18c79935b3d5e2fe65))

- Force rasterio no-binary installation with pip in Dockerfile
  ([`8e2a1ea`](https://github.com/nasaharvest/glam-api/commit/8e2a1eaba4de19cc46f71641eb680634067486b3))

### Refactoring

- Change BoundaryLayer file fields to default_storage
  ([`d7afa0a`](https://github.com/nasaharvest/glam-api/commit/d7afa0ad741b7ca9cb899f82480a4345388f2749))


## v1.6.0 (2025-01-07)

### Features

- Add utility function to upload files to s3
  ([`58bd67e`](https://github.com/nasaharvest/glam-api/commit/58bd67ea22b3c27fd5984392fe32a51b41587e05))

### Refactoring

- Remove duplicate utility function
  ([`4aad928`](https://github.com/nasaharvest/glam-api/commit/4aad928d5fa1c1d2f368326c759893e15508e855))


## v1.5.0 (2024-12-31)

### Build System

- Change python docker image from slim to slim-bullseye
  ([`4ce2e20`](https://github.com/nasaharvest/glam-api/commit/4ce2e20349a65864de61c49940d9737098888b2c))

### Features

- Add GDAL configuration options to django settings
  ([`a6f9518`](https://github.com/nasaharvest/glam-api/commit/a6f95181e0aa1c136a07f4ad6446c5fd3fd07819))

use the rasterio Env context manager to set the GDAL options defined in settings.py

### Refactoring

- Change s3 url patterns used with cogreader
  ([`7a612f7`](https://github.com/nasaharvest/glam-api/commit/7a612f7a6b13dc57aec5d8901ef8a74ea8f88570))


## v1.4.3 (2024-12-24)

### Bug Fixes

- Update S3 configuration setting references
  ([`c5076c7`](https://github.com/nasaharvest/glam-api/commit/c5076c77812663a979e8f360a89cb76b200bd94b))

### Build System

- Change python docker image from slim-buster to slim
  ([`b06c024`](https://github.com/nasaharvest/glam-api/commit/b06c024d03060445c5eef1b3310643d6f5c1bfc2))

### Code Style

- Add temporary logging
  ([`ae8c129`](https://github.com/nasaharvest/glam-api/commit/ae8c129d24f380d13bb79365b95628118ae79d3c))


## v1.4.2 (2024-12-22)

### Bug Fixes

- Remove security token override for raster storage class
  ([`72b2437`](https://github.com/nasaharvest/glam-api/commit/72b2437d35615a5947d429d918e85d02356960d5))

### Build System

- Bump python version of base image in Dockerfile to 3.11-slim-buster
  ([`ba444fc`](https://github.com/nasaharvest/glam-api/commit/ba444fc035671b5a1bb546261e8bf6bb7dfc8af3))


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

### Breaking Changes

- Upgrade Django version: 3.2.15 -> ^4.2. BREAKING CHANGE: Replace requirements files with poetry
  for dependency management.


## v0.2.0 (2022-10-20)


## v0.1.0 (2022-10-13)
