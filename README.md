# DataSafe: Smart Backup Tool

**DataSafe** is a simple and efficient tool for creating backups of your important folders and storing them securely. The tool relies on SQLAlchemy to store metadata about the backups in a database, making them easy to track and manage.

## Key Features

*   **Ease of Use:** A simple command-line interface makes creating backups quick and easy.
*   **Multiple Compression Options:** The tool supports several compression options (ZIP, TAR, TAR.GZ) to reduce the size of backups.
*   **Metadata Storage:** Stores metadata about backups in a SQLite database using SQLAlchemy.
*   **Path Specification:** Easily specify the path of the folder to back up.
*   **Default Compression:** Backups are compressed by default to reduce size.
*   **Configuration Options:** Backup options (such as compression and size calculation) can be customized via the command line.
* **Required path:** Path required for the source directory.

## How to Use

### Prerequisites

*   Python 3.6+
*   SQLAlchemy

### Installation

1.  Clone the repository:

    ```bash
    git clone [repository link]
    cd DataSafe
2.  Install dependencies:

    ```bash
    pip install SQLAlchemy
### Running

```bash
python app.py <source_folder_path> [options]
```

### Options

*   `<source_folder_path>`: (Required) The path to the folder you want to back up.
*   `-u` or `--database`: The database connection URL (SQLite by default). Example: `--database sqlite:///backups.db`
*   `-s` or `--no_size`: Disable Calculate directory size (enabled by default).
*   `-n` or `--no-compressed`: Disable compression (enabled by default).
*  `-t` or `--compression_type`: Compression type (ZIP, TAR, TAR_GZ). ZIP is the default. Example: `--compression_type TAR`


### Examples

*   Create a compressed backup of the `Documents` folder:

    ```bash
    python main.py Documents
*   Create an uncompressed backup of the `Projects` folder and store it in a different database:

    ```bash
    python main.py Projects --database postgresql://user:password@host:port/database -n
*   Create a compressed backup with TAR.GZ compression:

    ```bash
    python main.py MyFolder --compression_type TAR_GZ
## Project Structure

*   `core.py`: Contains the definitions of the core classes (`SourceDirectory`, `BackupArchive`).
*   `models.py`: Contains the definitions of the database models (SQLAlchemy models) and the database management class (`DatabaseManager`).
*   `manager.py`: Contains the `BackupManager` class that manages the backup process.
*   `app.py`: The main entry point of the program.

## Contributing

If you would like to contribute to the development of DataSafe, you can submit a pull request with an explanation of the changes you have made.

## License

MIT License Copyright (c) 2025 [Yazan-Dev9](https://github.com/Yazan-Dev9)
