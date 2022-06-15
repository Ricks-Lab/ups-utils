![](https://img.shields.io/github/license/Ricks-Lab/ups-utils)
[![PyPI version](https://badge.fury.io/py/rickslab-ups-utils.svg)](https://badge.fury.io/py/rickslab-ups-utils)
[![Downloads](https://pepy.tech/badge/rickslab-ups-utils)](https://pepy.tech/project/rickslab-ups-utils)
![GitHub commit activity](https://img.shields.io/github/commit-activity/y/Ricks-Lab/ups-utils)
![GitHub last commit](https://img.shields.io/github/last-commit/Ricks-Lab/ups-utils)

# rickslab-ups-utils

A set of utilities to monitor and react to the status of a supported UPS

## Installation

There are currently 3 possible ways of installing *rickslab-ups-utils*.  These are summarized in
order of preference as:

* Debian Package - This will install a Debian package file from my public
server.  It is signed and verified with my GPG key.  This will be installed
as root and can be removed and updated with apt tools.
* PyPI - Uses the Python Package Index as the source.  This should work on
systems other than Debian based, but I have ony verified Ubuntu.  Feel free
to report any issues, and I will work them out to support other distros.
* Repository - You can always clone the repository and run that version.
This is useful if you want to contribute to the project.

### Debian Package Installation

First, remove any previous PyPI installation and exit that terminal:

```shell
pip uninstall rickslab-ups-utils
exit
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

After installation, you will need to create a new group, *upsutils*, and add trusted users to this group.
This required for this type of installation in order to secure the snmp shared secret stored in the configuration
files:

```shell
sudo groupadd upsutils
sudo usermod -a -G upsutils $LOGNAME
```

After adding the user to a new group, the user must logout and relogin before the change is in effect.

### PyPI Installation

Install the latest package from [PyPI](https://pypi.org/project/rickslab-ups-utils/) with the following
commands:

```shell
pip3 install rickslab-ups-utils
```

For an install from PyPI, all files will be installed in a subdirectory of
`~/.local/share/rickslab-ups-utils/config`. Files will be owned by you and there is no
need to setup a special group, but permissions will need to be read only by you.

## Configuration

Application configuration parameters must be specified in the `ups-utils.ini` file.  A
template files is provided: `ups-utils.ini.template`. You can verify the values of the
configuration settings by executing:

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

To assure the use of the utilities only with secure configuration files, all utilities should
exit with an error if not properly secured.

The ups-utils rely on the command *snmpget* which is part of the snmp package that must
be installed:

```shell
sudo apt install snmp
```

## ups-daemon

With no options specified, the utility will give the current status of the
UPS configured with *daemon = true* in the ups-config.json file. With the
*--daemon* option, *ups-daemon* will continuously check the status of the
UPS.  When it detects that the UPS is sourcing powering from the battery,
it will check the amount of time it has been running on battery and run
the specified suspend script when the specified threshold is exceeded.  It
will execute the specified resume script when it detects power has resumed.
When the utility detects a Battery Low event from the UPS or that time
remaining for battery or the battery charge is below specified thresholds,
then the shutdown script will be executed. If *ups-daemon* detects a return
to line power has occurred before the shutdown has completed, it will
execute the cancel shutdown script.  With the *--verbose* option set, no
event update messages will be output, otherwise, only events are output.
The *--logfile filename* option is used to specify a logfile, but is not
implemented at this time.  The threshold and script definitions must be
made in the config.py file using *config.py.template* as a template.

## ups-ls

This utility displays most relevant parameters for installed and compatible
UPSs listed in the config.json file.  By default, all available parameters
are displayed. The --input and --output options can be used to get relevant
UPS input and output parameters.  With the *--list_commands* option, the
utility will list all available SNMP commands for the configured UPS.  With
the *--list_params* option, the daemon configuration parameters will be listed.
The *--list_decoders* option will display list of all MiB decoders available
for the UPS defined as daemon target.

## ups-mon

A utility to give the current state of all compatible UPSs. The default behavior
is to continuously update a text based table in the current window until Ctrl-C is
pressed.  With the *--gui* option, a table of relevant parameters will be updated
in a Gtk window.  You can specify the delay between updates with the *--sleep N*
option where N is an integer > 10 that specifies the number of seconds to sleep
between updates.  The *--log* option is used to write all monitor data to a psv log
file.  When writing to a log file, the utility will indicate this in red at the top of
the window with a message that includes the log file name.  The *--status* option will
output a table of the current status.  The *--long* option will include additional
informational parameters. By default, unresponsive UPSs will not be displayed, but the
*--show_unresponsive* can be used to force their display.

## New in Development  -  v1.2.0 

* Delay sys exit on failure to allow more information to be available for user to troubleshoot.
* Check file permissions for security issues and exit if not secure.
* Determine installation type (Local Git Repository, PyPI, or Debian), and force use
of Debian location for configuration files if it is a debian installation.
* The ups-utils.ini file is now only required for ups-daemon.  Other utilities will
use defaults if missing.
* Added verbose option to ups-daemon to output status message for normal readings.
* Changes in documentation to describe steps necessary to secure snmp shared secret.
* Added check of configuration files readability.
* Implement code improvements from gpu-utils project.
* Move listing like functions from *ups-daemon* to *ups-ls*.
* Complete rewrite.

## Known Issues

The utility currently supports:

* APC UPS with AP9630 and AP9641 NMC
* EATON UPS with PowerWalker NMC.  I had an issue with voltage interpretation, and
found that PowerWalker does not support the use of their NMC with Eaton UPS.  But it 
mostly works anyway.

It monitors the specified UPSs using snmp v2c.  I have not implemented the
ability to listen to snmp traps yet, as I still have some research to do.
If you have different UPS and would like to extend the dictionary in this
[code](https://github.com/Ricks-Lab/ups-utils/blob/master/UPSmodules/UPSmodule.py)
to support it, feel free to make a pull request.

## Reference Material

* [apc-ups-snmp](https://github.com/phillipsnick/apc-ups-snmp)
* [Partial List of OIDs for APC UPS](https://www.opsview.com/resources/monitoring/blog/monitoring-apc-ups-useful-oids)
* [Another Partial List of OIDs for APC UPS](https://www.itninja.com/blog/view/snmp-oids-for-apc-smart-ups-3000-rm-xl)
* [Another Partial List of OIDs for APC UPS](https://wiki.netxms.org/wiki/UPS_Monitoring_(APC)_via_SNMP)
* [APC Reference](https://www.apc.com/salestools/LFLG-AFACYW/LFLG-AFACYW_R1_EN.pdf)
* [snmp utilities](http://www.net-snmp.org/docs/man/)
* [MIB Browser](http://www.ireasoning.com/)
* [Eaton PowerWalker NMC](https://powerwalker.com/?page=nmc&lang=en)

## New in Previous Release  -  v1.0.0

* Initial Release - Full functionality and working debian package!
