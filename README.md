<p align="center">
  <a href="https://github.com/SeatizenDOI/zenodo-tools/graphs/contributors"><img src="https://img.shields.io/github/contributors/SeatizenDOI/zenodo-tools" alt="GitHub contributors"></a>
  <a href="https://github.com/SeatizenDOI/zenodo-tools/network/members"><img src="https://img.shields.io/github/forks/SeatizenDOI/zenodo-tools" alt="GitHub forks"></a>
  <a href="https://github.com/SeatizenDOI/zenodo-tools/issues"><img src="https://img.shields.io/github/issues/SeatizenDOI/zenodo-tools" alt="GitHub issues"></a>
  <a href="https://github.com/SeatizenDOI/zenodo-tools/blob/master/LICENSE"><img src="https://img.shields.io/github/license/SeatizenDOI/zenodo-tools" alt="License"></a>
  <a href="https://github.com/SeatizenDOI/zenodo-tools/pulls"><img src="https://img.shields.io/github/issues-pr/SeatizenDOI/zenodo-tools" alt="GitHub pull requests"></a>
  <a href="https://github.com/SeatizenDOI/zenodo-tools/stargazers"><img src="https://img.shields.io/github/stars/SeatizenDOI/zenodo-tools" alt="GitHub stars"></a>
  <a href="https://github.com/SeatizenDOI/zenodo-tools/watchers"><img src="https://img.shields.io/github/watchers/SeatizenDOI/zenodo-tools" alt="GitHub watchers"></a>
</p>


<div align="center">

# Zenodo tools

</div>

This repository provides tools for uploading, downloading and manipulating seatizen sessions on the zenodo platform


## Summary

* [Installation](#installation)
* [Usage upload](#usage-of-zenodo-upload-script-parameters)
* [Usage download](#usage-of-zenodo-download-script-parameters)
* [Contributing](#contributing)
* [License](#license)


## Installation

To ensure a consistent environment for all users, this project uses a Conda environment defined in a `zenodo_env.yml` file. Follow these steps to set up your environment:

1. **Install Conda:** If you do not have Conda installed, download and install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/products/distribution).

2. **Create the Conda Environment:** Navigate to the root of the project directory and run the following command to create a new environment from the `zenodo_env.yml` file:
   ```bash
   conda env create -f zenodo_env.yml
   ```

3. **Activate the Environment:** Once the environment is created, activate it using:
   ```bash
   conda activate zenodo_env
   ```
4. **Create config.json:** To use this repository, you need a config.json file at the root of the project containing your own ACCESS_TOKEN:
    ```json
    {
        "ACCESS_TOKEN": "ACCESS_TOKEN",
        "ZENODO_LINK": "https://zenodo.org/api/deposit/depositions"
    }
    ```
5. **Other lib:** Install mod-spatialite. Here for ubuntu 22.04
```bash
sudo apt-get install libsqlite3-mod-spatialite
```


## Contributing

Contributions are welcome! To contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or fix.
3. Commit your changes with clear, descriptive messages.
4. Push your branch and submit a pull request.

## License

This framework is distributed under the wtfpl license. See `LICENSE` for more information.

## TODO

Zenodo monitoring :

- Static group class for each user
- Qgis project for geopackage
- Statistic after each export
- Information about split file if to big