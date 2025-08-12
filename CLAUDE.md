# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run Commands

### Running the Application
- **Normal mode**: `python run.py` or double-click `start.bat`
- **Test mode** (without hardware): `python test_mode.py` or double-click `start_test_mode.bat`
- **Check compatibility**: Run `compatibility_guide.bat` for Python version compatibility info

### Virtual Environment Setup
- Setup virtual environment: `setup_venv.bat` or `setup_venv.ps1`

### Creating Executable
- Build standalone executable: `pyinstaller RFIDReaderApp.spec`

## Architecture Overview

This RFID reader management application is built with PyQt6 and communicates with RFID hardware via serial protocol.

### Core Components

1. **main.py** - Main application entry point with PyQt6 GUI
   - `RFIDReaderApp`: Main window class managing UI and user interactions
   - `RFIDReaderThread`: Background thread handling serial communication with RFID hardware
   - `LogPanel`: Custom widget for displaying operation logs
   - Supports continuous read/write operations and material templates

2. **rfid_protocol.py** - RFID communication protocol implementation
   - Handles EF...FE protocol for reading/writing RFID tags
   - `read_tag()`: Reads tag data from specified channel (0-7)
   - `write_tag()`: Writes 112-byte data to specified channel
   - `_tag_data_to_bytes()`: Converts tag data dictionary to 112-byte format

3. **read_rfid_tag.py** - Protocol command construction and response parsing
   - `construct_read_command()`: Builds read commands for channels 0-7
   - `parse_rfid_response()`: Parses RFID module responses
   - `construct_write_command()`: Builds write commands with tag data

### Communication Protocol

The application uses a frame-based serial protocol (115200 baud):
- Frame structure: `FH(0xEF) | LEN | CMDC | DATA | BCC | EOF(0xFE)`
- Read command: `0x11`, Write command: `0x12`
- Supports 8 channels (0x00-0x07)
- 112-byte tag data structure containing material properties

### Tag Data Format

RFID tags store 112 bytes structured as:
- Tag Version (2 bytes)
- Filament Manufacturer (16 bytes, ASCII)
- Material Name (16 bytes, ASCII)
- Color Name (32 bytes, ASCII)
- Diameter Target (2 bytes, µm)
- Weight Nominal (2 bytes, grams)
- Print Temp (2 bytes, °C)
- Bed Temp (2 bytes, °C)
- Density (2 bytes, µg/cm³)
- Remaining bytes: Reserved/padding

### Test Mode

The application includes a test mode (`test_mode.py`) that:
- Creates virtual serial ports for testing without hardware
- Simulates RFID tag responses with mock data
- Useful for development and testing UI functionality

## Important Notes

- Python version requirement: 3.6-3.10 (PyQt6 compatibility)
- Serial port COM1 is excluded from available ports list
- Application saves/loads form data using QSettings
- Continuous operations run at 0.5-second intervals
- BCC checksum: XOR of all bytes from FH to DATA, then bitwise NOT