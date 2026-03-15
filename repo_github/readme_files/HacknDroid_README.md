# HacknDroid
**Hackndroid** is a framework used for the automation of some Mobile Application Penetration Testing (MAPT) activities and the interaction with the mobile Android device.

# More details
For further details, visit the documentation [here](https://raffadndm.gitbook.io/toolkit/hackndroid).

# Main functionalities
- ***advanced_search:*** Search and replacement in file/folder (recursively) for bynary patterns, strings or secrets
- ***apk:*** Several APKs related operations (apk analysis for root detection/certificate pinning hints, apk decompiling/compiling, JADX-GUI launch, etc.)
- ***app_data_and_logs:*** Access to app data (e.g. backups, storage) and logs
- ***device_info:*** Get mobile device information
- ***devices:*** Select one of the available mobile devices
- ***emulator:*** Manage AVDs and launch emulators
- ***file_transfer:*** Transfer files from/to mobile devices
- ***frida:*** Frida setup and scripts launcher
- ***install_uninstall:*** Install/Uninstall an app on the mobile device.
- ***interactive_shell:*** Interactive shell for the mobile device
- ***mirroring:*** Mirroring management (screenshot, video recording and scren mirroring)
- ***mobile_settings:*** Management of mobile device modes (battery saver, do not disturb, connectivity)
- ***processes_list:*** List all the processes
- ***proxy:*** Set proxy on the mobile device using the current PC IP or another IP (e.g. regular proxy, invisible proxy via iptables or dns spoofing) and TLS certificates management
- ***shutdown_reboot:*** Reboot/shutdown the device with several options

---

## Install
Install python requirements using the following command:
```bash
pip install -r requirements.txt
```

Install all the binary requirements with the following command:
```bash
python3 hackndroid.py --install
```

> ***Note:***
> Before installing, ensure that the latest version of the Java JDK is installed on your system.
> 
> Additionally, make sure to configure the `JAVA_HOME` environment variable to point to the *JDK installation directory*, and update the `PATH` variable to include the `<jdk-path>/bin` directory.

---

# Run the program
```bash
python hackndroid.py
```

By running the program, the script will populate the file `config.ini` created during the installation phase with, for example, data related to the device used. 

# Runtime Examples 
At the beginning, the program detect if a mobile device is connected to the current computer:
- if a device is connected, the program will start with every option available in the menu 

![run_with_device](https://891057776-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FFfczzabL9Z6aqUzkVYdN%2Fuploads%2Fgit-blob-1dfb36e57af8cff6d540e3f66e69e815044a2da4%2Frun_with_device.png?alt=media)

![run_with_device2](https://891057776-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FFfczzabL9Z6aqUzkVYdN%2Fuploads%2Fgit-blob-a5c5638820e99a3c31380589ce3a371553f53450%2Frun_with_device2.png?alt=media)


- otherwise, the script will show to the user only options that could be used without a mobile device

![run_without_device](https://891057776-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FFfczzabL9Z6aqUzkVYdN%2Fuploads%2Fgit-blob-a797a7ab5defc3b5d5c0457d148d380719643e29%2Frun_without_device.png?alt=media)

![run_without_device2](https://891057776-files.gitbook.io/~/files/v0/b/gitbook-x-prod.appspot.com/o/spaces%2FFfczzabL9Z6aqUzkVYdN%2Fuploads%2Fgit-blob-c1ae6e67580694bd14ab292d244c602a46f4c56e%2Frun_without_device2.png?alt=media)

However, the current device could be selected not only when the program starts but also using the `devices` option as follows:

### Tested on
- Windows
- Linux
- MacOS