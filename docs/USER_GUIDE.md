# Ricks-Lab UPS Utilities - User Guide

A set of utilities to monitor and react to the status of a set of supported UPSs.

## Current rickslab-ups-utils Version: 1.2.x

 - [Installation](#installation)
 - [Getting Started](#getting-started)
 - [Using ups-ls](#using-ups-ls)
 - [Using ups-mon](#using-ups-mon)
 - [Using ups-daemon](#using-ups-daemon)


## Installation

There are 4 methods of installation available and summarized here:
* [Repository](#repository-installation) - This approach is recommended for those interested
in contributing to the project or helping to troubleshoot an issue in realtime with the
developer. This type of installation can exist along with any of the other installation type.
* [PyPI](#pypi-installation) - Meant for users wanting to run the very latest version.  All
**PATCH** level versions are released here first.  This install method is also meant for
users not on a Debian distribution.
* [Rickslab.com Debian](#rickslabcom-debian-installation) - Lags the PyPI release in order
to assure robustness. May not include every **PATCH** version.

### Repository Installation

For a developer/contributor to the project, it is expected that you duplicate the development environment
using a virtual environment. So far, my development activities for this project have used python3.6. 
The following are details on setting up a virtual environment with python3.6:

```shell
sudo apt install -y python3.6-venv
sudo apt install -y python3.6-dev
```

Clone the repository from GitHub with the following command:

```shell
git clone https://github.com/Ricks-Lab/ups-utils.git
cd ups-utils
```

Initialize your *rickslab-ups-utils-env* if it is your first time to use it. From the project root directory, execute:

```shell
python3.6 -m venv rickslab-ups-utils-env
source rickslab-ups-utils-env/bin/activate
pip install --no-cache-dir -r requirements-venv.txt
```

On newer systems, I have found that I get a `ModuleNotFoundError: No module named 'numpy'`, even though `numpy` was
successfully installed in the newly created virtual environment.  To resolve this, I deactivated the venv and installed
it for the system instance of python.  When back in the venv, the issue is resolved.  There seems to be a bigger 
issue in using some packages, including Gtk and numpy, from within a virtual environment.

You then run the desired commands by specifying the full path: `./ups-ls`

### PyPI Installation

Install the latest package from [PyPI](https://pypi.org/project/rickslab-ups-utils/) with the following
commands:

```shell
pip3 install rickslab-ups-utils
```

Or, use the pip upgrade option if you have already installed a previous version:

```shell
pip3 install rickslab-ups-utils -U
```

You may need to open a new terminal window in order for the path to the utilities to be set.

### Rickslab.com Debian Installation

First, remove any previous PyPI installation and exit that terminal.  If you
also have a Debian installed version, the pip uninstall will likely fail,
unless you remove the Debian package first.  You can skip this step if you
are certain no other install types are still installed:

```shell
sudo apt purge rickslab-ups-utils
sudo apt autoremove
pip uninstall rickslab-ups-utils
exit
```

If you had previously (before 1.2.0) installed from rickslab.com, you should
delete the key from the apt keyring:

```shell
sudo apt-key del C98B8839
```

Next, add the *rickslab-ups-utils* repository:

```shell
wget -q -O - https://debian.rickslab.com/PUBLIC.KEY | sudo gpg --dearmour -o /usr/share/keyrings/rickslab-agent.gpg

echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/rickslab-agent.gpg] https://debian.rickslab.com/ups-utils/ stable main' | sudo tee /etc/apt/sources.list.d/rickslab-ups-utils.list

sudo apt update
```

Then install the package with apt:

```shell
sudo apt install rickslab-ups-utils
```

If you decide to no longer use this type of install, you can remove
rickslab-ups-utils from the system repository list by executing the following:

```shell
echo '' | sudo tee /etc/apt/sources.list.d/rickslab-ups-utils.list
```

## Getting Started

# Configuration

Application configuration parameters must be specified in the `ups-utils.ini` file.  A
set of template files are provided: `ups-utils.ini.template` and `ups-config.ini.template`.
You can determine the location of the template files to modify by executing the following command:

```shell
ups-ls --about
```

Once you have created the .json and .ini files from the template files, you can verify
the values of the configuration settings by executing:

```shell
ups-ls --list_params
```

Also, a UPS list must be specified in the `ups-config.json` file using `ups-config.json.template`
as a template.  This file contains details about each UPS that make snmp communication possible.
The utility requires snmp v2c in order to communicate with the network accessible UPSs.  As a
result, you must configure your target Network attached UPS devices to use SNMPv2 with a known
Private Community String.

If you installed from debian package, the template configuration files will be owned by root.  When
you create your configuration files from the templates, you MUST change group ownership to
*upsutils* and change permissions to 660:

```shell
cd /usr/share/rickslab-ups-utils/config/
sudo chgrp upsutils ups-utils.ini ups-config.json
sudo chmod 660 ups-utils.ini ups-config.json
```

If you installed from PyPI, you will be the owner of the file, so there is no need to change
group ownership, but the configuration files must be readable by only you:

```shell
cd ~/.local/share/rickslab-ups-utils/config
chmod 600 ups-utils.ini ups-config.json
```

To assure the use of the utilities only with secure configuration files, all utilities will
exit with an error if not properly secured.

The **ups-utils** rely on the command *snmpget* which is part of the snmp package that must
be installed:

```shell
sudo apt install snmp
```

## Using ups-ls

After getting your system setup to support **rickslab-ups-utils**, it is best to verify functionality by
listing your UPS details with the `ups-ls` command.  The utility will read the `ups-config.json` to get
a list of configured UPSs. The utility will also verify accessibility of the listed UPSs. Here is an
example of output for a single UPS using `ups-ls --no_markup`:

```
UPS Name: UPS1-PDX
   UPS IP/FQDN: 192.168.100.140
   UPS Type: apc_ap96xx
   UPS Model: SRT3000RMXLA-NC
   NMC Model: AP9641
   Daemon: False
   UPS Real Name: APC UPS
   General UPS Information: APC Web/SNMP Management Card (MB:v4.2.9 PF:v1.3.3.1 PN:apc_hw21_aos_1.3.3.1.bin
                            AF1:v1.3.3.1 AN1:apc_hw21_su_1.3.3.1.bin MN:AP9641 HR:5 SN: 5A2128T03472
                            MD:07/15/2021) (Embedded PowerNet SNMP Agent SW v2.2 compatible)
   UPS BIOS Serial Number: AS2128296401
   UPS Firmware Revision: UPS 08.2 (ID1025)
   UPS Manufacture Date: 07/18/2021
   UPS Model Type: Smart-UPS SRT    3000
   UPS Contact: Rick
   UPS Location: RicksLab
   Communicating with UPS Device: Communication OK
   UPS System Status: OnLine-SCE-On
   Battery Status: Battery Normal
   Battery Replacement: OK
   Last Self Test Results: OK
   Date of Last Self Test: 06/07/2022
   UPS Up Time: (581111960) 67 days, 6:11:59.60
   Last Transfer Event: UPS Self Test
   Battery Temp (C): 28
   UPS Environment Temp (C): 29
   Percentage of Total Capacity: 100
   Time on Battery: (0.0, ' 0:00:00.00')
   Runtime Remaining: (119.28, ' 1:11:34.00')
   Input Voltage (V): 122
   Input Frequency (Hz): 60
   Output Voltage (V): 120
   Output Frequency (Hz): 60
   Output Load as % of Capacity: 12
   Output Power (W): 294
   Output Current (A): 3
```


## Using ups-mon

The `ups-mon` command will produce a continuously updating table of parameters useful in monitoring 
a UPS.  By default, a text based table will be displayed in the terminal window where the command is 
executed.  Using `--gui` command line argument will produce a Gtk base GUI to display the same parameters.
In both types of displays, output will be color coded based on entries in the `ups-utils.ini` file.  Here 
is example output with the `--gui` option:

![](ups-mon-gui_screenshot.png)

## Using ups-daemon

The `ups-daemon` command will interact with only the UPS identified as the daemon UPS in the `ups-config.json`
file.  The default behavior is similar to the `ups-ls` command, but will also include a summary of
parameters from `ups-utils.ini`.

```
UPS Name: UPS1
   UPS IP/FQDN: 192.168.1.241
   UPS Type: apc_ap96xx
   UPS Model: SRT3000XLA-TW
   NMC Model: AP9630
   Daemon: True
   UPS Real Name: RicksLab_UPS1
   General UPS Information: APC Web/SNMP Management Card (MB:v4.1.0 PF:v6.7.2 PN:apc_hw05_aos_672.bin
                            AF1:v6.7.2 AN1:apc_hw05_sumx_672.bin MN:AP9630 HR:05 SN: ZA1450081947
                            MD:12/10/2014) (Embedded PowerNet SNMP Agent SW v2.2 compatible)
   UPS BIOS Serial Number: AS1839197322
   UPS Firmware Revision: UPS 06.0 (ID1010)
   UPS Manufacture Date: 09/29/2018
   UPS Model Type: Smart-UPS SRT    3000
   UPS Contact: Rick
   UPS Location: RicksLab-Rack
   Communicating with UPS Device: Communication OK
   UPS System Status: OnLine-SCE-On
   Battery Status: Battery Normal
   Battery Replacement: OK
   Last Self Test Results: OK
   Date of Last Self Test: 06/05/2022
   UPS Up Time: (719602520) 83 days, 6:53:45.20
   Last Transfer Event: Small Spike
   Battery Temp (C): 25
   UPS Environment Temp (C): ---
   Percentage of Total Capacity: 100
   Time on Battery: (0.0, ' 0:00:00.00')
   Runtime Remaining: (154.81, ' 1:32:53.00')
   Input Voltage (V): 117
   Input Frequency (Hz): 59
   Output Voltage (V): 120
   Output Frequency (Hz): 60
   Output Load as % of Capacity: 27
   Output Power (W): 733
   Output Current (A): 7

Daemon parameters:
    boinc_home: /home/boinc/BOINC/
    ups_utils_script_path: /home/rick/pydev/ups-utils/
    suspend_script: /home/rick/pydev/ups-utils/pauseBOINC.sh
    resume_script: /home/rick/pydev/ups-utils/resumeBOINC.sh
    shutdown_script: /home/rick/pydev/ups-utils/shutdownBOINC.sh
    cancel_shutdown_script: /home/rick/pydev/ups-utils/cancelShutdownBOINC.sh
    read_interval: {'monitor': 10, 'daemon': 30, 'limit': 5}
    threshold_env_temp: {'crit': 35, 'warn': 30, 'limit': 5}
    threshold_battery_time_rem: {'crit': 5, 'warn': 10, 'limit': 4}
    threshold_time_on_battery: {'crit': 3, 'warn': 2, 'limit': 1}
    threshold_battery_load: {'crit': 90, 'warn': 80, 'limit': 5}
    threshold_battery_capacity: {'crit': 10, 'warn': 50, 'limit': 5}
```

The real purpose of this command is to be used a daemon to monitor a system on
UPS power.  This is the behavior when used with the `--daemon` option.  Scripts
to execute pausing and resuming of power intensive applications, like BOINC.  A
shutdown script can be configured to shutdown the system when battery is below a
specified threshold.  By default, only exception events are displayed, but with
the `--verbose` option, status messages of system status are displayed as in the
example below.

![](ups-daemon-verbose_screenshot.png)
