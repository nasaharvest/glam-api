# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.2.0] - 2022-10-20
### Added
- Added function in daac.py that returns dtype based on science dataset (sds) name
- Added EarthdataLoginSetup.py for .netrc file creation

### Changed
- Set allow_intermediate_compression in cog_translate functions in download utility to prevent ballooning file sizes
- Updated dev_reqs.txt, added --no-binary flag to rasterio requirement for reading hdf files


## [0.1.0] - 2022-10-13
### Added
- Initial commit of reorganized & restructured GLAM Django application