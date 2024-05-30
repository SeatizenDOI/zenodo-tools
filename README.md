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

## Usage of zenodo-upload Script Parameters

The zenodo-upload script is designed to facilitate the workflow of uploading raw and processed data with metadata. You can use various options to specify inputs and the types of data to upload. Here is a description of the main parameters:

To run the zenodo-upload.py, navigate to the project root and execute:

```bash
python zenodo-upload.py [OPTIONS]
```

Where `[OPTIONS]` can include:

### Input Parameters

The script allows you to select an input method from several mutually exclusive options:

* `-efol`, `--enable_folder`: Use data from a session folder.
* `-eses`, `--enable_session`: Use data from a single session.
* `-ecsv`, `--enable_csv`: Use data from a CSV file.
* `-eno`, `--enable_nothing`: Do not use a session; use with the clean parameter.

### Input Paths

You can specify the paths to the files or folders to be used as input:

* `-pfol`, `--path_folder`: Path to the session folder. Default: /home/bioeos/Documents/Bioeos/plancha-session.
* `-pses`, `--path_session`: Path to a specific session. Default: /media/bioeos/E/202309_plancha_session/20230926_REU-HERMITAGE_ASV-2_01/.
* `-pcsv`, `--path_csv_file`: Path to the CSV file containing the inputs. Default: ./csv_inputs/retry.csv.

### Data Types to Upload

The script allows you to choose the type of data to upload:

* `-ur`, `--upload-rawdata`: Upload raw data from a session.
* `-up`, `--upload-processeddata`: Specify the folder to upload. Use f for FRAMES, m for METADATA, b for BATHY, g for GPS, i for IA. For example, -up fi to upload frames and IA.
* `-um`, `--update-metadata`: Update metadata from a session.

### Optional Arguments

The script also includes optional arguments to fine-tune its behavior:

* `-is`, `--index_start`: Choose the index from which to start. Default: 0.
* `-cd`, `--clean_draft`: Clean all drafts with no published version.

## Usage of zenodo-download Script Parameters


### Input Parameters

The script allows you to select an input method from several mutually exclusive options:

* `-edoi`, `--enable_doi`: Use a DOI (Digital Object Identifier).
* `-ename`, `--enable_name`: Use a session name.
* `-ecsv`, `--enable_csv`: Use data from a CSV file.

### Input Path

You can specify the path to the CSV file to be used as input:

* `-pcsv`, `--path_csv_file`: Path to the CSV file containing the inputs. The header can be session_name or doi or both. Default: ./csv_inputs/download_example.csv.

### Output Path

You can specify the path to the folder where the downloaded sessions will be saved:

* `-pout`, `--path_folder_out`: Output folder to rebuild sessions. Default: /tmp/test_download.

### Data Types to Download

The script allows you to choose the type of data to download:

* `-dr`, `--download_rawdata`: Download raw data from a session.
* `-dp`, `--download_processed_data`: Download processed data from a session.

### Optional Arguments

The script also includes optional arguments to fine-tune its behavior:

* `-is`, `--index_start`: Choose the index from which to start. Default: 0.

## Contributing

Contributions are welcome! To contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or fix.
3. Commit your changes with clear, descriptive messages.
4. Push your branch and submit a pull request.

## License

This framework is distributed under the wtfpl license. See `LICENSE` for more information.