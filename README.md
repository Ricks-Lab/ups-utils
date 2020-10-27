![](https://img.shields.io/github/license/Ricks-Lab/ups-utils)
[![PyPI version](https://badge.fury.io/py/rickslab-ups-utils.svg)](https://badge.fury.io/py/rickslab-ups-utils)
[![Downloads](https://pepy.tech/badge/rickslab-ups-utils)](https://pepy.tech/project/rickslab-ups-utils)
![GitHub commit activity](https://img.shields.io/github/commit-activity/y/Ricks-Lab/ups-utils)
![GitHub last commit](https://img.shields.io/github/last-commit/Ricks-Lab/ups-utils)

# rickslab-ups-utils

A set of utilities to monitor and react to the status of a supported UPS

## Installation

### Debian Package Installation

First, remove any previous PyPI installation and exit that terminal:
```
pip uninstall rickslab-ups-utils
exit
```
Next, add the *rickslab-ups-utils* repository:
```
wget -q -O - https://debian.rickslab.com/PUBLIC.KEY | sudo apt-key add -

echo 'deb [arch=amd64] https://debian.rickslab.com/ups-utils/ stable main' | sudo tee /etc/apt/sources.list.d/rickslab-ups-utils.list

sudo apt update
```
Then install the package with apt:
```
sudo apt install rickslab-ups-utils
```

### PyPI Installation

Install the latest package from [PyPI](https://pypi.org/project/rickslab-ups-utils/) with the following
commands:

```
pip3 uninstall rickslab-ups-utils
pip3 install rickslab-ups-utils
```
The uninstall is required to make sure all modules are updated.  If you still get an old version,
then specify not to use cached files:
```
pip3 install --no-cache-dir rickslab-ups-utils
```

## Getting Started

Application configuration parameters can be specified in the `ups-utils.ini` file.  A
template files is provided: `ups-utils.ini.template`.  You can verify the values of
the configuration settings by executing

```
ups-daemon --list_params
```

Also, a UPS list must be specified in the `config.json` file using `config.json.template` as a
template.  This file contains details about each UPS that make snmp communication possible.  The
utility requires snmp v2c in order to communicate with the network accessible UPSs.  As a result,
you must configure your target Network attached UPS devices to use SNMPv2 with a known Private
Community String.

The ups-utils rely on the command *snmpget* which is part of the snmp package that must
be installed:

```
sudo apt install snmp
```

## ups-daemon

With no options specified, the utility will give the current status of the UPS configured
with *daemon = true* in the config.json file. With the *--daemon* option, *ups-daemon*
will continuously check the status of the UPS.  When it detects that the UPS is sourcing
powering from the battery, it will check the amount of time it has been running on battery
and run the specified suspend script when the specified threshold is exceeded.  It will
execute the specified resume script when it detects power has resumed.  When the utility
detects a Battery Low event from the UPS or that time remaining for battery or the battery
charge is below specified thresholds, then the shutdown script will be executed. If
*ups-deamon* detects a return to line power has occurred before the shutdown has completed,
it will execute the cancel shutdown script.  With the *--list_commands* option, the utility
will list all available SNMP commands for the configured UPS.  With the *--list_params*
option, the daemon configuration parameters will be listed. The *--logfile filename* option
is used to specify a logfile, but is not implemented at this time.  The threshold and script
definitions must be made in the config.py file using config.py.template as a template.

## ups-ls

This utility displays most relevant parameters for installed and compatible UPSs
listed in the config.json file.  By default, all available parameters are displayed.
The *--input* and *--output* options can be used to get relevant UPS input and output
parameters.

## ups-monitor

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

## New in this Beta Release  -  v0.11.0

* Initial Beta Release - Please feedback your question/issues in the project's issues.  Thanks!

## Under Development

The utility currently supports:

* APC UPS with AP9630 NMC
* EATON UPS with PowerWalker NMC

It monitors the specified UPS using snmp v2c.  I have not implemented the ability to listen to snmp traps
yet, as I still have some research to do.  If you have different UPS and would like to extend the dictionary
in this [code](https://github.com/Ricks-Lab/ups-utils/blob/master/UPSmodules/UPSmodule.py) to support it, feel
free to make a pull request.

## Reference Material

* [apc-ups-snmp](https://github.com/phillipsnick/apc-ups-snmp)
* [Partial List of OIDs for APC UPS](https://www.opsview.com/resources/monitoring/blog/monitoring-apc-ups-useful-oids)
* [Another Partial List of OIDs for APC UPS](https://www.itninja.com/blog/view/snmp-oids-for-apc-smart-ups-3000-rm-xl)
* [Another Partial List of OIDs for APC UPS](https://wiki.netxms.org/wiki/UPS_Monitoring_(APC)_via_SNMP)
* [APC Reference](https://www.apc.com/salestools/LFLG-AFACYW/LFLG-AFACYW_R1_EN.pdf)
* [snmp utilities](http://www.net-snmp.org/docs/man/)
* [MIB Browser](http://www.ireasoning.com/)
* [Eaton PowerWalker NMC](https://powerwalker.com/?page=nmc&lang=en)
